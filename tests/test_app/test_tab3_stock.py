"""TC-018-01..10 — Tab 3 个股深度分析: compute_indicators + session_state preselect."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


# ── Synthetic OHLCV helper ────────────────────────────────────────────────────


def _make_ohlcv(n: int = 200, seed: int = 42) -> pd.DataFrame:
    """Return n rows of deterministic OHLCV with a realistic random walk."""
    rng = np.random.default_rng(seed)
    close = 100.0 + np.cumsum(rng.normal(0, 0.5, n))
    close = np.maximum(close, 5.0)
    noise = np.abs(rng.normal(0, 0.005, n))
    high = close * (1 + noise)
    low = close * (1 - noise)
    open_ = close * (1 + rng.normal(0, 0.003, n))
    volume = np.abs(rng.normal(5_000_000, 500_000, n))
    dates = pd.date_range("2023-06-01", periods=n, freq="B")
    return pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    })


# ── TC-018-01 ─────────────────────────────────────────────────────────────────


class TestComputeIndicatorsRSI:
    """TC-018-01: rsi14 all non-null values in [0,100]; NaN rows ≤ 13."""

    def test_rsi_non_null_in_range(self):
        from app.data_loader import compute_indicators
        df = _make_ohlcv(200)
        result = compute_indicators(df)
        non_null = result["rsi14"].dropna()
        assert len(non_null) > 0
        assert non_null.between(0, 100).all(), "rsi14 out of [0,100] range"

    def test_rsi_warmup_nan_count_le_13(self):
        from app.data_loader import compute_indicators
        df = _make_ohlcv(200)
        result = compute_indicators(df)
        nan_count = result["rsi14"].isna().sum()
        assert nan_count <= 13, f"rsi14 warm-up NaN count {nan_count} > 13"

    def test_rsi_column_present(self):
        from app.data_loader import compute_indicators
        df = _make_ohlcv(50)
        result = compute_indicators(df)
        assert "rsi14" in result.columns

    def test_insufficient_rows_no_exception(self):
        from app.data_loader import compute_indicators
        df = _make_ohlcv(5)
        result = compute_indicators(df)
        assert "rsi14" in result.columns
        assert result["rsi14"].isna().all()


# ── TC-018-02 ─────────────────────────────────────────────────────────────────


class TestComputeIndicatorsBollinger:
    """TC-018-02: bb_upper > bb_mid > bb_lower strictly from row 20 onwards."""

    def test_bb_order_from_row_20(self):
        from app.data_loader import compute_indicators
        df = _make_ohlcv(200)
        result = compute_indicators(df)
        tail = result.iloc[19:].dropna(subset=["bb_upper", "bb_mid", "bb_lower"])
        assert len(tail) > 0, "no non-null BB rows from row 20"
        assert (tail["bb_upper"] > tail["bb_mid"]).all(), "bb_upper not always > bb_mid"
        assert (tail["bb_mid"] > tail["bb_lower"]).all(), "bb_mid not always > bb_lower"

    def test_bb_columns_present(self):
        from app.data_loader import compute_indicators
        df = _make_ohlcv(200)
        result = compute_indicators(df)
        for col in ("bb_upper", "bb_mid", "bb_lower"):
            assert col in result.columns


# ── TC-018-03 ─────────────────────────────────────────────────────────────────


class TestMacdGoldenCross:
    """TC-018-03: MACD上穿信号线处检测到金叉。"""

    def test_golden_cross_detected(self):
        from app.data_loader import compute_indicators
        df = _make_ohlcv(200)
        result = compute_indicators(df).dropna(subset=["macd", "macd_signal"])
        golden = result[
            (result["macd"] > result["macd_signal"])
            & (result["macd"].shift(1) <= result["macd_signal"].shift(1))
        ]
        assert len(golden) >= 1, "expected at least one golden cross in 200-row data"

    def test_macd_columns_present(self):
        from app.data_loader import compute_indicators
        df = _make_ohlcv(200)
        result = compute_indicators(df)
        for col in ("macd", "macd_signal", "macd_hist"):
            assert col in result.columns


# ── TC-018-04 ─────────────────────────────────────────────────────────────────


class TestMacdDeathCross:
    """TC-018-04: MACD下穿信号线处检测到死叉。"""

    def test_death_cross_detected(self):
        from app.data_loader import compute_indicators
        df = _make_ohlcv(200)
        result = compute_indicators(df).dropna(subset=["macd", "macd_signal"])
        death = result[
            (result["macd"] < result["macd_signal"])
            & (result["macd"].shift(1) >= result["macd_signal"].shift(1))
        ]
        assert len(death) >= 1, "expected at least one death cross in 200-row data"


# ── TC-018-05 ─────────────────────────────────────────────────────────────────


class TestTierColors:
    """TC-018-05: TIER_COLORS[2] == '#F5A623'."""

    def test_tier2_color(self):
        from app.components.tab3_stock import TIER_COLORS
        assert TIER_COLORS[2] == "#F5A623"

    def test_tier1_color(self):
        from app.components.tab3_stock import TIER_COLORS
        assert TIER_COLORS[1] == "#FF7A1A"

    def test_tier3_color(self):
        from app.components.tab3_stock import TIER_COLORS
        assert TIER_COLORS[3] == "#9AA0AC"

    def test_tier4_color(self):
        from app.components.tab3_stock import TIER_COLORS
        assert TIER_COLORS[4] == "#4F8EF7"


# ── TC-018-06 ─────────────────────────────────────────────────────────────────


class TestNewsTimeline:
    """TC-018-06: news_df with >8 rows → at most 8 displayed."""

    def test_at_most_8_news_shown(self):
        from app.components.tab3_stock import render_news_timeline
        news_df = pd.DataFrame([
            {
                "title": f"News {i}",
                "source": "TestSource",
                "published_at": "2026-01-01T10:00:00",
                "sentiment": "positive",
                "relevance_score": 0.9,
            }
            for i in range(12)
        ])
        rendered_calls = []
        import streamlit as st
        from unittest.mock import patch
        with patch("streamlit.markdown") as mock_md:
            render_news_timeline(news_df)
        assert mock_md.call_count <= 8


# ── TC-018-07 ─────────────────────────────────────────────────────────────────


class TestSwitchTickerReloads:
    """TC-018-07: switching ticker reloads chart with no cross-contamination."""

    def test_compute_indicators_independent_per_ticker(self):
        from app.data_loader import compute_indicators
        df_a = _make_ohlcv(200, seed=1)
        df_b = _make_ohlcv(200, seed=2)
        result_a = compute_indicators(df_a)
        result_b = compute_indicators(df_b)
        # Different input → different output (not sharing state)
        assert not result_a["close"].equals(result_b["close"])
        assert not result_a["rsi14"].equals(result_b["rsi14"])


# ── TC-018-08 ─────────────────────────────────────────────────────────────────


class TestDateRangeCutoff:
    """TC-018-08: 选择1M → x轴显示最近30天。"""

    def test_1m_filter_returns_30_days(self):
        from app.components.tab3_stock import filter_by_date_range
        df = _make_ohlcv(200)
        result = filter_by_date_range(df, "1M")
        assert len(result) <= 31, f"1M should return ≤31 rows, got {len(result)}"
        assert len(result) >= 1

    def test_3m_filter_returns_90_days(self):
        from app.components.tab3_stock import filter_by_date_range
        df = _make_ohlcv(200)
        result = filter_by_date_range(df, "3M")
        assert len(result) <= 93


# ── TC-018-09..10 ─────────────────────────────────────────────────────────────


class TestSessionStatePreselect:
    """TC-018-09/10: tab3_code session_state preselect and auto-clear."""

    def test_preselect_value_popped(self):
        import streamlit as st
        from unittest.mock import patch, MagicMock

        # Simulate session_state with preselected code
        session_state = {"tab3_code": "300308"}

        def fake_pop(key, default=None):
            return session_state.pop(key, default)

        with patch("streamlit.session_state", session_state), \
             patch("streamlit.selectbox", return_value="300308") as mock_selectbox, \
             patch("streamlit.plotly_chart"), \
             patch("streamlit.markdown"), \
             patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]), \
             patch("app.data_loader.load_ohlcv", return_value=_make_ohlcv(200)), \
             patch("app.data_loader.load_news_for_ticker", return_value=pd.DataFrame()), \
             patch("app.data_loader.load_scarcity_matrix", return_value=pd.DataFrame(columns=["code", "rank"])), \
             patch("app.data_loader.compute_indicators", side_effect=lambda df: df):
            from app.components.tab3_stock import render_tab3
            render_tab3()

        # After render, tab3_code should be consumed
        assert "tab3_code" not in session_state

    def test_preselect_used_as_selectbox_index(self):
        from app.components.tab3_stock import get_preselect_code
        import streamlit as st
        from unittest.mock import patch

        session_state = {"tab3_code": "688143"}
        with patch("streamlit.session_state", session_state):
            code = get_preselect_code()
        assert code == "688143"

    def test_no_preselect_returns_none(self):
        from app.components.tab3_stock import get_preselect_code
        from unittest.mock import patch

        with patch("streamlit.session_state", {}):
            code = get_preselect_code()
        assert code is None
