"""回测执行器：策略信号 → BacktestResult。"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class BacktestResult:
    code: str
    strategy: str
    total_return: float
    benchmark_return: float
    max_drawdown: float      # 负数，如 -0.15
    win_rate: float
    num_trades: int
    equity_curve: pd.Series  # index=DatetimeIndex, 起始净值=1.0


def run_backtest(
    code: str,
    strategy: str,
    df: pd.DataFrame,
) -> BacktestResult:
    """运行回测。

    Args:
        code: 股票代码（仅写入结果，不用于 fetch）
        strategy: "ma_cross" | "macd_cross"
        df: 含 close 列（小写）的 OHLCV DataFrame，index 为 DatetimeIndex

    Raises:
        ValueError: 空 df / close 含 NaN / 数据不足 / 未知策略
        KeyError: 缺少 close 列
    """
    if len(df) == 0:
        raise ValueError("Empty OHLCV data")
    if "close" not in df.columns:
        raise KeyError("close column required")
    if df["close"].isna().any():
        raise ValueError("NaN values in close column")
    if len(df) < 26:
        raise ValueError("Insufficient data: need ≥ 26 rows")

    df = df.sort_index()

    if strategy == "ma_cross":
        from engine.backtest.strategies import ma_cross_signals
        position = ma_cross_signals(df)
    elif strategy == "macd_cross":
        from engine.backtest.strategies import macd_cross_signals
        position = macd_cross_signals(df)
    else:
        raise ValueError(f"Unknown strategy: {strategy!r}")

    close = df["close"]
    daily_ret = close.pct_change().fillna(0.0)
    strategy_ret = position * daily_ret
    equity_curve = (1.0 + strategy_ret).cumprod()

    total_return = float(equity_curve.iloc[-1] - 1.0)
    benchmark_return = float(close.iloc[-1] / close.iloc[0] - 1.0)

    # 逐笔交易统计
    pos_arr = position.to_numpy()
    close_arr = close.to_numpy()
    trades_pnl: list[bool] = []
    i = 0
    n = len(pos_arr)
    while i < n:
        if pos_arr[i] == 1:
            entry_price = close_arr[i - 1] if i > 0 else close_arr[0]
            j = i + 1
            while j < n and pos_arr[j] == 1:
                j += 1
            exit_price = close_arr[j - 1]
            trades_pnl.append(bool(exit_price > entry_price))
            i = j
        else:
            i += 1

    num_trades = len(trades_pnl)
    win_rate = sum(trades_pnl) / num_trades if num_trades > 0 else 0.0

    if num_trades == 0:
        max_drawdown = 0.0
    else:
        max_drawdown = float((equity_curve / equity_curve.cummax() - 1.0).min())

    # 无交易时 equity 全 1.0，确保数值精确
    if num_trades == 0:
        equity_curve = pd.Series(
            np.ones(len(df)), index=df.index, dtype=float, name="equity"
        )

    return BacktestResult(
        code=code,
        strategy=strategy,
        total_return=total_return,
        benchmark_return=benchmark_return,
        max_drawdown=max_drawdown,
        win_rate=win_rate,
        num_trades=num_trades,
        equity_curve=equity_curve,
    )
