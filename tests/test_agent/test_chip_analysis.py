"""TC-037-01..07 — Phase 11 chip_analysis: ChipAnalysis signal model."""

from __future__ import annotations

import duckdb
import pytest
from engine.agent.chip_analysis import (
    ChipAnalysis,
    ChipLockLevel,
    analyze_chip,
    load_and_analyze,
)
from engine.agent.chip_fetcher import ChipBar, ChipDataUnavailable, ChipSummary

# ── DDL ───────────────────────────────────────────────────────────────────────

_CHIP_SUMMARY_DDL = """
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

# ── Mock summaries ─────────────────────────────────────────────────────────────


def _summary_688143() -> ChipSummary:
    """长盈通 688143 mock — current price 131.60 is above 90% band (128.24)."""
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
        bars=[ChipBar(price_lower=60.0, price_upper=70.0, chip_ratio=0.1)],
    )


def _summary_below_band() -> ChipSummary:
    """Mock where current_price (12.0) < range_90_lower (15.0) → below_90_band."""
    return ChipSummary(
        code="000001",
        date="2026-05-20",
        avg_cost=20.0,
        profitable_pct=0.20,
        concentration=55.0,
        range_70_lower=17.0,
        range_70_upper=22.0,
        range_90_lower=15.0,
        range_90_upper=25.0,
        bars=[],
    )


def _summary_in_band() -> ChipSummary:
    """Mock where current_price sits within 90% band."""
    return ChipSummary(
        code="000002",
        date="2026-05-20",
        avg_cost=10.0,
        profitable_pct=0.60,
        concentration=45.0,
        range_70_lower=9.0,
        range_70_upper=13.0,
        range_90_lower=7.0,
        range_90_upper=15.0,
        bars=[],
    )


# ── TC-037-01 ─────────────────────────────────────────────────────────────────


class TestAnalyzeChipAboveBand:
    """TC-037-01: 131.60 > range_90_upper=128.24 → above_90_band=True."""

    def test_above_90_band_true(self):
        result = analyze_chip("688143", 131.60, _summary_688143())
        assert result.above_90_band is True

    def test_below_90_band_false(self):
        result = analyze_chip("688143", 131.60, _summary_688143())
        assert result.below_90_band is False

    def test_cost_deviation_approx_31_7(self):
        result = analyze_chip("688143", 131.60, _summary_688143())
        # (131.60 - 99.96) / 99.96 * 100 ≈ 31.65
        assert abs(result.cost_deviation_pct - 31.65) < 0.5

    def test_chip_lock_level_low(self):
        result = analyze_chip("688143", 131.60, _summary_688143())
        assert result.chip_lock_level == ChipLockLevel.LOW

    def test_returns_chip_analysis_instance(self):
        result = analyze_chip("688143", 131.60, _summary_688143())
        assert isinstance(result, ChipAnalysis)


# ── TC-037-02 ─────────────────────────────────────────────────────────────────


class TestAnalyzeChipBelowBand:
    """TC-037-02: price < range_90_lower → below_90_band=True, signal_summary 含 '套牢'."""

    def test_below_90_band_true(self):
        result = analyze_chip("000001", 12.0, _summary_below_band())
        assert result.below_90_band is True

    def test_above_90_band_false(self):
        result = analyze_chip("000001", 12.0, _summary_below_band())
        assert result.above_90_band is False

    def test_signal_summary_contains_taolao(self):
        result = analyze_chip("000001", 12.0, _summary_below_band())
        assert "套牢" in result.signal_summary


# ── TC-037-03 ─────────────────────────────────────────────────────────────────


class TestChipLockLevel:
    """TC-037-03: concentration thresholds map to correct ChipLockLevel."""

    def _analyze(self, concentration: float) -> ChipAnalysis:
        summary = ChipSummary(
            code="000001", date="2026-05-20",
            avg_cost=10.0, profitable_pct=0.5, concentration=concentration,
            range_70_lower=9.0, range_70_upper=11.0,
            range_90_lower=8.0, range_90_upper=12.0,
            bars=[],
        )
        return analyze_chip("000001", 10.5, summary)

    def test_low_concentration(self):
        assert self._analyze(33.92).chip_lock_level == ChipLockLevel.LOW

    def test_medium_concentration(self):
        assert self._analyze(55.0).chip_lock_level == ChipLockLevel.MEDIUM

    def test_high_concentration(self):
        assert self._analyze(65.0).chip_lock_level == ChipLockLevel.HIGH

    def test_boundary_40_is_medium(self):
        assert self._analyze(40.0).chip_lock_level == ChipLockLevel.MEDIUM

    def test_boundary_60_is_high(self):
        assert self._analyze(60.0).chip_lock_level == ChipLockLevel.HIGH


# ── TC-037-04 ─────────────────────────────────────────────────────────────────


class TestAnalyzeChipPureFunction:
    """TC-037-04: same inputs → same output (no hidden state or randomness)."""

    def test_idempotent_results(self):
        summary = _summary_688143()
        r1 = analyze_chip("688143", 131.60, summary)
        r2 = analyze_chip("688143", 131.60, summary)
        assert r1.model_dump() == r2.model_dump()

    def test_signal_summary_max_80_chars(self):
        result = analyze_chip("688143", 131.60, _summary_688143())
        assert len(result.signal_summary) <= 80


# ── TC-037-05 ─────────────────────────────────────────────────────────────────


class TestLoadAndAnalyzeHappyPath:
    """TC-037-05: load_and_analyze reads from in-memory DuckDB, returns ChipAnalysis."""

    @pytest.fixture
    def conn_with_data(self):
        conn = duckdb.connect(":memory:")
        conn.execute(_CHIP_SUMMARY_DDL)
        conn.execute("""
            INSERT INTO chip_summary VALUES
            ('688143', '2026-05-20', 99.96, 0.9973, 33.92, 80.0, 120.0, 63.28, 128.24)
        """)
        yield conn
        conn.close()

    def test_returns_chip_analysis(self, conn_with_data):
        result = load_and_analyze("688143", 131.60, conn_with_data)
        assert isinstance(result, ChipAnalysis)

    def test_code_matches(self, conn_with_data):
        result = load_and_analyze("688143", 131.60, conn_with_data)
        assert result.code == "688143"

    def test_date_matches_inserted_row(self, conn_with_data):
        result = load_and_analyze("688143", 131.60, conn_with_data)
        assert result.date == "2026-05-20"

    def test_date_none_picks_latest(self):
        conn = duckdb.connect(":memory:")
        conn.execute(_CHIP_SUMMARY_DDL)
        conn.execute("""
            INSERT INTO chip_summary VALUES
            ('688143', '2026-05-18', 98.0, 0.98, 30.0, 75.0, 115.0, 60.0, 125.0),
            ('688143', '2026-05-20', 99.96, 0.9973, 33.92, 80.0, 120.0, 63.28, 128.24)
        """)
        result = load_and_analyze("688143", 131.60, conn, date=None)
        assert result.date == "2026-05-20"
        conn.close()


# ── TC-037-06 ─────────────────────────────────────────────────────────────────


class TestLoadAndAnalyzeNoData:
    """TC-037-06: load_and_analyze with no matching code → ChipDataUnavailable."""

    @pytest.fixture
    def empty_conn(self):
        conn = duckdb.connect(":memory:")
        conn.execute(_CHIP_SUMMARY_DDL)
        yield conn
        conn.close()

    def test_raises_chip_data_unavailable(self, empty_conn):
        with pytest.raises(ChipDataUnavailable):
            load_and_analyze("000000", 10.0, empty_conn)

    def test_exception_contains_code(self, empty_conn):
        try:
            load_and_analyze("000000", 10.0, empty_conn)
        except ChipDataUnavailable as exc:
            assert "000000" in str(exc)


# ── TC-037-07 ─────────────────────────────────────────────────────────────────


class TestAnalyzeChipInvalidAvgCost:
    """TC-037-07: avg_cost <= 0 → ValueError raised (avoid division by zero)."""

    def _summary_zero_cost(self) -> ChipSummary:
        return ChipSummary(
            code="000001", date="2026-05-20",
            avg_cost=0.0,
            profitable_pct=0.5, concentration=40.0,
            range_70_lower=9.0, range_70_upper=11.0,
            range_90_lower=8.0, range_90_upper=12.0,
            bars=[],
        )

    def test_zero_avg_cost_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid avg_cost"):
            analyze_chip("000001", 10.0, self._summary_zero_cost())

    def test_negative_avg_cost_raises_value_error(self):
        summary = self._summary_zero_cost().model_copy(update={"avg_cost": -5.0})
        with pytest.raises(ValueError, match="Invalid avg_cost"):
            analyze_chip("000001", 10.0, summary)
