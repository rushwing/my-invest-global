"""MacroRegime — three-pillar macro gate computation and cache."""

from __future__ import annotations

import datetime as dt
import json
import logging
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

from engine.data_agent.storage import _find_project_root
from engine.macro_agent.storage import MacroStorage

log = logging.getLogger(__name__)

_UTC = ZoneInfo("UTC")

# Staleness threshold: more than 4 calendar days ≈ > 3 trading days
_YIELD_STALE_DAYS = 4

# Big-4 cloud CapEx companies
_BIG4 = ["MSFT", "AMZN", "GOOGL", "META"]


class MacroRegime:
    """Computes three-pillar macro gate state and persists to DuckDB + JSON cache."""

    def __init__(self, storage: MacroStorage) -> None:
        self._storage = storage
        self._cache_path: Path = _find_project_root() / "data" / "macro_state.json"

    def compute(self, as_of: date) -> dict:
        """Compute regime state for as_of date and persist to macro_regime table."""
        capex_state, capex_as_of = self._capex_pillar(as_of)
        yield_state, yield_as_of = self._yield_pillar(as_of)
        risk_state = self._risk_pillar(as_of)

        # Stale short-circuits composite
        if any(s == "stale" for s in (capex_state, yield_state, risk_state)):
            composite = "stale"
        elif any(s in ("red", "inverted") for s in (capex_state, yield_state, risk_state)):
            composite = "red"
        elif capex_state == "green" and yield_state == "normal" and risk_state == "risk_on":
            composite = "green"
        else:
            composite = "yellow"

        result = {
            "as_of_date": as_of,
            "capex_state": capex_state,
            "yield_curve_state": yield_state,
            "risk_state": risk_state,
            "composite_state": composite,
            "capex_as_of": str(capex_as_of) if capex_as_of else None,
            "yield_as_of": yield_as_of,
            "computed_at": dt.datetime.now(tz=_UTC),
        }
        self._storage.upsert_regime(result)
        return result

    def write_cache(self, state: dict) -> None:
        """Write composite state to JSON file, respecting manual overrides."""
        path = self._cache_path
        if path.exists():
            try:
                existing = json.loads(path.read_text())
                if not existing.get("auto_computed"):
                    return  # manual override — leave untouched
            except (json.JSONDecodeError, OSError):
                pass  # corrupted → overwrite

        out = {
            "state": state.get("composite_state"),
            "auto_computed": True,
            "capex_as_of": state.get("capex_as_of"),
            "yield_as_of": str(state["yield_as_of"]) if state.get("yield_as_of") else None,
            "computed_at": state.get("computed_at"),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out, indent=2))

    # ── Private pillars ───────────────────────────────────────────────────────

    def _capex_pillar(self, as_of: date) -> tuple[str, date | None]:
        qoq_list: list[float] = []
        for company in _BIG4:
            rows = self._storage.get_capex_quarters(company, 2)
            if len(rows) < 2:
                continue
            cur = rows[0].get("capex_usd")
            prev = rows[1].get("capex_usd")
            if cur is not None and prev is not None and prev != 0:
                qoq_list.append((cur - prev) / prev * 100)

        if not qoq_list:
            return "stale", None

        avg_qoq = sum(qoq_list) / len(qoq_list)
        if avg_qoq < -10:
            return "red", as_of
        if avg_qoq >= 0:
            return "green", as_of
        return "yellow", as_of

    def _yield_pillar(self, as_of: date) -> tuple[str, date | None]:
        dgs10_row = self._storage._conn.execute(
            "SELECT value, period_date FROM macro_indicators"
            " WHERE indicator_id='DGS10' ORDER BY period_date DESC LIMIT 1"
        ).fetchone()
        dgs2_row = self._storage._conn.execute(
            "SELECT value, period_date FROM macro_indicators"
            " WHERE indicator_id='DGS2' ORDER BY period_date DESC LIMIT 1"
        ).fetchone()

        if dgs10_row is None or dgs2_row is None:
            return "stale", None

        v10, d10 = dgs10_row
        v2, d2 = dgs2_row
        latest_period = max(d10, d2)

        if (as_of - latest_period).days > _YIELD_STALE_DAYS:
            return "stale", latest_period

        spread = v10 - v2
        if spread < 0:
            return "inverted", latest_period
        return "normal", latest_period

    def _risk_pillar(self, as_of: date) -> str:
        sox_cur = self._storage._conn.execute(
            "SELECT value FROM macro_indicators WHERE indicator_id='^SOX'"
            " AND period_date <= ? ORDER BY period_date DESC LIMIT 1",
            [as_of],
        ).fetchone()
        if sox_cur is None:
            return "stale"

        sox_hist = self._storage._conn.execute(
            "SELECT value FROM macro_indicators WHERE indicator_id='^SOX'"
            " AND period_date < ? ORDER BY period_date DESC LIMIT 20",
            [as_of],
        ).fetchall()
        if len(sox_hist) < 20:
            return "stale"

        ma_20 = sum(r[0] for r in sox_hist) / 20
        sox_above_ma = sox_cur[0] > ma_20

        sentiment_row = self._storage._conn.execute(
            "SELECT value FROM macro_indicators WHERE indicator_id='AV_SENTIMENT'"
            " AND period_date <= ? ORDER BY period_date DESC LIMIT 1",
            [as_of],
        ).fetchone()
        sentiment = sentiment_row[0] if sentiment_row and sentiment_row[0] is not None else 0.0

        if sox_above_ma and sentiment > 0:
            return "risk_on"
        return "risk_off"
