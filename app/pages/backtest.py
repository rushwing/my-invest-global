"""回测结果展示层纯函数。"""
from __future__ import annotations

import pandas as pd

from engine.backtest.runner import BacktestResult


def format_backtest_result(result: BacktestResult) -> pd.DataFrame:
    """Convert BacktestResult to single-row display DataFrame. Pure function."""
    return pd.DataFrame(
        [
            {
                "total_return": float(result.total_return),
                "benchmark_return": float(result.benchmark_return),
                "max_drawdown": float(result.max_drawdown),
                "win_rate": float(result.win_rate),
            }
        ]
    )
