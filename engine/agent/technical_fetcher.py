"""Fetch A-share OHLCV from akshare and compute technical indicators via pandas-ta."""
from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any

import pandas as pd


def fetch_ohlcv(code: str, start: str, end: str | None = None) -> pd.DataFrame:
    """拉取日频 OHLCV，返回小写列名 open/high/low/close/volume，index 为 DatetimeIndex。

    Args:
        code: A 股代码，如 "300308"
        start: 开始日期 "YYYY-MM-DD"
        end: 结束日期 "YYYY-MM-DD"，默认今日

    Returns:
        DataFrame，列：open/high/low/close/volume，index 升序 DatetimeIndex
    """
    import akshare as ak

    start_fmt = start.replace("-", "")
    end_fmt = end.replace("-", "") if end else date.today().strftime("%Y%m%d")
    df = ak.stock_zh_a_hist(
        symbol=code, period="daily", start_date=start_fmt, end_date=end_fmt, adjust="qfq"
    )
    df = df.rename(
        columns={
            "日期": "date",
            "开盘": "open",
            "最高": "high",
            "最低": "low",
            "收盘": "close",
            "成交量": "volume",
        }
    )
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    return df[["open", "high", "low", "close", "volume"]]


def fetch_technicals(
    codes: list[str],
    lookback_days: int = 60,
) -> dict[str, dict[str, float]]:
    """Fetch daily OHLCV for each code and compute MA/MACD/RSI indicators.

    Returns a dict mapping code → indicator dict. On per-code failure the code
    maps to an empty dict so the pipeline continues without interruption.

    Computed keys per code:
        MA5, MA10, MA20, MA30  — simple moving averages
        MACD_DIF               — DIF line (EMA12 - EMA26); user term: MACDIF
        MACD_DEA               — DEA signal line (EMA9 of DIF); user term: MACDFS
        MACD_BAR               — histogram (DIF - DEA) × 2; user term: MACDIE
        RSI14                  — RSI with period=14
    """
    import akshare as ak
    import pandas_ta as ta  # noqa: F401 — imported for side-effects (DataFrame.ta accessor)

    start = (date.today() - timedelta(days=lookback_days + 30)).strftime("%Y%m%d")
    result: dict[str, dict[str, float]] = {}

    for code in codes:
        try:
            df = ak.stock_zh_a_hist(
                symbol=code, period="daily", start_date=start, adjust="qfq"
            )
            df = df.rename(columns={
                "收盘": "Close",
                "开盘": "Open",
                "最高": "High",
                "最低": "Low",
                "成交量": "Volume",
            })
            df.ta.sma(length=5, append=True)
            df.ta.sma(length=10, append=True)
            df.ta.sma(length=20, append=True)
            df.ta.sma(length=30, append=True)
            df.ta.macd(fast=12, slow=26, signal=9, append=True)
            df.ta.rsi(length=14, append=True)
            last: Any = df.iloc[-1]

            def _v(key: str) -> float:
                val = last.get(key, float("nan"))
                f = float(val)
                return float("nan") if math.isnan(f) else round(f, 3)

            result[code] = {
                "MA5": _v("SMA_5"),
                "MA10": _v("SMA_10"),
                "MA20": _v("SMA_20"),
                "MA30": _v("SMA_30"),
                "MACD_DIF": _v("MACD_12_26_9"),
                "MACD_DEA": _v("MACDs_12_26_9"),
                "MACD_BAR": _v("MACDh_12_26_9"),
                "RSI14": _v("RSI_14"),
            }
        except Exception:
            result[code] = {}

    return result
