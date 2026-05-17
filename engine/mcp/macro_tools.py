"""MCP macro tools — 6 read-only tools for macro regime data."""

from __future__ import annotations

import datetime as dt
from typing import Any

from pydantic import BaseModel, ConfigDict

from engine.macro_agent.storage import MacroStorage
from engine.mcp.server import mcp

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
    is_stale: bool
    as_of_date: dt.date | None = None
    capex_as_of: str | None = None
    yield_as_of: dt.date | None = None


class CapExTrendResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    company: str
    quarters: list[dict[str, Any]]
    latest_qoq_pct: float | None = None


class FOMCCalendarResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    meetings: list[dict[str, Any]]
    next_meeting_date: dt.date | None = None


class YieldCurveResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    dgs10: float | None = None
    dgs2: float | None = None
    spread_10y_2y: float | None = None
    realtime_start: dt.date | None = None
    period_date: dt.date | None = None


class NewsSentimentResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    av_budget_remaining: int
    av_sentiment_score: float | None = None
    cls_news_count: int = 0


class IndexSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    indicator_id: str
    group_code: str
    value: float | None = None
    period_date: dt.date | None = None
    market_tz: str | None = None
    value_unit: str | None = None
    source: str | None = None


class GlobalIndicesResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    snapshots: list[IndexSnapshot]


# ── MCP tools ─────────────────────────────────────────────────────────────────

@mcp.tool()
def get_macro_state() -> dict:
    """Return the latest macro regime composite gate state."""
    regime = _storage.get_regime_latest()
    if regime is None:
        return MacroStateResult(composite_state="stale", is_stale=True).model_dump()
    state = regime.get("composite_state", "stale")
    return MacroStateResult(
        composite_state=state,
        capex_state=regime.get("capex_state"),
        yield_curve_state=regime.get("yield_curve_state"),
        risk_state=regime.get("risk_state"),
        is_stale=(state == "stale"),
        as_of_date=regime.get("as_of_date"),
        capex_as_of=regime.get("capex_as_of"),
        yield_as_of=regime.get("yield_as_of"),
    ).model_dump()


@mcp.tool()
def get_capex_trend(company: str, quarters: int = 4) -> dict:
    """Return CapEx quarterly trend for a Big-4 cloud company."""
    rows = _storage.get_capex_quarters(company, quarters)
    latest_qoq: float | None = None
    if rows and rows[0].get("capex_yoy_pct") is not None:
        latest_qoq = float(rows[0]["capex_yoy_pct"])
    return CapExTrendResult(
        company=company,
        quarters=rows,
        latest_qoq_pct=latest_qoq,
    ).model_dump()


@mcp.tool()
def get_fomc_calendar(lookahead_days: int = 90) -> dict:
    """Return upcoming FOMC meetings within lookahead_days from today."""
    today = dt.date.today()
    meetings = _storage.get_fomc_upcoming(today, lookahead_days=lookahead_days)
    next_date = meetings[0]["meeting_date"] if meetings else None
    return FOMCCalendarResult(
        meetings=meetings,
        next_meeting_date=next_date,
    ).model_dump()


@mcp.tool()
def get_yield_curve() -> dict:
    """Return current 10Y/2Y treasury yields and spread."""
    dgs10 = _storage.get_latest_indicator("DGS10")
    dgs2 = _storage.get_latest_indicator("DGS2")
    v10 = dgs10["value"] if dgs10 else None
    v2 = dgs2["value"] if dgs2 else None
    spread = (v10 - v2) if (v10 is not None and v2 is not None) else None
    realtime_start = (dgs10 or dgs2 or {}).get("realtime_start")
    period_date = (dgs10 or {}).get("period_date")
    return YieldCurveResult(
        dgs10=v10,
        dgs2=v2,
        spread_10y_2y=spread,
        realtime_start=realtime_start,
        period_date=period_date,
    ).model_dump()


@mcp.tool()
def get_news_sentiment(hours_back: int = 24) -> dict:
    """Return news sentiment snapshot and AlphaVantage budget status."""
    today = dt.date.today()
    cutoff = dt.datetime.now(tz=dt.UTC) - dt.timedelta(hours=hours_back)

    av_used = _storage.get_av_budget(today)
    av_remaining = max(0, _AV_FREE_LIMIT - av_used)

    cls_rows = _storage._conn.execute(
        "SELECT indicator_id, value, fetched_at FROM macro_indicators"
        " WHERE indicator_id='CLS_NEWS' AND fetched_at >= ?"
        " ORDER BY fetched_at DESC",
        [cutoff],
    ).fetchall()

    av_row = _storage.get_latest_indicator("AV_SENTIMENT")
    av_score = av_row["value"] if av_row else None

    return NewsSentimentResult(
        av_budget_remaining=av_remaining,
        av_sentiment_score=float(av_score) if av_score is not None else None,
        cls_news_count=len(cls_rows),
    ).model_dump()


@mcp.tool()
def get_global_indices(groups: list[str] | None = None) -> dict:
    """Return latest indicator snapshots, optionally filtered by group code."""
    if groups:
        placeholders = ", ".join("?" * len(groups))
        sql = (
            f"SELECT indicator_id, group_code, value, period_date,"
            f" market_tz, value_unit, source"
            f" FROM macro_indicators WHERE group_code IN ({placeholders})"
            f" ORDER BY group_code, indicator_id"
        )
        cur = _storage._conn.execute(sql, groups)
    else:
        sql = (
            "SELECT indicator_id, group_code, value, period_date,"
            " market_tz, value_unit, source"
            " FROM macro_indicators ORDER BY group_code, indicator_id"
        )
        cur = _storage._conn.execute(sql)

    rows = cur.fetchall()
    if rows and isinstance(rows[0], dict):
        row_dicts = rows
    else:
        cols = [d[0] for d in cur.description]
        row_dicts = [dict(zip(cols, row)) for row in rows]

    snapshots = [IndexSnapshot(**r) for r in row_dicts]
    return GlobalIndicesResult(snapshots=snapshots).model_dump()
