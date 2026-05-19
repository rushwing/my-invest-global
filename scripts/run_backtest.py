"""CLI 回测入口。

使用方式：
    uv run python -m scripts.run_backtest \\
        --code 300308 --strategy ma_cross --start 2024-01-01
    uv run python -m scripts.run_backtest \\
        --code 300308 --strategy macd_cross --start 2024-01-01 --mock
"""
from __future__ import annotations

import argparse

import pandas as pd


def _mock_ohlcv(periods: int = 70) -> pd.DataFrame:
    import numpy as np
    import pandas as pd

    dates = pd.date_range("2024-01-01", periods=periods, freq="D")
    close = np.r_[
        np.linspace(120, 90, 25),
        np.linspace(91, 135, 30),
        np.linspace(134, 110, periods - 55),
    ]
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


def main() -> None:
    parser = argparse.ArgumentParser(description="运行单只股票回测")
    parser.add_argument("--code", required=True, help="A 股代码，如 300308")
    parser.add_argument(
        "--strategy",
        required=True,
        choices=["ma_cross", "macd_cross"],
        help="策略名",
    )
    parser.add_argument("--start", required=True, help="开始日期 YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="结束日期 YYYY-MM-DD（默认今日）")
    parser.add_argument(
        "--mock", action="store_true", help="使用 mock OHLCV（不访问 akshare，用于 CI）"
    )
    args = parser.parse_args()

    if args.mock:
        df = _mock_ohlcv()
    else:
        from engine.agent.technical_fetcher import fetch_ohlcv
        df = fetch_ohlcv(args.code, args.start, args.end)

    from engine.backtest.runner import run_backtest
    result = run_backtest(code=args.code, strategy=args.strategy, df=df)

    print(f"code:             {result.code}")
    print(f"strategy:         {result.strategy}")
    print(f"total_return:     {result.total_return:.2%}")
    print(f"benchmark_return: {result.benchmark_return:.2%}")
    print(f"max_drawdown:     {result.max_drawdown:.2%}")
    print(f"win_rate:         {result.win_rate:.2%}")
    print(f"num_trades:       {result.num_trades}")


if __name__ == "__main__":
    main()
