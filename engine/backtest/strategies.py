"""MA 金叉 / MACD 金叉策略信号函数。"""
from __future__ import annotations

import pandas as pd


def ma_cross_signals(df: pd.DataFrame) -> pd.Series:
    """MA5/MA20 金叉死叉信号。

    Returns signal Series (1=持有, 0=空仓)，shift(1) 避免 lookahead bias。
    """
    close = df["close"]
    ma5 = close.rolling(5).mean()
    ma20 = close.rolling(20).mean()
    raw = (ma5 > ma20).astype(int)
    return raw.shift(1).fillna(0).astype(int).rename("signal")


def macd_cross_signals(df: pd.DataFrame) -> pd.Series:
    """DIF/DEA 金叉死叉信号（EMA12−EMA26 vs EMA9 of DIF）。

    Returns signal Series (1=持有, 0=空仓)，shift(1) 避免 lookahead bias。
    """
    close = df["close"]
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    raw = (dif > dea).astype(int)
    return raw.shift(1).fillna(0).astype(int).rename("signal")
