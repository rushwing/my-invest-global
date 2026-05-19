"""TC-020-05..11 — app.data_loader pure compute and DuckDB loaders."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def _clear_st_cache():
    import streamlit as st
    st.cache_data.clear()
    yield
    st.cache_data.clear()


# ── TC-020-05 ─────────────────────────────────────────────────────────────────


class TestComputePortfolioMetrics:
    """TC-020-05: compute_portfolio_metrics returns elastic_target=33 for yellow."""

    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame([
            {"category": "白马股", "market_value": 70.0},
            {"category": "弹性股", "market_value": 30.0},
        ])

    def test_yellow_elastic_target(self, sample_df):
        from app.data_loader import compute_portfolio_metrics
        result = compute_portfolio_metrics(sample_df, "yellow")
        assert result["elastic_target"] == 33

    def test_green_elastic_target(self, sample_df):
        from app.data_loader import compute_portfolio_metrics
        result = compute_portfolio_metrics(sample_df, "green")
        assert result["elastic_target"] == 38

    def test_red_elastic_target(self, sample_df):
        from app.data_loader import compute_portfolio_metrics
        result = compute_portfolio_metrics(sample_df, "red")
        assert result["elastic_target"] == 20

    def test_uppercase_input_normalized(self, sample_df):
        from app.data_loader import compute_portfolio_metrics
        result = compute_portfolio_metrics(sample_df, "YELLOW")
        assert result["elastic_target"] == 33

    def test_elastic_pct_computed(self, sample_df):
        from app.data_loader import compute_portfolio_metrics
        result = compute_portfolio_metrics(sample_df, "yellow")
        assert abs(result["elastic_pct"] - 30.0) < 0.01

    def test_total_mv_computed(self, sample_df):
        from app.data_loader import compute_portfolio_metrics
        result = compute_portfolio_metrics(sample_df, "yellow")
        assert result["total_mv"] == pytest.approx(100.0)

    def test_empty_df_no_zero_division(self):
        from app.data_loader import compute_portfolio_metrics
        empty = pd.DataFrame(columns=["category", "market_value"])
        result = compute_portfolio_metrics(empty, "yellow")
        assert result["elastic_target"] == 33
        assert result["total_mv"] == 0.0
        assert result["white_pct"] == 0.0
        assert result["elastic_pct"] == 0.0

    def test_zero_total_mv_no_zero_division(self):
        from app.data_loader import compute_portfolio_metrics
        df = pd.DataFrame([{"category": "白马股", "market_value": 0.0}])
        result = compute_portfolio_metrics(df, "yellow")
        assert result["total_mv"] == 0.0
        assert result["elastic_target"] == 33


# ── TC-020-06 ─────────────────────────────────────────────────────────────────


class TestLoadOhlcv:
    """TC-020-06: load_ohlcv falls back to AkShare when DuckDB returns empty."""

    def _empty_df_con(self):
        mock_con = MagicMock()
        mock_con.__enter__ = lambda s: mock_con
        mock_con.__exit__ = MagicMock(return_value=False)
        mock_con.execute.return_value.df.return_value = pd.DataFrame(
            columns=["date", "open", "high", "low", "close", "volume"]
        )
        return mock_con

    def test_akshare_called_on_empty_duckdb(self):
        fake_df = pd.DataFrame({
            "date": ["2024-01-02"],
            "open": [10.0], "high": [11.0], "low": [9.0],
            "close": [10.5], "volume": [1000.0],
        })
        with patch("app.data_loader.duckdb.connect", return_value=self._empty_df_con()), \
             patch("app.data_loader.fetch_akshare_history", return_value=fake_df) as mock_fetch, \
             patch("app.data_loader.write_ohlcv_to_duckdb"):
            from app.data_loader import load_ohlcv
            result = load_ohlcv("300308", days=180)
        mock_fetch.assert_called_once_with("300308", 180)
        assert not result.empty

    def test_returns_sorted_by_date(self):
        fake_df = pd.DataFrame({
            "date": ["2024-01-03", "2024-01-01", "2024-01-02"],
            "open": [10.0, 9.0, 9.5],
            "high": [11.0, 10.0, 10.5],
            "low": [9.0, 8.5, 9.0],
            "close": [10.5, 9.5, 10.0],
            "volume": [1000.0, 900.0, 950.0],
        })
        with patch("app.data_loader.duckdb.connect", return_value=self._empty_df_con()), \
             patch("app.data_loader.fetch_akshare_history", return_value=fake_df), \
             patch("app.data_loader.write_ohlcv_to_duckdb"):
            from app.data_loader import load_ohlcv
            result = load_ohlcv("300308", days=180)
        assert list(result["date"]) == sorted(result["date"].tolist())


# ── TC-020-07..09 ─────────────────────────────────────────────────────────────


@pytest.fixture
def fund_flow_db():
    """In-memory DuckDB with stock_fund_flow table (5 days of data for 300308)."""
    import duckdb
    conn = duckdb.connect(":memory:")
    conn.execute(
        "CREATE TABLE stock_fund_flow "
        "(code TEXT, trade_date DATE, main_net_inflow DOUBLE)"
    )
    today = date.today()
    for i in range(5):
        d = today - timedelta(days=i)
        conn.execute(
            "INSERT INTO stock_fund_flow VALUES (?, ?, ?)",
            ["300308", d, float(i + 1)],
        )
    yield conn
    conn.close()


class TestLoadFundFlow5d:
    """TC-020-07..09: load_fund_flow_5d various scenarios."""

    def test_empty_codes_returns_empty_dataframe(self):
        from app.data_loader import load_fund_flow_5d
        result = load_fund_flow_5d([], days=5)
        assert result.empty
        assert list(result.columns) == ["code", "trade_date", "main_net_inflow"]

    def test_returns_correct_columns(self, fund_flow_db):
        with patch("app.data_loader.duckdb.connect", return_value=fund_flow_db):
            from app.data_loader import load_fund_flow_5d
            result = load_fund_flow_5d(["300308"], days=5)
        assert "code" in result.columns
        assert "trade_date" in result.columns
        assert "main_net_inflow" in result.columns

    def test_returns_nonempty_for_known_code(self, fund_flow_db):
        with patch("app.data_loader.duckdb.connect", return_value=fund_flow_db):
            from app.data_loader import load_fund_flow_5d
            result = load_fund_flow_5d(["300308"], days=5)
        assert not result.empty

    def test_no_exception_when_table_missing(self):
        """TC-020-09: DuckDB has no stock_fund_flow table → empty DataFrame."""
        import duckdb
        empty_conn = duckdb.connect(":memory:")  # no table created
        with patch("app.data_loader.duckdb.connect", return_value=empty_conn):
            from app.data_loader import load_fund_flow_5d
            result = load_fund_flow_5d(["300308"], days=5)
        assert result.empty
        assert list(result.columns) == ["code", "trade_date", "main_net_inflow"]
        empty_conn.close()


# ── TC-020-10..11 ─────────────────────────────────────────────────────────────


@pytest.fixture
def market_breadth_db():
    """In-memory DuckDB with stock_quotes table (20 days × 100 stocks)."""
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
            pct = (i % 3) - 1  # -1, 0, +1 cycling
            conn.execute(
                "INSERT INTO stock_quotes VALUES (?, ?, ?)",
                [f"{i:06d}", f"{d} 15:00:00", float(pct)],
            )
    yield conn
    conn.close()


class TestLoadMarketBreadth:
    """TC-020-10..11: load_market_breadth various scenarios."""

    def test_up_ratio_in_0_1(self, market_breadth_db):
        with patch("app.data_loader.duckdb.connect", return_value=market_breadth_db):
            from app.data_loader import load_market_breadth
            result = load_market_breadth(days=20)
        assert not result.empty
        assert result["up_ratio"].between(0, 1).all()

    def test_row_count_le_days(self, market_breadth_db):
        with patch("app.data_loader.duckdb.connect", return_value=market_breadth_db):
            from app.data_loader import load_market_breadth
            result = load_market_breadth(days=20)
        assert len(result) <= 20

    def test_columns_correct(self, market_breadth_db):
        with patch("app.data_loader.duckdb.connect", return_value=market_breadth_db):
            from app.data_loader import load_market_breadth
            result = load_market_breadth(days=20)
        assert "date" in result.columns
        assert "up_ratio" in result.columns

    def test_no_exception_when_table_missing(self):
        """TC-020-11: DuckDB has no stock_quotes → empty DataFrame."""
        import duckdb
        empty_conn = duckdb.connect(":memory:")
        with patch("app.data_loader.duckdb.connect", return_value=empty_conn):
            from app.data_loader import load_market_breadth
            result = load_market_breadth(days=20)
        assert result.empty
        assert list(result.columns) == ["date", "up_ratio"]
        empty_conn.close()
