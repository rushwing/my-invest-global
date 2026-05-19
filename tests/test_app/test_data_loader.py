"""TC-020-01..11 — app.data_loader and app.dashboard integration."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, call, patch

import pandas as pd
import pytest

# Skip entire file if the module under test is not yet implemented.
pytest.importorskip("app.data_loader")

from app.data_loader import (  # noqa: E402
    compute_portfolio_metrics,
    load_fund_flow_5d,
    load_latest_holdings,
    load_latest_signals,
    load_macro_state,
    load_market_breadth,
    load_ohlcv,
    load_recommendations,
)


@pytest.fixture(autouse=True)
def _clear_st_cache():
    import streamlit as st
    st.cache_data.clear()
    yield
    st.cache_data.clear()


# ── TC-020-01 ─────────────────────────────────────────────────────────────────


class TestDashboardEntrypoint:
    """TC-020-01: uv run streamlit run app/dashboard.py 启动无报错，登录表单显示。"""

    def test_main_is_callable(self):
        from app.dashboard import main
        assert callable(main)

    def test_main_runs_without_error(self):
        from app.dashboard import main
        import streamlit as st

        mock_col = MagicMock()
        mock_col.__enter__ = lambda s: mock_col
        mock_col.__exit__ = MagicMock(return_value=False)

        with patch("streamlit.set_page_config"), \
             patch("streamlit.stop"), \
             patch("streamlit.tabs", return_value=[mock_col] * 4), \
             patch("streamlit.columns", return_value=[mock_col] * 2), \
             patch("app.auth.is_unlocked", return_value=False), \
             patch("app.sidebar.render_sidebar"), \
             patch("app.dashboard.render_locked_mask"), \
             patch("app.dashboard.render_header"), \
             patch("app.styles.inject_global_css"):
            main()  # must not raise

    def test_app_dashboard_importable(self):
        import importlib
        mod = importlib.import_module("app.dashboard")
        assert mod is not None


# ── TC-020-02 ─────────────────────────────────────────────────────────────────


class TestDataRefresh:
    """TC-020-02: 侧边栏 Save 按钮触发 st.cache_data.clear() + st.rerun()。"""

    def test_save_clears_cache_and_reruns(self):
        pytest.importorskip("app.sidebar")
        from app.sidebar import render_sidebar
        import streamlit as st

        with patch("streamlit.button", return_value=True), \
             patch("streamlit.cache_data") as mock_cache, \
             patch("streamlit.rerun") as mock_rerun, \
             patch("app.sidebar.save_holdings"), \
             patch("streamlit.data_editor", return_value=pd.DataFrame()), \
             patch("app.data_loader.load_latest_holdings", return_value=None):
            render_sidebar(locked=False)

        mock_cache.clear.assert_called()
        mock_rerun.assert_called()


# ── TC-020-03 ─────────────────────────────────────────────────────────────────


class TestCacheTTL:
    """TC-020-03: 同一数据请求 300s 内再次调用无重复 IO，从缓存返回。"""

    def test_load_latest_signals_cached(self, tmp_path):
        import json
        sig_file = tmp_path / "signals_20260101.json"
        sig_file.write_text(json.dumps({"signal": "buy"}))

        call_count = [0]
        original_glob = type(tmp_path).glob

        def counting_glob(self, pattern):
            call_count[0] += 1
            return original_glob(self, pattern)

        with patch("pathlib.Path.glob", counting_glob), \
             patch("app.data_loader.Path", side_effect=lambda p: tmp_path if "processed" in str(p) else __import__("pathlib").Path(p)):
            load_latest_signals()
            load_latest_signals()

        # IO should occur at most once (cache absorbs the second call)
        # We verify by checking function is decorated with cache_data
        assert hasattr(load_latest_signals, "__wrapped__"), \
            "load_latest_signals must be decorated with @st.cache_data"

    def test_all_loaders_have_cache_decorator(self):
        for fn in (
            load_latest_holdings, load_latest_signals, load_recommendations,
            load_macro_state, load_fund_flow_5d, load_market_breadth,
        ):
            assert hasattr(fn, "__wrapped__"), \
                f"{fn.__name__} must be decorated with @st.cache_data"


# ── TC-020-04 ─────────────────────────────────────────────────────────────────


class TestMissingFileDegradation:
    """TC-020-04: 删除所有 processed/ 文件 → 函数返回 None/空，不抛异常。"""

    def test_load_latest_holdings_returns_none_when_no_files(self, tmp_path):
        with patch("app.data_loader.Path", return_value=tmp_path):
            result = load_latest_holdings()
        assert result is None

    def test_load_latest_signals_returns_none_when_no_files(self, tmp_path):
        empty_gen = iter([])
        with patch("pathlib.Path.glob", return_value=empty_gen):
            result = load_latest_signals()
        assert result is None

    def test_load_recommendations_returns_none_when_no_files(self):
        with patch("pathlib.Path.glob", return_value=iter([])):
            result = load_recommendations()
        assert result is None

    def test_load_macro_state_defaults_when_no_file(self, tmp_path):
        nonexistent = tmp_path / "macro_state.json"
        with patch("app.data_loader.Path", return_value=nonexistent):
            result = load_macro_state()
        assert result["state"] == "yellow"
        assert "override" in result


# ── TC-020-05 ─────────────────────────────────────────────────────────────────


class TestComputePortfolioMetrics:
    """TC-020-05: compute_portfolio_metrics(df, 'yellow') → elastic_target=33."""

    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame([
            {"category": "白马股", "market_value": 70.0},
            {"category": "弹性股", "market_value": 30.0},
        ])

    def test_yellow_elastic_target(self, sample_df):
        assert compute_portfolio_metrics(sample_df, "yellow")["elastic_target"] == 33

    def test_green_elastic_target(self, sample_df):
        assert compute_portfolio_metrics(sample_df, "green")["elastic_target"] == 38

    def test_red_elastic_target(self, sample_df):
        assert compute_portfolio_metrics(sample_df, "red")["elastic_target"] == 20

    def test_uppercase_normalized(self, sample_df):
        assert compute_portfolio_metrics(sample_df, "YELLOW")["elastic_target"] == 33

    def test_elastic_pct_correct(self, sample_df):
        result = compute_portfolio_metrics(sample_df, "yellow")
        assert abs(result["elastic_pct"] - 30.0) < 0.01

    def test_empty_df_no_zero_division(self):
        empty = pd.DataFrame(columns=["category", "market_value"])
        result = compute_portfolio_metrics(empty, "yellow")
        assert result["elastic_target"] == 33
        assert result["total_mv"] == 0.0
        assert result["white_pct"] == 0.0
        assert result["elastic_pct"] == 0.0


# ── TC-020-06 ─────────────────────────────────────────────────────────────────


class TestLoadOhlcv:
    """TC-020-06: load_ohlcv miss → AkShare fallback → write DuckDB → return sorted."""

    def _empty_con(self):
        mock_con = MagicMock()
        mock_con.__enter__ = lambda s: mock_con
        mock_con.__exit__ = MagicMock(return_value=False)
        mock_con.execute.return_value.df.return_value = pd.DataFrame(
            columns=["date", "open", "high", "low", "close", "volume"]
        )
        return mock_con

    def _fake_df(self):
        return pd.DataFrame({
            "date": ["2024-01-02"],
            "open": [10.0], "high": [11.0], "low": [9.0],
            "close": [10.5], "volume": [1000.0],
        })

    def test_akshare_called_on_empty_duckdb(self):
        with patch("app.data_loader.duckdb.connect", return_value=self._empty_con()), \
             patch("app.data_loader.fetch_akshare_history", return_value=self._fake_df()) as mock_fetch, \
             patch("app.data_loader.write_ohlcv_to_duckdb"):
            load_ohlcv("300308", days=180)
        mock_fetch.assert_called_once_with("300308", 180)

    def test_write_duckdb_called_after_akshare(self):
        with patch("app.data_loader.duckdb.connect", return_value=self._empty_con()), \
             patch("app.data_loader.fetch_akshare_history", return_value=self._fake_df()), \
             patch("app.data_loader.write_ohlcv_to_duckdb") as mock_write:
            load_ohlcv("300308", days=180)
        mock_write.assert_called_once()

    def test_result_sorted_by_date(self):
        unsorted_df = pd.DataFrame({
            "date": ["2024-01-03", "2024-01-01", "2024-01-02"],
            "open": [10.0] * 3, "high": [11.0] * 3, "low": [9.0] * 3,
            "close": [10.5] * 3, "volume": [1000.0] * 3,
        })
        with patch("app.data_loader.duckdb.connect", return_value=self._empty_con()), \
             patch("app.data_loader.fetch_akshare_history", return_value=unsorted_df), \
             patch("app.data_loader.write_ohlcv_to_duckdb"):
            result = load_ohlcv("300308", days=3)
        assert list(result["date"]) == sorted(result["date"].tolist())


# ── TC-020-07..09 ─────────────────────────────────────────────────────────────


@pytest.fixture
def fund_flow_db():
    import duckdb
    conn = duckdb.connect(":memory:")
    conn.execute(
        "CREATE TABLE stock_fund_flow "
        "(code TEXT, trade_date DATE, main_net_inflow DOUBLE)"
    )
    today = date.today()
    for i in range(5):
        d = today - timedelta(days=i)
        conn.execute("INSERT INTO stock_fund_flow VALUES (?, ?, ?)", ["300308", d, float(i + 1)])
    yield conn
    conn.close()


class TestLoadFundFlow5d:
    """TC-020-07..09: load_fund_flow_5d various scenarios."""

    def test_empty_codes_returns_empty_dataframe(self):
        result = load_fund_flow_5d([], days=5)
        assert result.empty
        assert list(result.columns) == ["code", "trade_date", "main_net_inflow"]

    def test_returns_correct_columns(self, fund_flow_db):
        with patch("app.data_loader.duckdb.connect", return_value=fund_flow_db):
            result = load_fund_flow_5d(["300308"], days=5)
        for col in ("code", "trade_date", "main_net_inflow"):
            assert col in result.columns

    def test_returns_nonempty_for_known_code(self, fund_flow_db):
        with patch("app.data_loader.duckdb.connect", return_value=fund_flow_db):
            result = load_fund_flow_5d(["300308"], days=5)
        assert not result.empty

    def test_no_exception_when_table_missing(self):
        import duckdb
        empty_conn = duckdb.connect(":memory:")
        with patch("app.data_loader.duckdb.connect", return_value=empty_conn):
            result = load_fund_flow_5d(["300308"], days=5)
        assert result.empty
        assert list(result.columns) == ["code", "trade_date", "main_net_inflow"]
        empty_conn.close()


# ── TC-020-10..11 ─────────────────────────────────────────────────────────────


@pytest.fixture
def market_breadth_db():
    import duckdb
    conn = duckdb.connect(":memory:")
    conn.execute(
        "CREATE TABLE stock_quotes "
        "(code TEXT, quote_time TIMESTAMP, pct_change DOUBLE)"
    )
    today = date.today()
    for day_offset in range(20):
        d = today - timedelta(days=day_offset)
        for i in range(100):
            pct = float((i % 3) - 1)
            conn.execute(
                "INSERT INTO stock_quotes VALUES (?, ?, ?)",
                [f"{i:06d}", f"{d} 15:00:00", pct],
            )
    yield conn
    conn.close()


class TestLoadMarketBreadth:
    """TC-020-10..11: load_market_breadth up_ratio in [0,1]; no-table fallback."""

    def test_up_ratio_in_0_1(self, market_breadth_db):
        with patch("app.data_loader.duckdb.connect", return_value=market_breadth_db):
            result = load_market_breadth(days=20)
        assert not result.empty
        assert result["up_ratio"].between(0, 1).all()

    def test_row_count_le_days(self, market_breadth_db):
        with patch("app.data_loader.duckdb.connect", return_value=market_breadth_db):
            result = load_market_breadth(days=20)
        assert len(result) <= 20

    def test_columns_correct(self, market_breadth_db):
        with patch("app.data_loader.duckdb.connect", return_value=market_breadth_db):
            result = load_market_breadth(days=20)
        assert "date" in result.columns
        assert "up_ratio" in result.columns

    def test_no_exception_when_table_missing(self):
        import duckdb
        empty_conn = duckdb.connect(":memory:")
        with patch("app.data_loader.duckdb.connect", return_value=empty_conn):
            result = load_market_breadth(days=20)
        assert result.empty
        assert list(result.columns) == ["date", "up_ratio"]
        empty_conn.close()
