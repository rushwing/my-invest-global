"""TC-035-01..04: REQ-035 回测框架测试。"""

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


def _make_ohlcv(periods: int = 45, trend: str = "v") -> pd.DataFrame:
    """构造带趋势转折的 mock OHLCV，保证 MA/MACD 有机会产生交叉信号。"""
    dates = pd.date_range("2024-01-01", periods=periods, freq="D")
    if trend == "v" and periods >= 45:
        close = np.r_[np.linspace(100, 92, 20), np.linspace(93, 125, periods - 20)]
    elif trend == "wave" and periods >= 70:
        close = np.r_[
            np.linspace(120, 90, 25),
            np.linspace(91, 135, 30),
            np.linspace(134, 110, periods - 55),
        ]
    else:
        close = np.linspace(100, 120, periods)
    return pd.DataFrame(
        {
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": [1_000_000] * periods,
        },
        index=dates,
    )


# ---------------------------------------------------------------------------
# TC-035-01: run_backtest(ma_cross) 返回 BacktestResult 并处理输入边界
# ---------------------------------------------------------------------------


class TestRunBacktestMaCross:
    def test_returns_backtest_result_structure(self) -> None:
        from engine.backtest.runner import BacktestResult, run_backtest

        df = _make_ohlcv(45, "v")
        result = run_backtest(code="300308", strategy="ma_cross", df=df)

        assert isinstance(result, BacktestResult)
        assert result.code == "300308"
        assert result.strategy == "ma_cross"
        assert isinstance(result.total_return, float)
        assert isinstance(result.benchmark_return, float)
        assert isinstance(result.max_drawdown, float)
        assert isinstance(result.win_rate, float)
        assert isinstance(result.num_trades, int)
        assert isinstance(result.equity_curve, pd.Series)

    def test_equity_curve_length_and_index(self) -> None:
        from engine.backtest.runner import run_backtest

        df = _make_ohlcv(45, "v")
        result = run_backtest(code="300308", strategy="ma_cross", df=df)

        assert len(result.equity_curve) == len(df)
        assert result.equity_curve.index.equals(df.index)
        assert result.equity_curve.iloc[0] == pytest.approx(1.0)

    def test_raises_on_empty_df(self) -> None:
        from engine.backtest.runner import run_backtest

        df = _make_ohlcv(45)
        with pytest.raises(ValueError, match="Empty OHLCV data"):
            run_backtest("300308", "ma_cross", df.iloc[0:0])

    def test_raises_on_missing_close_column(self) -> None:
        from engine.backtest.runner import run_backtest

        df = _make_ohlcv(45)
        with pytest.raises(KeyError, match="close column required"):
            run_backtest("300308", "ma_cross", df.drop(columns=["close"]))

    def test_raises_on_nan_in_close(self) -> None:
        from engine.backtest.runner import run_backtest

        df = _make_ohlcv(45)
        dirty = df.copy()
        dirty.iloc[0, dirty.columns.get_loc("close")] = float("nan")
        with pytest.raises(ValueError, match="NaN values in close column"):
            run_backtest("300308", "ma_cross", dirty)

    def test_raises_on_insufficient_data(self) -> None:
        from engine.backtest.runner import run_backtest

        df = _make_ohlcv(45)
        with pytest.raises(ValueError, match="Insufficient data"):
            run_backtest("300308", "ma_cross", df.iloc[:25])

    def test_raises_on_unknown_strategy(self) -> None:
        from engine.backtest.runner import run_backtest

        df = _make_ohlcv(45)
        with pytest.raises(ValueError, match="Unknown strategy"):
            run_backtest("300308", "bad_strategy", df)

    def test_no_trade_fallback(self) -> None:
        from engine.backtest.runner import run_backtest

        df = _make_ohlcv(45)
        flat = df.assign(close=100.0, open=99.5, high=101.0, low=99.0)
        result = run_backtest("300308", "ma_cross", flat)

        assert result.total_return == pytest.approx(0.0)
        assert result.max_drawdown == pytest.approx(0.0)
        assert result.win_rate == pytest.approx(0.0)
        assert result.num_trades == 0
        assert np.allclose(result.equity_curve.to_numpy(), 1.0)


# ---------------------------------------------------------------------------
# TC-035-02: run_backtest(macd_cross) 返回 BacktestResult 并给出交易统计
# ---------------------------------------------------------------------------


class TestRunBacktestMacdCross:
    def test_returns_backtest_result_structure(self) -> None:
        from engine.backtest.runner import BacktestResult, run_backtest

        df = _make_ohlcv(70, "wave")
        result = run_backtest(code="300308", strategy="macd_cross", df=df)

        assert isinstance(result, BacktestResult)
        assert result.code == "300308"
        assert result.strategy == "macd_cross"
        assert isinstance(result.total_return, float)
        assert isinstance(result.benchmark_return, float)
        assert isinstance(result.max_drawdown, float)
        assert isinstance(result.win_rate, float)
        assert isinstance(result.num_trades, int)
        assert isinstance(result.equity_curve, pd.Series)

    def test_trade_stats_in_valid_range(self) -> None:
        from engine.backtest.runner import run_backtest

        df = _make_ohlcv(70, "wave")
        result = run_backtest(code="300308", strategy="macd_cross", df=df)

        assert result.num_trades >= 0
        assert 0.0 <= result.win_rate <= 1.0
        assert len(result.equity_curve) == len(df)
        assert result.equity_curve.index.equals(df.index)

    def test_macd_signal_series_shape(self) -> None:
        from engine.backtest.strategies import macd_cross_signals

        df = _make_ohlcv(70, "wave")
        signals = macd_cross_signals(df)

        assert isinstance(signals, pd.Series)
        assert len(signals) == len(df)
        assert set(signals.dropna().unique()).issubset({0, 1})


# ---------------------------------------------------------------------------
# TC-035-03: format_backtest_result() 返回单行指标 DataFrame
# ---------------------------------------------------------------------------


class TestFormatBacktestResult:
    @pytest.fixture()
    def sample_result(self):
        from engine.backtest.runner import BacktestResult

        return BacktestResult(
            code="300308",
            strategy="ma_cross",
            total_return=0.1234,
            benchmark_return=0.2345,
            max_drawdown=-0.0567,
            win_rate=0.5,
            num_trades=4,
            equity_curve=pd.Series(
                [1.0, 1.05, 1.12],
                index=pd.date_range("2024-01-01", periods=3),
            ),
        )

    def test_returns_single_row_dataframe(self, sample_result) -> None:
        from app.pages.backtest import format_backtest_result

        df = format_backtest_result(sample_result)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_contains_required_columns(self, sample_result) -> None:
        from app.pages.backtest import format_backtest_result

        df = format_backtest_result(sample_result)

        for col in ["total_return", "benchmark_return", "max_drawdown", "win_rate"]:
            assert col in df.columns
            assert isinstance(df.loc[0, col], float)

    def test_is_pure_function(self, sample_result) -> None:
        from app.pages.backtest import format_backtest_result

        format_backtest_result(sample_result)

        assert sample_result.total_return == pytest.approx(0.1234)
        assert sample_result.equity_curve.iloc[0] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# TC-035-04: run_backtest.py CLI 使用 mock OHLCV 跑通两种策略
# ---------------------------------------------------------------------------


class TestRunBacktestCLI:
    @pytest.mark.parametrize("strategy", ["ma_cross", "macd_cross"])
    def test_cli_exits_cleanly_with_mock(self, strategy: str) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.run_backtest",
                "--code",
                "300308",
                "--strategy",
                strategy,
                "--start",
                "2024-01-01",
                "--mock",
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(Path(__file__).resolve().parents[1]),
        )
        assert proc.returncode == 0, f"CLI failed:\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
        assert "total_return" in proc.stdout
        assert "max_drawdown" in proc.stdout
        assert "Traceback" not in proc.stderr
