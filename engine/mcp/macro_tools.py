"""MCP macro tools — 6 read-only tools for macro regime data."""

from __future__ import annotations

import datetime as dt
import json
import logging
from typing import Any

from pydantic import BaseModel, ConfigDict

from engine.macro_agent.storage import MacroStorage
from engine.mcp.server import mcp

log = logging.getLogger(__name__)

# Module-level storage (patched in tests)
_storage: MacroStorage = MacroStorage()

# Free-tier AlphaVantage daily limit for budget reporting
_AV_FREE_LIMIT = 25


# ── Pydantic result models ─────────────────────────────────────────────────────

class MacroStateResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    composite_state: str
    capex_state: str | None = None
    yield_curve_state: str | None = None
    risk_state: str | None = None
    capex_as_of: str | None = None
    yield_as_of: dt.date | None = None
    computed_at: dt.datetime | None = None
    is_stale: bool


class CapExQuarter(BaseModel):
    model_config = ConfigDict(extra="ignore")

    company: str
    fiscal_quarter: str
    period_end: dt.date
    capex_usd: float | None = None
    capex_yoy_pct: float | None = None
    filing_form: str | None = None


class CapExTrendResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    company: str
    quarters: list[CapExQuarter]
    latest_qoq_pct: float | None = None
    is_stale: bool = False


class FOMCMeeting(BaseModel):
    model_config = ConfigDict(extra="ignore")

    meeting_date: dt.date
    decision_date: dt.date | None = None
    meeting_type: str = ""
    rate_decision: str | None = None
    target_lower: float | None = None
    target_upper: float | None = None


class FOMCCalendarResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    meetings: list[FOMCMeeting]
    next_meeting_date: dt.date | None = None


class YieldCurveResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    yield_10y: float | None = None
    yield_2y: float | None = None
    spread_10y_2y: float | None = None
    yield_state: str = "stale"
    as_of_date: dt.date | None = None
    source: str = "fred"
    realtime_start: dt.date | None = None


class NewsSentimentResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    cls_headlines: list[str]
    av_sentiment_score: float | None = None
    av_sentiment_label: str | None = None
    av_budget_remaining: int
    as_of_utc: dt.datetime


class IndexSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    indicator_id: str
    group_code: str
    period_date: dt.date
    close: float | None = None
    pct_change: float | None = None
    market_tz: str = ""
    source: str = ""


class GlobalIndicesResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    snapshots: list[IndexSnapshot]
    as_of_utc: dt.datetime


# ── MCP tools ─────────────────────────────────────────────────────────────────

@mcp.tool()
def get_macro_state() -> dict[str, Any]:
    """Return the latest macro regime composite gate state (CapEx / yield curve / risk)."""
    regime = _storage.get_regime_latest()
    if regime is None:
        return MacroStateResult(composite_state="stale", is_stale=True).model_dump(mode="json")
    state = regime.get("composite_state", "stale")
    return MacroStateResult(
        composite_state=state,
        capex_state=regime.get("capex_state"),
        yield_curve_state=regime.get("yield_curve_state"),
        risk_state=regime.get("risk_state"),
        capex_as_of=regime.get("capex_as_of"),
        yield_as_of=regime.get("yield_as_of"),
        computed_at=regime.get("computed_at"),
        is_stale=(state == "stale"),
    ).model_dump(mode="json")


@mcp.tool()
def get_capex_trend(company: str, quarters: int = 4) -> dict[str, Any]:
    """Return CapEx quarterly trend for MSFT/AMZN/GOOGL/META (with QoQ staleness flag)."""
    rows = _storage.get_capex_quarters(company, quarters)
    latest_qoq: float | None = None
    if len(rows) >= 2:
        cur = rows[0].get("capex_usd")
        prev = rows[1].get("capex_usd")
        if cur is not None and prev is not None and prev != 0:
            latest_qoq = round((cur - prev) / prev * 100, 4)
    quarter_models = [CapExQuarter(**r) for r in rows]
    return CapExTrendResult(
        company=company,
        quarters=quarter_models,
        latest_qoq_pct=latest_qoq,
        is_stale=not rows,
    ).model_dump(mode="json")


@mcp.tool()
def get_fomc_calendar(lookahead_days: int = 90) -> dict[str, Any]:
    """Return upcoming FOMC meetings within lookahead_days from today."""
    today = dt.date.today()
    meetings = _storage.get_fomc_upcoming(today, lookahead_days=lookahead_days)
    meeting_models = [FOMCMeeting(**m) for m in meetings]
    next_date = meetings[0]["meeting_date"] if meetings else None
    return FOMCCalendarResult(
        meetings=meeting_models,
        next_meeting_date=next_date,
    ).model_dump(mode="json")


@mcp.tool()
def get_yield_curve() -> dict[str, Any]:
    """Return current 10Y/2Y treasury yields, spread, and FRED vintage date."""
    dgs10 = _storage.get_latest_indicator("DGS10")
    dgs2 = _storage.get_latest_indicator("DGS2")
    v10: float | None = dgs10["value"] if dgs10 else None
    v2: float | None = dgs2["value"] if dgs2 else None
    spread = (v10 - v2) if (v10 is not None and v2 is not None) else None

    if spread is None:
        yield_state = "stale"
    elif spread > 0.5:
        yield_state = "normal"
    elif spread >= -0.2:
        yield_state = "flat"
    else:
        yield_state = "inverted"

    realtime_start = (dgs10 or dgs2 or {}).get("realtime_start")
    as_of_date = (dgs10 or {}).get("period_date")
    source: str = (dgs10 or dgs2 or {}).get("source", "fred") or "fred"

    return YieldCurveResult(
        yield_10y=v10,
        yield_2y=v2,
        spread_10y_2y=spread,
        yield_state=yield_state,
        as_of_date=as_of_date,
        source=source,
        realtime_start=realtime_start,
    ).model_dump(mode="json")


@mcp.tool()
def get_news_sentiment(hours_back: int = 24) -> dict[str, Any]:
    """Return recent CLS headlines and AlphaVantage sentiment score with budget status."""
    today = dt.date.today()
    cutoff = dt.datetime.now(tz=dt.UTC) - dt.timedelta(hours=hours_back)

    av_used = _storage.get_av_budget(today)
    av_remaining = max(0, _AV_FREE_LIMIT - av_used)

    cls_raw_rows = _storage._conn.execute(
        "SELECT value_raw FROM macro_indicators"
        " WHERE group_code='O' AND indicator_id='CLS_NEWS' AND fetched_at >= ?"
        " ORDER BY fetched_at DESC LIMIT 50",
        [cutoff],
    ).fetchall()
    cls_headlines: list[str] = []
    for raw_row in cls_raw_rows:
        raw = raw_row[0] if raw_row else None
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    cls_headlines.extend(str(h) for h in parsed if h)
            except (json.JSONDecodeError, TypeError):
                pass

    av_row = _storage.get_latest_indicator("AV_SENTIMENT")
    av_score: float | None = (
        float(av_row["value"]) if av_row and av_row.get("value") is not None else None
    )

    av_label: str | None = None
    if av_score is not None:
        if av_score > 0.15:
            av_label = "Bullish"
        elif av_score < -0.15:
            av_label = "Bearish"
        else:
            av_label = "Neutral"

    return NewsSentimentResult(
        cls_headlines=cls_headlines,
        av_sentiment_score=av_score,
        av_sentiment_label=av_label,
        av_budget_remaining=av_remaining,
        as_of_utc=dt.datetime.now(tz=dt.UTC),
    ).model_dump(mode="json")


@mcp.tool()
def get_global_indices(groups: list[str]) -> dict[str, Any]:
    """Return latest indicator snapshots for the specified group codes (J/K/M/N)."""
    if groups:
        placeholders = ", ".join("?" * len(groups))
        sql = (
            f"SELECT indicator_id, group_code, period_date,"
            f" value AS close, NULL AS pct_change,"
            f" market_tz, source"
            f" FROM macro_indicators WHERE group_code IN ({placeholders})"
            f" ORDER BY group_code, indicator_id, period_date DESC"
        )
        cur = _storage._conn.execute(sql, groups)
    else:
        sql = (
            "SELECT indicator_id, group_code, period_date,"
            " value AS close, NULL AS pct_change,"
            " market_tz, source"
            " FROM macro_indicators ORDER BY group_code, indicator_id, period_date DESC"
        )
        cur = _storage._conn.execute(sql)

    rows = cur.fetchall()
    cols = [d[0] for d in cur.description] if cur.description else []

    snapshots: list[IndexSnapshot] = []
    for row in rows:
        if isinstance(row, dict):
            d = row
        else:
            d = dict(zip(cols, row))
        # Handle pre-aliased dict keys (e.g., from test mocks with 'value' key)
        if "close" not in d and "value" in d:
            d = {**d, "close": d["value"]}
        snapshots.append(IndexSnapshot(**d))

    return GlobalIndicesResult(
        snapshots=snapshots,
        as_of_utc=dt.datetime.now(tz=dt.UTC),
    ).model_dump(mode="json")
