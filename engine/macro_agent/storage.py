"""MacroStorage — DuckDB persistence for macro agent tables.

Database: <project_root>/data/db/aidc.duckdb (shared with data_agent).
Pass db_path=":memory:" in tests; pass None to use the default project path.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import duckdb

from engine.data_agent.storage import _find_project_root

# ── Schema DDL ────────────────────────────────────────────────────────────────

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS macro_indicators (
    indicator_id    TEXT        NOT NULL,
    group_code      TEXT        NOT NULL,
    period_date     DATE        NOT NULL,
    market_tz       TEXT        NOT NULL,
    value           DOUBLE,
    value_unit      TEXT,
    value_raw       TEXT,
    source          TEXT,
    realtime_start  DATE,
    vintage_as_of   DATE,
    utc_ts          TIMESTAMPTZ NOT NULL,
    fetched_at      TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (indicator_id, period_date, source)
);

CREATE TABLE IF NOT EXISTS capex_quarterly (
    company         TEXT        NOT NULL,
    cik             TEXT        NOT NULL,
    fiscal_quarter  TEXT        NOT NULL,
    period_end      DATE        NOT NULL,
    capex_usd       DOUBLE,
    capex_yoy_pct   DOUBLE,
    filing_form     TEXT,
    source          TEXT,
    source_hash     TEXT,
    fetched_at      TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (company, fiscal_quarter, source)
);

CREATE TABLE IF NOT EXISTS fomc_calendar (
    meeting_date    DATE        PRIMARY KEY,
    meeting_type    TEXT,
    decision_date   DATE,
    rate_decision   TEXT,
    target_lower    DOUBLE,
    target_upper    DOUBLE,
    source          TEXT,
    updated_at      TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS macro_regime (
    as_of_date          DATE        PRIMARY KEY,
    capex_state         TEXT,
    yield_curve_state   TEXT,
    risk_state          TEXT,
    composite_state     TEXT,
    capex_as_of         TEXT,
    yield_as_of         DATE,
    computed_at         TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS alpha_vantage_budget (
    date            DATE        PRIMARY KEY,
    requests_used   INT         NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS release_dates (
    indicator_id    TEXT        NOT NULL,
    release_date    DATE        NOT NULL,
    source          TEXT,
    PRIMARY KEY (indicator_id, release_date)
);

CREATE SEQUENCE IF NOT EXISTS retrieval_log_id_seq;

CREATE TABLE IF NOT EXISTS retrieval_log (
    id          BIGINT      DEFAULT nextval('retrieval_log_id_seq') PRIMARY KEY,
    code        TEXT,
    field_group TEXT,
    source      TEXT,
    started_at  TIMESTAMPTZ,
    latency_ms  INTEGER,
    status      TEXT,
    error_msg   TEXT
);
"""

# ── Upsert SQL ────────────────────────────────────────────────────────────────

_UPSERT_INDICATORS = """
INSERT INTO macro_indicators
    (indicator_id, group_code, period_date, market_tz, value, value_unit,
     value_raw, source, realtime_start, vintage_as_of, utc_ts, fetched_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (indicator_id, period_date, source) DO UPDATE SET
    group_code     = excluded.group_code,
    market_tz      = excluded.market_tz,
    value          = excluded.value,
    value_unit     = excluded.value_unit,
    value_raw      = excluded.value_raw,
    realtime_start = excluded.realtime_start,
    vintage_as_of  = excluded.vintage_as_of,
    utc_ts         = excluded.utc_ts,
    fetched_at     = excluded.fetched_at
"""

_UPSERT_CAPEX = """
INSERT INTO capex_quarterly
    (company, cik, fiscal_quarter, period_end, capex_usd, capex_yoy_pct,
     filing_form, source, source_hash, fetched_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (company, fiscal_quarter, source) DO UPDATE SET
    cik           = excluded.cik,
    period_end    = excluded.period_end,
    capex_usd     = excluded.capex_usd,
    capex_yoy_pct = excluded.capex_yoy_pct,
    filing_form   = excluded.filing_form,
    source_hash   = excluded.source_hash,
    fetched_at    = excluded.fetched_at
"""

_UPSERT_FOMC = """
INSERT INTO fomc_calendar
    (meeting_date, meeting_type, decision_date, rate_decision,
     target_lower, target_upper, source, updated_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (meeting_date) DO UPDATE SET
    meeting_type  = excluded.meeting_type,
    decision_date = excluded.decision_date,
    rate_decision = excluded.rate_decision,
    target_lower  = excluded.target_lower,
    target_upper  = excluded.target_upper,
    source        = excluded.source,
    updated_at    = excluded.updated_at
"""

_UPSERT_REGIME = """
INSERT INTO macro_regime
    (as_of_date, capex_state, yield_curve_state, risk_state,
     composite_state, capex_as_of, yield_as_of, computed_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (as_of_date) DO UPDATE SET
    capex_state       = excluded.capex_state,
    yield_curve_state = excluded.yield_curve_state,
    risk_state        = excluded.risk_state,
    composite_state   = excluded.composite_state,
    capex_as_of       = excluded.capex_as_of,
    yield_as_of       = excluded.yield_as_of,
    computed_at       = excluded.computed_at
"""


# ── MacroStorage ──────────────────────────────────────────────────────────────

class MacroStorage:
    """DuckDB-backed persistence for macro agent tables.

    Shares the same DuckDB file as data_agent.Storage but manages its own
    connection instance (DuckDB supports multiple connections to one file).
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            resolved = _find_project_root() / "data" / "db" / "aidc.duckdb"
            resolved.parent.mkdir(parents=True, exist_ok=True)
            connect_str = str(resolved)
        elif str(db_path) == ":memory:":
            connect_str = ":memory:"
        else:
            resolved = Path(db_path)
            resolved.parent.mkdir(parents=True, exist_ok=True)
            connect_str = str(resolved)

        self._conn = duckdb.connect(connect_str)
        self._conn.execute(_INIT_SQL)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _fetchone_as_dict(self, sql: str, params: list[Any]) -> dict | None:
        cur = self._conn.execute(sql, params)
        row = cur.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))

    def _fetchall_as_dicts(self, sql: str, params: list[Any]) -> list[dict]:
        cur = self._conn.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    # ── Write API ─────────────────────────────────────────────────────────────

    def upsert_indicators(self, records: list[dict]) -> int:
        if not records:
            return 0
        params = [
            (
                r["indicator_id"], r["group_code"], r["period_date"], r["market_tz"],
                r.get("value"), r.get("value_unit"), r.get("value_raw"), r.get("source"),
                r.get("realtime_start"), r.get("vintage_as_of"), r["utc_ts"], r["fetched_at"],
            )
            for r in records
        ]
        self._conn.executemany(_UPSERT_INDICATORS, params)
        return len(params)

    def upsert_capex(self, records: list[dict]) -> int:
        if not records:
            return 0
        params = [
            (
                r["company"], r["cik"], r["fiscal_quarter"], r["period_end"],
                r.get("capex_usd"), r.get("capex_yoy_pct"), r.get("filing_form"),
                r.get("source"), r.get("source_hash"), r["fetched_at"],
            )
            for r in records
        ]
        self._conn.executemany(_UPSERT_CAPEX, params)
        return len(params)

    def upsert_fomc(self, records: list[dict]) -> int:
        if not records:
            return 0
        params = [
            (
                r["meeting_date"], r.get("meeting_type"), r.get("decision_date"),
                r.get("rate_decision"), r.get("target_lower"), r.get("target_upper"),
                r.get("source"), r.get("updated_at"),
            )
            for r in records
        ]
        self._conn.executemany(_UPSERT_FOMC, params)
        return len(params)

    def upsert_regime(self, record: dict) -> None:
        self._conn.execute(
            _UPSERT_REGIME,
            (
                record["as_of_date"], record.get("capex_state"),
                record.get("yield_curve_state"), record.get("risk_state"),
                record.get("composite_state"), record.get("capex_as_of"),
                record.get("yield_as_of"), record["computed_at"],
            ),
        )

    def increment_av_budget(self, d: date) -> None:
        self._conn.execute(
            """
            INSERT INTO alpha_vantage_budget (date, requests_used)
            VALUES (?, 1)
            ON CONFLICT (date) DO UPDATE SET requests_used = requests_used + 1
            """,
            [d],
        )

    # ── Read API ──────────────────────────────────────────────────────────────

    def get_latest_indicator(
        self, indicator_id: str, source: str | None = None
    ) -> dict | None:
        if source is None:
            return self._fetchone_as_dict(
                "SELECT * FROM macro_indicators WHERE indicator_id = ?"
                " ORDER BY fetched_at DESC LIMIT 1",
                [indicator_id],
            )
        return self._fetchone_as_dict(
            "SELECT * FROM macro_indicators WHERE indicator_id = ? AND source = ?"
            " ORDER BY fetched_at DESC LIMIT 1",
            [indicator_id, source],
        )

    def get_capex_quarters(self, company: str, n: int = 4) -> list[dict]:
        return self._fetchall_as_dicts(
            "SELECT * FROM capex_quarterly WHERE company = ?"
            " ORDER BY period_end DESC LIMIT ?",
            [company, n],
        )

    def get_fomc_upcoming(self, from_date: date, lookahead_days: int = 90) -> list[dict]:
        end_date = from_date + timedelta(days=lookahead_days)
        return self._fetchall_as_dicts(
            "SELECT * FROM fomc_calendar"
            " WHERE meeting_date >= ? AND meeting_date <= ?"
            " ORDER BY meeting_date ASC",
            [from_date, end_date],
        )

    def get_regime_latest(self) -> dict | None:
        return self._fetchone_as_dict(
            "SELECT * FROM macro_regime ORDER BY as_of_date DESC LIMIT 1",
            [],
        )

    def get_av_budget(self, d: date) -> int:
        row = self._conn.execute(
            "SELECT requests_used FROM alpha_vantage_budget WHERE date = ?", [d]
        ).fetchone()
        return row[0] if row is not None else 0

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> MacroStorage:
        return self

    def __exit__(self, *_) -> None:
        self.close()
