"""Phase 11 — 筹码分布数据采集层 (REQ-036).

Primary data source: akshare stock_cyq_em.
Storage: DuckDB chip_summary + chip_distribution tables.
"""

from __future__ import annotations

from datetime import date as _date
from typing import Any

from pydantic import BaseModel


class ChipDataUnavailable(Exception):
    pass


class ChipBar(BaseModel):
    price_lower: float
    price_upper: float
    chip_ratio: float


class ChipSummary(BaseModel):
    code: str
    date: str
    avg_cost: float
    profitable_pct: float
    concentration: float
    range_70_lower: float
    range_70_upper: float
    range_90_lower: float
    range_90_upper: float
    bars: list[ChipBar]


# ── Column map ────────────────────────────────────────────────────────────────

_COL_PRICE = "价格"
_COL_RATIO = "筹码占比"
_COL_PROFITABLE = "获利比例"
_COL_AVG_COST = "平均成本"
_COL_R90_LO = "90成本-低"
_COL_R90_HI = "90成本-高"
_COL_R70_LO = "70成本-低"
_COL_R70_HI = "70成本-高"
_COL_CONCENTRATION = "集中度"

_REQUIRED_COLS = {_COL_PRICE, _COL_RATIO, _COL_PROFITABLE, _COL_AVG_COST, _COL_R90_LO, _COL_R90_HI}


def fetch_chip_summary(code: str, date: str | None = None) -> ChipSummary:
    """Fetch chip distribution from akshare and return ChipSummary.

    Raises ChipDataUnavailable if akshare returns empty data.
    """
    import akshare as ak

    df = ak.stock_cyq_em(symbol=code, adjust="")

    if df is None or df.empty:
        raise ChipDataUnavailable(f"No chip data for {code}")

    missing = _REQUIRED_COLS - set(df.columns)
    if missing:
        raise ChipDataUnavailable(f"Missing required columns for {code}: {missing}")

    # Summary fields are identical across all rows; use first row.
    # Price-sort only applies to bars (histogram ordering).
    row0 = df.iloc[0]
    avg_cost = float(row0[_COL_AVG_COST])
    profitable_pct = float(row0[_COL_PROFITABLE]) / 100.0
    range_90_lower = float(row0[_COL_R90_LO])
    range_90_upper = float(row0[_COL_R90_HI])

    if _COL_R70_LO in df.columns and _COL_R70_HI in df.columns:
        range_70_lower = float(row0[_COL_R70_LO])
        range_70_upper = float(row0[_COL_R70_HI])
    else:
        range_70_lower = range_90_lower
        range_70_upper = range_90_upper

    if _COL_CONCENTRATION in df.columns:
        concentration = float(row0[_COL_CONCENTRATION])
    else:
        concentration = min(
            100.0, max(0.0, (range_90_upper - range_90_lower) / avg_cost * 100)
        )

    df_sorted = df.sort_values(_COL_PRICE).reset_index(drop=True)
    prices = df_sorted[_COL_PRICE].tolist()
    ratios = df_sorted[_COL_RATIO].tolist()

    bars: list[ChipBar] = []
    for i, (price, ratio) in enumerate(zip(prices, ratios)):
        if i < len(prices) - 1:
            upper = prices[i + 1]
        else:
            step = (prices[-1] - prices[-2]) if len(prices) >= 2 else price
            upper = price + step
        bars.append(ChipBar(
            price_lower=float(price), price_upper=float(upper), chip_ratio=float(ratio),
        ))

    result_date = date if date is not None else _date.today().isoformat()

    return ChipSummary(
        code=code,
        date=result_date,
        avg_cost=avg_cost,
        profitable_pct=profitable_pct,
        concentration=concentration,
        range_70_lower=range_70_lower,
        range_70_upper=range_70_upper,
        range_90_lower=range_90_lower,
        range_90_upper=range_90_upper,
        bars=bars,
    )


def store_chip_data(conn: Any, summary: ChipSummary) -> None:
    """UPSERT chip_summary and chip_distribution rows into DuckDB."""
    conn.execute(
        """
        INSERT INTO chip_summary
            (code, date, avg_cost, profitable_pct, concentration,
             range_70_lower, range_70_upper, range_90_lower, range_90_upper)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (code, date) DO UPDATE SET
            avg_cost       = excluded.avg_cost,
            profitable_pct = excluded.profitable_pct,
            concentration  = excluded.concentration,
            range_70_lower = excluded.range_70_lower,
            range_70_upper = excluded.range_70_upper,
            range_90_lower = excluded.range_90_lower,
            range_90_upper = excluded.range_90_upper
        """,
        (
            summary.code, summary.date, summary.avg_cost, summary.profitable_pct,
            summary.concentration, summary.range_70_lower, summary.range_70_upper,
            summary.range_90_lower, summary.range_90_upper,
        ),
    )

    for bar in summary.bars:
        conn.execute(
            """
            INSERT INTO chip_distribution (code, date, price_lower, price_upper, chip_ratio)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (code, date, price_lower) DO UPDATE SET
                price_upper = excluded.price_upper,
                chip_ratio  = excluded.chip_ratio
            """,
            (summary.code, summary.date, bar.price_lower, bar.price_upper, bar.chip_ratio),
        )
