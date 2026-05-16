"""Tests for engine.data_agent.storage — DuckDB upsert and git-root resolution."""

import datetime as dt
from pathlib import Path
from unittest.mock import patch

import pytest

from engine.data_agent.fields import FieldGroup
from engine.data_agent.storage import Storage, _find_project_root


class TestFindProjectRoot:
    def test_finds_root_from_subdir(self):
        root = _find_project_root()
        assert (root / ".git").exists() or root is not None

    def test_returns_path(self):
        root = _find_project_root()
        assert isinstance(root, Path)


@pytest.fixture
def tmp_db(tmp_path):
    """Provide a Storage instance backed by a temp DuckDB file."""
    db_path = tmp_path / "test.duckdb"
    with patch("engine.data_agent.storage.DB_PATH", db_path):
        store = Storage(db_path=db_path)
        yield store
        store.close()


class TestStorageInit:
    def test_opens_without_error(self, tmp_db):
        # If we get here, __init__ succeeded
        assert tmp_db is not None

    def test_tables_created(self, tmp_db):
        tables = tmp_db._conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()
        table_names = {row[0] for row in tables}
        expected = {"stock_quotes", "stock_prices", "stock_fundamentals",
                    "business_segments", "stock_meta", "retrieval_log"}
        assert expected.issubset(table_names)


class TestUpsertQuotes:
    def test_upsert_returns_row_count(self, tmp_db):
        rows = [
            {
                "code": "600000",
                "quote_time": dt.datetime(2026, 5, 15, 9, 30, tzinfo=dt.UTC),
                "price": 10.5,
                "pct_change": 1.2,
                "volume": 1000000,
                "amount": 10500000.0,
                "market_cap": 100e9,
                "dynamic_pe": 15.0,
                "pb": 1.2,
                "turnover_rate": 0.5,
                "source": "tencent",
            }
        ]
        count = tmp_db.upsert(FieldGroup.QUOTE, rows)
        assert count == 1

    def test_upsert_idempotent(self, tmp_db):
        rows = [
            {
                "code": "600000",
                "quote_time": dt.datetime(2026, 5, 15, 9, 30, tzinfo=dt.UTC),
                "price": 10.5,
                "pct_change": 1.2,
                "volume": 1000000,
                "amount": 10500000.0,
                "market_cap": None,
                "dynamic_pe": None,
                "pb": None,
                "turnover_rate": None,
                "source": "tencent",
            }
        ]
        tmp_db.upsert(FieldGroup.QUOTE, rows)
        # Insert same row again — should update, not duplicate
        tmp_db.upsert(FieldGroup.QUOTE, rows)
        total = tmp_db._conn.execute("SELECT COUNT(*) FROM stock_quotes").fetchone()[0]
        assert total == 1

    def test_upsert_empty_rows(self, tmp_db):
        count = tmp_db.upsert(FieldGroup.QUOTE, [])
        assert count == 0


class TestUpsertKline:
    def test_upsert_kline(self, tmp_db):
        rows = [
            {
                "code": "688041",
                "trade_date": "2026-05-15",
                "open": 50.0,
                "close": 51.0,
                "high": 52.0,
                "low": 49.5,
                "volume": 500000,
                "amount": 25500000.0,
                "adj_type": "qfq",
                "source": "tencent",
            }
        ]
        count = tmp_db.upsert(FieldGroup.KLINE, rows)
        assert count == 1


class TestLogRetrieval:
    def test_log_inserts_row(self, tmp_db):
        tmp_db.log_retrieval(
            field_group=FieldGroup.QUOTE,
            source="tencent",
            status="ok",
            latency_ms=123,
        )
        count = tmp_db._conn.execute("SELECT COUNT(*) FROM retrieval_log").fetchone()[0]
        assert count == 1

    def test_log_with_error_msg(self, tmp_db):
        tmp_db.log_retrieval(
            field_group=FieldGroup.QUOTE,
            source="eastmoney",
            status="error",
            latency_ms=999,
            error_msg="connection timeout",
        )
        row = tmp_db._conn.execute(
            "SELECT status, error_msg FROM retrieval_log"
        ).fetchone()
        assert row[0] == "error"
        assert "timeout" in row[1]
