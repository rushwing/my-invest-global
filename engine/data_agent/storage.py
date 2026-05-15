"""
DuckDB storage layer for the stock data agent.

Database location: <project_root>/data/db/aidc.duckdb
Parquet cache:     <project_root>/data/cache/prices/

Project root is resolved by walking up from this file's location until a .git
directory is found, making the path independent of where scripts are invoked from.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import duckdb

from engine.data_agent.fields import FieldGroup


# ── Path resolution ───────────────────────────────────────────────────────────

def _find_project_root() -> Path:
    """Walk up from this file until a .git directory is found."""
    candidate = Path(__file__).resolve()
    for parent in candidate.parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError(
        f"Could not find project root (.git) starting from {Path(__file__)}"
    )


PROJECT_ROOT = _find_project_root()
DB_PATH      = PROJECT_ROOT / "data" / "db" / "aidc.duckdb"
PARQUET_ROOT = PROJECT_ROOT / "data" / "cache" / "prices"


# ── Schema DDL ────────────────────────────────────────────────────────────────

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS stock_quotes (
    code          TEXT        NOT NULL,
    quote_time    TIMESTAMPTZ NOT NULL,
    price         DOUBLE,
    pct_change    DOUBLE,
    volume        BIGINT,
    amount        DOUBLE,
    market_cap    DOUBLE,
    dynamic_pe    DOUBLE,
    pb            DOUBLE,
    turnover_rate DOUBLE,
    source        TEXT,
    PRIMARY KEY (code, quote_time)
);

CREATE TABLE IF NOT EXISTS stock_prices (
    code        TEXT        NOT NULL,
    trade_date  DATE        NOT NULL,
    open        DOUBLE,
    high        DOUBLE,
    low         DOUBLE,
    close       DOUBLE,
    volume      BIGINT,
    amount      DOUBLE,
    adj_factor  DOUBLE      DEFAULT 1.0,
    adj_type    TEXT,
    source      TEXT,
    fetched_at  TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (code, trade_date, adj_type)
);

CREATE TABLE IF NOT EXISTS stock_fundamentals (
    code         TEXT NOT NULL,
    report_date  DATE NOT NULL,
    period_type  TEXT NOT NULL,
    revenue      DOUBLE,
    net_profit   DOUBLE,
    gross_margin DOUBLE,
    net_margin   DOUBLE,
    roe          DOUBLE,
    roa          DOUBLE,
    eps          DOUBLE,
    bps          DOUBLE,
    debt_ratio   DOUBLE,
    op_cashflow  DOUBLE,
    goodwill     DOUBLE,
    rd_ratio     DOUBLE,
    source       TEXT,
    fetched_at   TIMESTAMPTZ,
    PRIMARY KEY (code, report_date, period_type)
);

CREATE TABLE IF NOT EXISTS business_segments (
    code          TEXT NOT NULL,
    report_date   DATE NOT NULL,
    segment_name  TEXT NOT NULL,
    revenue       DOUBLE,
    profit        DOUBLE,
    revenue_ratio DOUBLE,
    profit_ratio  DOUBLE,
    source        TEXT DEFAULT 'eastmoney',
    PRIMARY KEY (code, report_date, segment_name)
);

CREATE TABLE IF NOT EXISTS stock_meta (
    code       TEXT PRIMARY KEY,
    name       TEXT,
    exchange   TEXT,
    sector     TEXT,
    sub_sector TEXT,
    scarcity   TEXT,
    rating     TEXT,
    rank       INTEGER,
    active     BOOLEAN     DEFAULT TRUE,
    updated_at TIMESTAMPTZ
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

# ── Upsert helpers ────────────────────────────────────────────────────────────

_UPSERT_QUOTES = """
INSERT INTO stock_quotes
    (code, quote_time, price, pct_change, volume, amount,
     market_cap, dynamic_pe, pb, turnover_rate, source)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (code, quote_time) DO UPDATE SET
    price         = excluded.price,
    pct_change    = excluded.pct_change,
    volume        = excluded.volume,
    amount        = excluded.amount,
    market_cap    = excluded.market_cap,
    dynamic_pe    = excluded.dynamic_pe,
    pb            = excluded.pb,
    turnover_rate = excluded.turnover_rate,
    source        = excluded.source
"""

_UPSERT_PRICES = """
INSERT INTO stock_prices
    (code, trade_date, open, high, low, close, volume, amount,
     adj_factor, adj_type, source, fetched_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (code, trade_date, adj_type) DO UPDATE SET
    open       = excluded.open,
    high       = excluded.high,
    low        = excluded.low,
    close      = excluded.close,
    volume     = excluded.volume,
    amount     = excluded.amount,
    adj_factor = excluded.adj_factor,
    source     = excluded.source,
    fetched_at = excluded.fetched_at
"""

_UPSERT_FUNDAMENTALS = """
INSERT INTO stock_fundamentals
    (code, report_date, period_type, revenue, net_profit, gross_margin, net_margin,
     roe, roa, eps, bps, debt_ratio, op_cashflow, goodwill, rd_ratio, source, fetched_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (code, report_date, period_type) DO UPDATE SET
    revenue      = excluded.revenue,
    net_profit   = excluded.net_profit,
    gross_margin = excluded.gross_margin,
    net_margin   = excluded.net_margin,
    roe          = excluded.roe,
    roa          = excluded.roa,
    eps          = excluded.eps,
    bps          = excluded.bps,
    debt_ratio   = excluded.debt_ratio,
    op_cashflow  = excluded.op_cashflow,
    goodwill     = excluded.goodwill,
    rd_ratio     = excluded.rd_ratio,
    source       = excluded.source,
    fetched_at   = excluded.fetched_at
"""

_UPSERT_SEGMENTS = """
INSERT INTO business_segments
    (code, report_date, segment_name, revenue, profit, revenue_ratio, profit_ratio, source)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (code, report_date, segment_name) DO UPDATE SET
    revenue       = excluded.revenue,
    profit        = excluded.profit,
    revenue_ratio = excluded.revenue_ratio,
    profit_ratio  = excluded.profit_ratio,
    source        = excluded.source
"""


# ── Storage class ─────────────────────────────────────────────────────────────

class Storage:
    """
    DuckDB-backed persistence for all field groups.

    Opens (or creates) the database at DB_PATH on construction and initialises
    all tables.  Not thread-safe — intended for single-process use by the
    orchestrator which serialises writes.
    """

    def __init__(self, db_path: Path = DB_PATH) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = duckdb.connect(str(db_path))
        self._conn.execute(_INIT_SQL)

    # ── Public write API ──────────────────────────────────────────────────────

    def upsert_quotes(self, rows: list[dict[str, Any]]) -> int:
        """Upsert a batch of real-time quote snapshots. Returns row count."""
        if not rows:
            return 0
        params = [
            (
                r["code"], r["quote_time"], r.get("price"), r.get("pct_change"),
                r.get("volume"), r.get("amount"), r.get("market_cap"),
                r.get("dynamic_pe"), r.get("pb"), r.get("turnover_rate"),
                r.get("source"),
            )
            for r in rows
        ]
        self._conn.executemany(_UPSERT_QUOTES, params)
        return len(params)

    def upsert_prices(self, rows: list[dict[str, Any]]) -> int:
        """Upsert OHLCV daily price rows."""
        if not rows:
            return 0
        now = dt.datetime.now(tz=dt.timezone.utc)
        params = [
            (
                r["code"], r["trade_date"], r.get("open"), r.get("high"),
                r.get("low"), r.get("close"), r.get("volume"), r.get("amount"),
                r.get("adj_factor", 1.0), r.get("adj_type", "none"),
                r.get("source"), now,
            )
            for r in rows
        ]
        self._conn.executemany(_UPSERT_PRICES, params)
        return len(params)

    def upsert_fundamentals(self, rows: list[dict[str, Any]]) -> int:
        """Upsert quarterly/annual fundamental rows."""
        if not rows:
            return 0
        now = dt.datetime.now(tz=dt.timezone.utc)
        params = [
            (
                r["code"], r["report_date"], r.get("period_type", "Q"),
                r.get("revenue"), r.get("net_profit"), r.get("gross_margin"),
                r.get("net_margin"), r.get("roe"), r.get("roa"),
                r.get("eps"), r.get("bps"), r.get("debt_ratio"),
                r.get("op_cashflow"), r.get("goodwill"), r.get("rd_ratio"),
                r.get("source"), now,
            )
            for r in rows
        ]
        self._conn.executemany(_UPSERT_FUNDAMENTALS, params)
        return len(params)

    def upsert_segments(self, rows: list[dict[str, Any]]) -> int:
        """Upsert business segment rows (主营构成)."""
        if not rows:
            return 0
        params = [
            (
                r["code"], r["report_date"], r["segment_name"],
                r.get("revenue"), r.get("profit"),
                r.get("revenue_ratio"), r.get("profit_ratio"),
                r.get("source", "eastmoney"),
            )
            for r in rows
        ]
        self._conn.executemany(_UPSERT_SEGMENTS, params)
        return len(params)

    def upsert(self, group: FieldGroup, rows: list[dict[str, Any]]) -> int:
        """Dispatch to the correct upsert method by FieldGroup."""
        dispatch = {
            FieldGroup.QUOTE:       self.upsert_quotes,
            FieldGroup.KLINE:       self.upsert_prices,
            FieldGroup.KLINE_MIN:   self.upsert_prices,
            FieldGroup.FUNDAMENTAL: self.upsert_fundamentals,
            FieldGroup.SEGMENT:     self.upsert_segments,
        }
        fn = dispatch.get(group)
        if fn is None:
            return 0  # FUND_FLOW, SHAREHOLDER, ANNOUNCEMENT, INDEX — future tables
        return fn(rows)

    def log_retrieval(
        self,
        field_group: FieldGroup,
        source: str,
        status: str,
        code: str | None = None,
        latency_ms: int = 0,
        error_msg: str | None = None,
    ) -> None:
        """Append one row to retrieval_log."""
        self._conn.execute(
            """
            INSERT INTO retrieval_log
                (code, field_group, source, started_at, latency_ms, status, error_msg)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                code,
                field_group.value if isinstance(field_group, FieldGroup) else field_group,
                source,
                dt.datetime.now(tz=dt.timezone.utc),
                latency_ms,
                status,
                error_msg,
            ),
        )

    # ── Public read API ───────────────────────────────────────────────────────

    def get_last_fetch(
        self,
        group: FieldGroup,
        code: str | None = None,
    ) -> dt.datetime | None:
        """Return the most recent started_at timestamp for a field group (and optionally a stock code)."""
        where = "WHERE field_group = ?"
        params: list[Any] = [group.value]
        if code is not None:
            where += " AND code = ?"
            params.append(code)
        row = self._conn.execute(
            f"SELECT MAX(started_at) FROM retrieval_log {where}", params
        ).fetchone()
        return row[0] if row and row[0] is not None else None

    def query(self, sql: str, params: list[Any] | None = None):
        """Run an arbitrary read query; returns a DuckDB relation."""
        return self._conn.execute(sql, params or [])

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Storage":
        return self

    def __exit__(self, *_) -> None:
        self.close()
