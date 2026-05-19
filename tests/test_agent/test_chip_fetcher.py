"""TC-036-01..05 — Phase 11 chip_fetcher: akshare ingestion + DuckDB storage."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import duckdb
import pandas as pd
import pytest
from engine.agent.chip_fetcher import (
    ChipBar,
    ChipDataUnavailable,
    ChipSummary,
    fetch_chip_summary,
    store_chip_data,
)

# ── DDL (mirrored from REQ-036 so tests are self-contained) ───────────────────

_CHIP_DDL = """
CREATE TABLE IF NOT EXISTS chip_distribution (
    code        TEXT    NOT NULL,
    date        DATE    NOT NULL,
    price_lower REAL    NOT NULL,
    price_upper REAL    NOT NULL,
    chip_ratio  REAL    NOT NULL,
    PRIMARY KEY (code, date, price_lower)
);
CREATE TABLE IF NOT EXISTS chip_summary (
    code           TEXT  NOT NULL,
    date           DATE  NOT NULL,
    avg_cost       REAL  NOT NULL,
    profitable_pct REAL  NOT NULL,
    concentration  REAL  NOT NULL,
    range_70_lower REAL  NOT NULL,
    range_70_upper REAL  NOT NULL,
    range_90_lower REAL  NOT NULL,
    range_90_upper REAL  NOT NULL,
    PRIMARY KEY (code, date)
);
"""

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mem_conn():
    """In-memory DuckDB with chip tables pre-created."""
    conn = duckdb.connect(":memory:")
    conn.execute(_CHIP_DDL)
    yield conn
    conn.close()


def _make_standard_df() -> pd.DataFrame:
    """Full-column mock of ak.stock_cyq_em for 688143 (2026-05-20).

    Columns mirror REQ-036 _AKSHARE_COLUMN_MAP. Each row represents one price
    level; summary columns repeat across rows (implementer picks last/any row).
    Note: actual akshare column names must be confirmed during smoke test.
    """
    price_levels = [60, 70, 80, 90, 100, 110, 120, 130]
    rows = []
    for i, p in enumerate(price_levels):
        rows.append({
            "价格": float(p),
            "筹码占比": round(0.08 + i * 0.01, 3),
            "获利比例": 99.73,   # summary — same across rows
            "平均成本": 99.96,
            "90成本-低": 63.28,
            "90成本-高": 128.24,
            "70成本-低": 80.0,
            "70成本-高": 120.0,
            "集中度": 33.92,
        })
    return pd.DataFrame(rows)


def _make_no_optional_cols_df() -> pd.DataFrame:
    """DataFrame missing 70成本-低/高 and 集中度 (TC-036-05 fallback scenario)."""
    return pd.DataFrame([{
        "价格": 100.0,
        "筹码占比": 0.1,
        "获利比例": 80.0,
        "平均成本": 95.0,
        "90成本-低": 70.0,
        "90成本-高": 115.0,
    }])


# ── TC-036-01 ─────────────────────────────────────────────────────────────────


class TestFetchChipSummaryBasic:
    """TC-036-01: mock ak.stock_cyq_em → ChipSummary with correct field values."""

    def test_returns_chip_summary_instance(self):
        ak_stub = ModuleType("akshare")
        ak_stub.stock_cyq_em = MagicMock(return_value=_make_standard_df())
        with patch.dict(sys.modules, {"akshare": ak_stub}):
            result = fetch_chip_summary("688143")
        assert isinstance(result, ChipSummary)

    def test_avg_cost_positive(self):
        ak_stub = ModuleType("akshare")
        ak_stub.stock_cyq_em = MagicMock(return_value=_make_standard_df())
        with patch.dict(sys.modules, {"akshare": ak_stub}):
            result = fetch_chip_summary("688143")
        assert result.avg_cost > 0

    def test_profitable_pct_in_range(self):
        ak_stub = ModuleType("akshare")
        ak_stub.stock_cyq_em = MagicMock(return_value=_make_standard_df())
        with patch.dict(sys.modules, {"akshare": ak_stub}):
            result = fetch_chip_summary("688143")
        assert 0 < result.profitable_pct <= 1

    def test_bars_nonempty(self):
        ak_stub = ModuleType("akshare")
        ak_stub.stock_cyq_em = MagicMock(return_value=_make_standard_df())
        with patch.dict(sys.modules, {"akshare": ak_stub}):
            result = fetch_chip_summary("688143")
        assert len(result.bars) > 0

    def test_field_values_match_mock(self):
        ak_stub = ModuleType("akshare")
        ak_stub.stock_cyq_em = MagicMock(return_value=_make_standard_df())
        with patch.dict(sys.modules, {"akshare": ak_stub}):
            result = fetch_chip_summary("688143")
        assert abs(result.avg_cost - 99.96) < 0.01
        assert abs(result.range_90_lower - 63.28) < 0.01
        assert abs(result.range_90_upper - 128.24) < 0.01
        assert abs(result.concentration - 33.92) < 0.01

    def test_code_set_correctly(self):
        ak_stub = ModuleType("akshare")
        ak_stub.stock_cyq_em = MagicMock(return_value=_make_standard_df())
        with patch.dict(sys.modules, {"akshare": ak_stub}):
            result = fetch_chip_summary("688143")
        assert result.code == "688143"


# ── TC-036-02 ─────────────────────────────────────────────────────────────────


class TestStoreChipDataWrite:
    """TC-036-02: store_chip_data writes chip_summary and chip_distribution to DuckDB."""

    def _make_summary(self) -> ChipSummary:
        return ChipSummary(
            code="688143",
            date="2026-05-20",
            avg_cost=99.96,
            profitable_pct=0.9973,
            concentration=33.92,
            range_70_lower=80.0,
            range_70_upper=120.0,
            range_90_lower=63.28,
            range_90_upper=128.24,
            bars=[
                ChipBar(price_lower=60.0, price_upper=70.0, chip_ratio=0.08),
                ChipBar(price_lower=70.0, price_upper=80.0, chip_ratio=0.10),
            ],
        )

    def test_chip_summary_row_written(self, mem_conn):
        store_chip_data(mem_conn, self._make_summary())
        rows = mem_conn.execute(
            "SELECT * FROM chip_summary WHERE code='688143'"
        ).fetchall()
        assert len(rows) >= 1

    def test_chip_summary_fields_correct(self, mem_conn):
        store_chip_data(mem_conn, self._make_summary())
        row = mem_conn.execute(
            "SELECT avg_cost, profitable_pct, range_90_lower, range_90_upper "
            "FROM chip_summary WHERE code='688143'"
        ).fetchone()
        assert row is not None
        avg_cost, profitable_pct, r90_lo, r90_hi = row
        assert abs(avg_cost - 99.96) < 0.01
        assert abs(profitable_pct - 0.9973) < 0.0001
        assert abs(r90_lo - 63.28) < 0.01
        assert abs(r90_hi - 128.24) < 0.01

    def test_chip_distribution_rows_written(self, mem_conn):
        store_chip_data(mem_conn, self._make_summary())
        rows = mem_conn.execute(
            "SELECT * FROM chip_distribution WHERE code='688143'"
        ).fetchall()
        assert len(rows) == 2  # two bars in mock


# ── TC-036-03 ─────────────────────────────────────────────────────────────────


class TestStoreChipDataUpsert:
    """TC-036-03: double write for same (code, date) does not raise (UPSERT)."""

    def _make_summary(self, avg_cost: float = 99.96) -> ChipSummary:
        return ChipSummary(
            code="688143",
            date="2026-05-20",
            avg_cost=avg_cost,
            profitable_pct=0.9973,
            concentration=33.92,
            range_70_lower=80.0,
            range_70_upper=120.0,
            range_90_lower=63.28,
            range_90_upper=128.24,
            bars=[ChipBar(price_lower=60.0, price_upper=70.0, chip_ratio=0.1)],
        )

    def test_second_write_does_not_raise(self, mem_conn):
        store_chip_data(mem_conn, self._make_summary(99.96))
        store_chip_data(mem_conn, self._make_summary(100.00))  # same (code, date)
        # should not raise

    def test_second_write_updates_value(self, mem_conn):
        store_chip_data(mem_conn, self._make_summary(99.96))
        store_chip_data(mem_conn, self._make_summary(100.00))
        row = mem_conn.execute(
            "SELECT avg_cost FROM chip_summary WHERE code='688143'"
        ).fetchone()
        assert row is not None
        assert abs(row[0] - 100.00) < 0.01


# ── TC-036-04 ─────────────────────────────────────────────────────────────────


class TestFetchChipSummaryEmpty:
    """TC-036-04: empty akshare DataFrame → ChipDataUnavailable raised."""

    def test_raises_chip_data_unavailable(self):
        ak_stub = ModuleType("akshare")
        ak_stub.stock_cyq_em = MagicMock(return_value=pd.DataFrame())
        with patch.dict(sys.modules, {"akshare": ak_stub}):
            with pytest.raises(ChipDataUnavailable):
                fetch_chip_summary("688143")

    def test_does_not_return_none(self):
        ak_stub = ModuleType("akshare")
        ak_stub.stock_cyq_em = MagicMock(return_value=pd.DataFrame())
        with patch.dict(sys.modules, {"akshare": ak_stub}):
            result = None
            try:
                result = fetch_chip_summary("688143")
            except ChipDataUnavailable:
                pass
        assert result is None


# ── TC-036-05 ─────────────────────────────────────────────────────────────────


class TestFetchChipSummaryFallback:
    """TC-036-05: missing optional columns → fallback values, no exception."""

    def test_no_exception_on_missing_optional_cols(self):
        ak_stub = ModuleType("akshare")
        ak_stub.stock_cyq_em = MagicMock(return_value=_make_no_optional_cols_df())
        with patch.dict(sys.modules, {"akshare": ak_stub}):
            result = fetch_chip_summary("300308")
        assert isinstance(result, ChipSummary)

    def test_range_70_fallback_equals_range_90(self):
        """When 70成本 columns missing, range_70 should fall back to range_90."""
        ak_stub = ModuleType("akshare")
        ak_stub.stock_cyq_em = MagicMock(return_value=_make_no_optional_cols_df())
        with patch.dict(sys.modules, {"akshare": ak_stub}):
            result = fetch_chip_summary("300308")
        assert result.range_70_lower == result.range_90_lower
        assert result.range_70_upper == result.range_90_upper

    def test_concentration_fallback_is_valid_range(self):
        """When 集中度 missing, computed fallback must be in [0, 100]."""
        ak_stub = ModuleType("akshare")
        ak_stub.stock_cyq_em = MagicMock(return_value=_make_no_optional_cols_df())
        with patch.dict(sys.modules, {"akshare": ak_stub}):
            result = fetch_chip_summary("300308")
        assert 0 <= result.concentration <= 100
