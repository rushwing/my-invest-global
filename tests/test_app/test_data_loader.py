"""TC-020-01..11 — app.data_loader and app.dashboard integration."""

from __future__ import annotations

import importlib.util
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


class _Stop(Exception):
    """Sentinel raised by patched st.stop() to replicate Streamlit's StopException."""


# Detect availability at collection time — tests are collected regardless,
# but skipped at run-time when the module is not yet implemented.
_has_data_loader = importlib.util.find_spec("app.data_loader") is not None
_skip_dl = pytest.mark.skipif(
    not _has_data_loader, reason="app.data_loader not yet implemented"
)

# Conditional import so the module-level namespace is safe.
if _has_data_loader:
    from app.data_loader import (
        compute_portfolio_metrics,
        load_cloud_capex,
        load_fund_flow_5d,
        load_latest_holdings,
        load_latest_signals,
        load_macro_state,
        load_market_breadth,
        load_news_for_ticker,
        load_ohlcv,
        load_rebalance_history,
        load_recommendations,
        load_scarcity_matrix,
    )


@pytest.fixture(autouse=True)
def _clear_st_cache():
    import streamlit as st
    st.cache_data.clear()
    yield
    st.cache_data.clear()


# ── TC-020-01 ─────────────────────────────────────────────────────────────────


@_skip_dl
class TestDashboardEntrypoint:
    """TC-020-01: app.dashboard.main 可调用，锁定状态下行为正确。

    st.stop() 用 _Stop sentinel 模拟：确保依赖 st.stop() 中断的实现不会因
    no-op patch 而继续执行 tabs 渲染路径，避免误判。
    """

    def _mock_col(self):
        col = MagicMock()
        col.__enter__ = lambda s: col
        col.__exit__ = MagicMock(return_value=False)
        return col

    def _base_patches(self, mock_col, **overrides):
        """Common patch set for locked-state main() calls with _Stop sentinel."""
        return {
            "streamlit.set_page_config": MagicMock(),
            "streamlit.stop": MagicMock(side_effect=_Stop),
            "streamlit.tabs": MagicMock(return_value=[mock_col] * 4),
            "app.dashboard.is_unlocked": MagicMock(return_value=False),
            "app.dashboard.render_sidebar": MagicMock(),
            "app.dashboard.render_locked_mask": MagicMock(),
            "app.dashboard.inject_global_css": MagicMock(),
            **overrides,
        }

    def test_main_is_callable(self):
        from app.dashboard import main
        assert callable(main)

    def test_main_raises_only_stop_sentinel_when_locked(self):
        """main() raises exactly _Stop (sentinel for st.stop()) — no unexpected errors."""
        from app.dashboard import main
        col = self._mock_col()
        with patch("streamlit.set_page_config"), \
             patch("streamlit.stop", side_effect=_Stop), \
             patch("streamlit.tabs", return_value=[col] * 4), \
             patch("app.dashboard.is_unlocked", return_value=False), \
             patch("app.dashboard.render_sidebar"), \
             patch("app.dashboard.render_locked_mask"), \
             patch("app.dashboard.inject_global_css"), \
             pytest.raises(_Stop):
            main()

    def test_locked_state_calls_render_locked_mask(self):
        from app.dashboard import main
        col = self._mock_col()
        with patch("streamlit.set_page_config"), \
             patch("streamlit.stop", side_effect=_Stop), \
             patch("streamlit.tabs", return_value=[col] * 4), \
             patch("app.dashboard.is_unlocked", return_value=False), \
             patch("app.dashboard.render_sidebar"), \
             patch("app.dashboard.render_locked_mask") as mock_locked, \
             patch("app.dashboard.inject_global_css"), \
             pytest.raises(_Stop):
            main()
        mock_locked.assert_called()

    def test_locked_state_sidebar_called_with_locked_true(self):
        from app.dashboard import main
        col = self._mock_col()
        with patch("streamlit.set_page_config"), \
             patch("streamlit.stop", side_effect=_Stop), \
             patch("streamlit.tabs", return_value=[col] * 4), \
             patch("app.dashboard.is_unlocked", return_value=False), \
             patch("app.dashboard.render_sidebar") as mock_sidebar, \
             patch("app.dashboard.render_locked_mask"), \
             patch("app.dashboard.inject_global_css"), \
             pytest.raises(_Stop):
            main()
        mock_sidebar.assert_called_once()
        call_args, call_kwargs = mock_sidebar.call_args
        locked_val = call_kwargs.get("locked", call_args[0] if call_args else None)
        assert locked_val is True, \
            f"render_sidebar must be called with locked=True, got: {mock_sidebar.call_args}"

    def test_locked_state_raises_stop_sentinel(self):
        """_Stop is raised ↔ st.stop() was invoked (sentinel proves the call happened)."""
        from app.dashboard import main
        col = self._mock_col()
        with patch("streamlit.set_page_config"), \
             patch("streamlit.stop", side_effect=_Stop), \
             patch("streamlit.tabs", return_value=[col] * 4), \
             patch("app.dashboard.is_unlocked", return_value=False), \
             patch("app.dashboard.render_sidebar"), \
             patch("app.dashboard.render_locked_mask"), \
             patch("app.dashboard.inject_global_css"):
            pytest.raises(_Stop, main)

    def test_locked_state_does_not_render_tabs(self):
        """st.tabs() must not be called when locked; sentinel prevents fall-through."""
        from app.dashboard import main
        col = self._mock_col()
        with patch("streamlit.set_page_config"), \
             patch("streamlit.stop", side_effect=_Stop), \
             patch("streamlit.tabs") as mock_tabs, \
             patch("app.dashboard.is_unlocked", return_value=False), \
             patch("app.dashboard.render_sidebar"), \
             patch("app.dashboard.render_locked_mask"), \
             patch("app.dashboard.inject_global_css"), \
             pytest.raises(_Stop):
            main()
        mock_tabs.assert_not_called()


# ── TC-020-02 ─────────────────────────────────────────────────────────────────


@_skip_dl
class TestDataRefresh:
    """TC-020-02: 侧边栏 Save 按钮触发 st.cache_data.clear() + st.rerun()。"""

    def test_save_clears_cache_and_reruns(self):
        pytest.importorskip("app.sidebar")
        from app.sidebar import render_sidebar

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


@_skip_dl
class TestCacheTTL:
    """TC-020-03: 所有 loader 函数带 @st.cache_data 装饰器（__wrapped__ 存在）；缓存复用。"""

    def test_all_loaders_have_cache_decorator(self):
        for fn in (
            load_latest_holdings, load_latest_signals, load_recommendations,
            load_macro_state, load_fund_flow_5d, load_market_breadth,
            load_news_for_ticker, load_cloud_capex,
            load_scarcity_matrix, load_rebalance_history,
        ):
            assert hasattr(fn, "__wrapped__"), \
                f"{fn.__name__} must be decorated with @st.cache_data"

    def test_load_ohlcv_has_cache_decorator(self):
        assert hasattr(load_ohlcv, "__wrapped__")

    def test_loaders_all_use_ttl_300(self):
        """Re-import app.data_loader under a spy to verify every @st.cache_data uses ttl=300."""
        import sys
        import importlib
        import streamlit as st

        observed_ttls: list = []
        _real = st.cache_data

        def _spy(*args, **kwargs):
            observed_ttls.append(kwargs.get("ttl"))
            return _real(*args, **kwargs)

        mod_key = "app.data_loader"
        saved = sys.modules.pop(mod_key, None)
        try:
            with patch("streamlit.cache_data", new=_spy):
                importlib.import_module(mod_key)
        finally:
            if saved is not None:
                sys.modules[mod_key] = saved
            else:
                sys.modules.pop(mod_key, None)

        assert len(observed_ttls) >= 8, \
            f"expected ≥8 loaders with @st.cache_data(ttl=300); found {len(observed_ttls)}"
        bad = [t for t in observed_ttls if t != 300]
        assert not bad, \
            f"all loaders must use ttl=300; found other ttl values: {observed_ttls}"

    def test_cache_reuses_result_preventing_double_io(self, tmp_path):
        """load_macro_state: second call with same args must NOT re-execute body (cache hit)."""
        import json
        import streamlit as st
        st.cache_data.clear()

        state_file = tmp_path / "macro_state.json"
        state_file.write_text(json.dumps({"state": "green"}))

        with patch("app.data_loader.Path", return_value=state_file):
            result1 = load_macro_state()

        # Redirect Path to non-existent — cache hit should return stale green, not yellow default
        with patch("app.data_loader.Path", return_value=tmp_path / "gone.json"):
            result2 = load_macro_state()

        assert result1["state"] == "green"
        assert result2["state"] == "green", \
            "second call should return cached value, not re-execute with new Path"

    def test_duckdb_loader_cache_reuse(self):
        """load_market_breadth: duckdb.connect called only once across two calls (cache hit)."""
        import duckdb
        import streamlit as st
        st.cache_data.clear()

        real_conn = duckdb.connect(":memory:")
        try:
            with patch("app.data_loader.duckdb.connect", return_value=real_conn) as mock_connect:
                load_market_breadth(days=5)
                load_market_breadth(days=5)
            assert mock_connect.call_count == 1, (
                f"duckdb.connect should be called only once (2nd call = cache hit); "
                f"called {mock_connect.call_count}x"
            )
        finally:
            real_conn.close()


# ── TC-020-04 ─────────────────────────────────────────────────────────────────


@_skip_dl
class TestMissingFileDegradation:
    """TC-020-04: 无 processed/ 文件 → 函数返回 None/空，不抛异常。"""

    def test_load_latest_signals_returns_none_when_no_files(self):
        with patch("pathlib.Path.glob", return_value=iter([])):
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

    def test_load_latest_holdings_returns_none_when_no_files(self):
        with (
            patch("pathlib.Path.glob", return_value=iter([])),
            patch("pathlib.Path.exists", return_value=False),
        ):
            result = load_latest_holdings()
        assert result is None


# ── TC-020-05 ─────────────────────────────────────────────────────────────────


@_skip_dl
class TestComputePortfolioMetrics:
    """TC-020-05: compute_portfolio_metrics(df, 'yellow') → elastic_target=33。"""

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
        assert abs(compute_portfolio_metrics(sample_df, "yellow")["elastic_pct"] - 30.0) < 0.01

    def test_empty_df_no_zero_division(self):
        empty = pd.DataFrame(columns=["category", "market_value"])
        result = compute_portfolio_metrics(empty, "yellow")
        assert result["elastic_target"] == 33
        assert result["total_mv"] == 0.0
        assert result["white_pct"] == 0.0
        assert result["elastic_pct"] == 0.0


# ── TC-020-06 ─────────────────────────────────────────────────────────────────


@_skip_dl
class TestLoadOhlcv:
    """TC-020-06: load_ohlcv miss → AkShare fallback → write DuckDB → sorted result。"""

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
        unsorted = pd.DataFrame({
            "date": ["2024-01-03", "2024-01-01", "2024-01-02"],
            "open": [10.0] * 3, "high": [11.0] * 3, "low": [9.0] * 3,
            "close": [10.5] * 3, "volume": [1000.0] * 3,
        })
        with patch("app.data_loader.duckdb.connect", return_value=self._empty_con()), \
             patch("app.data_loader.fetch_akshare_history", return_value=unsorted), \
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
        conn.execute(
            "INSERT INTO stock_fund_flow VALUES (?, ?, ?)",
            ["300308", today - timedelta(days=i), float(i + 1)],
        )
    yield conn
    conn.close()


@_skip_dl
class TestLoadFundFlow5d:
    """TC-020-07..09: load_fund_flow_5d empty codes / with data / no table。"""

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
            conn.execute(
                "INSERT INTO stock_quotes VALUES (?, ?, ?)",
                [f"{i:06d}", f"{d} 15:00:00", float((i % 3) - 1)],
            )
    yield conn
    conn.close()


@_skip_dl
class TestLoadMarketBreadth:
    """TC-020-10..11: up_ratio in [0,1]; row count ≤ days; no-table fallback。"""

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
