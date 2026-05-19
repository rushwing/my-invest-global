"""TC-018-01..10 — Tab 3 个股深度分析: indicators, Plotly markers, session_state."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

# Skip entire file if data_loader (primary dependency) not yet implemented.
pytest.importorskip("app.data_loader")

from app.data_loader import compute_indicators  # noqa: E402


# ── Synthetic OHLCV helper ────────────────────────────────────────────────────


def _make_ohlcv(n: int = 200, seed: int = 42) -> pd.DataFrame:
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
        "open": open_, "high": high, "low": low,
        "close": close, "volume": volume,
    })


# ── TC-018-01 ─────────────────────────────────────────────────────────────────


class TestComputeIndicatorsRSI:
    """TC-018-01: rsi14 all non-null values in [0,100]; warm-up NaN ≤ 13."""

    def test_rsi_non_null_in_range(self):
        df = compute_indicators(_make_ohlcv(200))
        non_null = df["rsi14"].dropna()
        assert len(non_null) > 0
        assert non_null.between(0, 100).all()

    def test_rsi_warmup_nan_count_le_13(self):
        df = compute_indicators(_make_ohlcv(200))
        assert df["rsi14"].isna().sum() <= 13

    def test_rsi_column_present(self):
        assert "rsi14" in compute_indicators(_make_ohlcv(50)).columns

    def test_insufficient_rows_returns_all_nan_rsi(self):
        result = compute_indicators(_make_ohlcv(5))
        assert "rsi14" in result.columns
        assert result["rsi14"].isna().all()


# ── TC-018-02 ─────────────────────────────────────────────────────────────────


class TestComputeIndicatorsBollinger:
    """TC-018-02: bb_upper > bb_mid > bb_lower strictly from row 20 onwards."""

    def test_bb_order_from_row_20(self):
        result = compute_indicators(_make_ohlcv(200))
        tail = result.iloc[19:].dropna(subset=["bb_upper", "bb_mid", "bb_lower"])
        assert len(tail) > 0
        assert (tail["bb_upper"] > tail["bb_mid"]).all()
        assert (tail["bb_mid"] > tail["bb_lower"]).all()

    def test_bb_columns_present(self):
        result = compute_indicators(_make_ohlcv(200))
        for col in ("bb_upper", "bb_mid", "bb_lower"):
            assert col in result.columns


# ── TC-018-03 ─────────────────────────────────────────────────────────────────


class TestMacdGoldenCrossPlotly:
    """TC-018-03: 金叉 Plotly trace has green circle markers at crossover dates."""

    def test_golden_cross_trace_color_and_symbol(self):
        tab3 = pytest.importorskip("app.components.tab3_stock")
        df = compute_indicators(_make_ohlcv(200))
        fig = tab3.build_stock_chart(df)

        golden_trace = next((t for t in fig.data if t.name == "金叉"), None)
        assert golden_trace is not None, "figure must contain a trace named '金叉'"
        assert golden_trace.marker.color == "#00C47A"
        assert golden_trace.marker.symbol == "circle"

    def test_golden_cross_dates_are_actual_crossovers(self):
        tab3 = pytest.importorskip("app.components.tab3_stock")
        df = compute_indicators(_make_ohlcv(200)).dropna(subset=["macd", "macd_signal"])
        fig = tab3.build_stock_chart(df)

        golden_trace = next((t for t in fig.data if t.name == "金叉"), None)
        if golden_trace is None or len(golden_trace.x) == 0:
            pytest.skip("no golden cross in test data")

        # Every date in the golden trace must be a real crossover date
        expected_dates = set(
            df.loc[
                (df["macd"] > df["macd_signal"])
                & (df["macd"].shift(1) <= df["macd_signal"].shift(1)),
                "date",
            ]
        )
        for d in golden_trace.x:
            assert str(d) in expected_dates or d in expected_dates, \
                f"golden cross marker date {d} is not a real crossover"

    def test_golden_trace_has_at_least_one_marker(self):
        tab3 = pytest.importorskip("app.components.tab3_stock")
        df = compute_indicators(_make_ohlcv(200))
        fig = tab3.build_stock_chart(df)
        golden_trace = next((t for t in fig.data if t.name == "金叉"), None)
        assert golden_trace is not None
        assert len(golden_trace.x) >= 1


# ── TC-018-04 ─────────────────────────────────────────────────────────────────


class TestMacdDeathCrossPlotly:
    """TC-018-04: 死叉 Plotly trace has red circle markers at crossover dates."""

    def test_death_cross_trace_color_and_symbol(self):
        tab3 = pytest.importorskip("app.components.tab3_stock")
        df = compute_indicators(_make_ohlcv(200))
        fig = tab3.build_stock_chart(df)

        death_trace = next((t for t in fig.data if t.name == "死叉"), None)
        assert death_trace is not None, "figure must contain a trace named '死叉'"
        assert death_trace.marker.color == "#E84040"
        assert death_trace.marker.symbol == "circle"

    def test_death_cross_dates_are_actual_crossovers(self):
        tab3 = pytest.importorskip("app.components.tab3_stock")
        df = compute_indicators(_make_ohlcv(200)).dropna(subset=["macd", "macd_signal"])
        fig = tab3.build_stock_chart(df)

        death_trace = next((t for t in fig.data if t.name == "死叉"), None)
        if death_trace is None or len(death_trace.x) == 0:
            pytest.skip("no death cross in test data")

        expected_dates = set(
            df.loc[
                (df["macd"] < df["macd_signal"])
                & (df["macd"].shift(1) >= df["macd_signal"].shift(1)),
                "date",
            ]
        )
        for d in death_trace.x:
            assert str(d) in expected_dates or d in expected_dates, \
                f"death cross marker date {d} is not a real crossover"


# ── TC-018-05 ─────────────────────────────────────────────────────────────────


class TestTierColors:
    """TC-018-05: TIER_COLORS[2] == '#F5A623'."""

    def test_tier_colors(self):
        tab3 = pytest.importorskip("app.components.tab3_stock")
        assert tab3.TIER_COLORS[1] == "#FF7A1A"
        assert tab3.TIER_COLORS[2] == "#F5A623"
        assert tab3.TIER_COLORS[3] == "#9AA0AC"
        assert tab3.TIER_COLORS[4] == "#4F8EF7"


# ── TC-018-06 ─────────────────────────────────────────────────────────────────


class TestNewsTimeline:
    """TC-018-06: news_df > 8 rows → at most 8 displayed."""

    def test_at_most_8_news_shown(self):
        tab3 = pytest.importorskip("app.components.tab3_stock")
        from unittest.mock import patch as _patch

        news_df = pd.DataFrame([
            {
                "title": f"News {i}", "source": "TestSource",
                "published_at": "2026-01-01T10:00:00",
                "sentiment": "positive", "relevance_score": 0.9,
            }
            for i in range(12)
        ])
        with _patch("streamlit.markdown") as mock_md:
            tab3.render_news_timeline(news_df)
        assert mock_md.call_count <= 8


# ── TC-018-07 ─────────────────────────────────────────────────────────────────


class TestSwitchTickerReloads:
    """TC-018-07: switching ticker rebuilds chart with no cross-contamination."""

    def test_different_ticker_different_chart(self):
        tab3 = pytest.importorskip("app.components.tab3_stock")
        df_a = compute_indicators(_make_ohlcv(200, seed=1))
        df_b = compute_indicators(_make_ohlcv(200, seed=99))
        fig_a = tab3.build_stock_chart(df_a)
        fig_b = tab3.build_stock_chart(df_b)
        # Different data → different candlestick trace y-values
        candle_a = next(t for t in fig_a.data if t.type == "candlestick")
        candle_b = next(t for t in fig_b.data if t.type == "candlestick")
        assert list(candle_a.close) != list(candle_b.close)


# ── TC-018-08 ─────────────────────────────────────────────────────────────────


class TestDateRangeCutoff:
    """TC-018-08: 选择 1M → x轴显示最近 30 天。"""

    def test_1m_filter_returns_at_most_31_rows(self):
        tab3 = pytest.importorskip("app.components.tab3_stock")
        df = _make_ohlcv(200)
        result = tab3.filter_by_date_range(df, "1M")
        assert len(result) <= 31

    def test_6m_filter_returns_more_than_1m(self):
        tab3 = pytest.importorskip("app.components.tab3_stock")
        df = _make_ohlcv(200)
        assert len(tab3.filter_by_date_range(df, "6M")) > len(tab3.filter_by_date_range(df, "1M"))


# ── TC-018-09..10 ─────────────────────────────────────────────────────────────


class TestSessionStatePreselect:
    """TC-018-09/10: tab3_code preselect consumed after render_tab3."""

    def test_get_preselect_code_reads_session_state(self):
        tab3 = pytest.importorskip("app.components.tab3_stock")
        from unittest.mock import patch as _patch
        with _patch("streamlit.session_state", {"tab3_code": "300308"}):
            code = tab3.get_preselect_code()
        assert code == "300308"

    def test_get_preselect_code_returns_none_when_absent(self):
        tab3 = pytest.importorskip("app.components.tab3_stock")
        from unittest.mock import patch as _patch
        with _patch("streamlit.session_state", {}):
            code = tab3.get_preselect_code()
        assert code is None

    def test_tab3_code_cleared_from_session_state(self):
        tab3 = pytest.importorskip("app.components.tab3_stock")
        from unittest.mock import patch as _patch, MagicMock as _MM

        session = {"tab3_code": "300308"}
        mock_col = _MM()
        mock_col.__enter__ = lambda s: mock_col
        mock_col.__exit__ = _MM(return_value=False)

        with _patch("streamlit.session_state", session), \
             _patch("streamlit.selectbox", return_value="300308"), \
             _patch("streamlit.plotly_chart"), \
             _patch("streamlit.markdown"), \
             _patch("streamlit.columns", return_value=[mock_col] * 2), \
             _patch("app.data_loader.load_ohlcv", return_value=_make_ohlcv(200)), \
             _patch("app.data_loader.load_news_for_ticker", return_value=pd.DataFrame()), \
             _patch("app.data_loader.load_scarcity_matrix",
                    return_value=pd.DataFrame(columns=["code", "rank"])), \
             _patch("app.data_loader.compute_indicators", side_effect=lambda df: df):
            tab3.render_tab3()

        assert "tab3_code" not in session
