"""Phase 11 — 筹码分析引擎 (REQ-037).

Pure analysis layer: ChipAnalysis signal model + analyze_chip().
No I/O in analyze_chip; load_and_analyze handles DuckDB reads.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class ChipLockLevel(StrEnum):
    HIGH = "high"      # concentration >= 60
    MEDIUM = "medium"  # 40 <= concentration < 60
    LOW = "low"        # concentration < 40


class ChipAnalysis(BaseModel):
    code: str
    date: str
    current_price: float
    avg_cost: float
    profitable_pct: float
    concentration: float
    range_70_lower: float
    range_70_upper: float
    range_90_lower: float
    range_90_upper: float
    above_90_band: bool
    below_90_band: bool
    cost_deviation_pct: float
    chip_spread_90: float
    chip_lock_level: ChipLockLevel
    signal_summary: str


def _chip_lock_level(concentration: float) -> ChipLockLevel:
    if concentration >= 60:
        return ChipLockLevel.HIGH
    if concentration >= 40:
        return ChipLockLevel.MEDIUM
    return ChipLockLevel.LOW


def analyze_chip(code: str, current_price: float, summary: Any) -> ChipAnalysis:
    """Derive ChipAnalysis from current_price + ChipSummary. Pure function.

    Raises ValueError if avg_cost <= 0 (division by zero guard).
    """
    if summary.avg_cost <= 0:
        raise ValueError(f"Invalid avg_cost={summary.avg_cost!r} for {code}")

    above_90_band = current_price > summary.range_90_upper
    below_90_band = current_price < summary.range_90_lower
    cost_deviation_pct = round(
        (current_price - summary.avg_cost) / summary.avg_cost * 100, 1
    )
    chip_spread_90 = summary.range_90_upper - summary.range_90_lower

    if above_90_band and summary.profitable_pct >= 0.95:
        signal = f"价格突破90%筹码上界，{summary.profitable_pct:.0%}筹码浮盈，获利兑现压力大"
    elif above_90_band:
        signal = "价格突破90%筹码上界，部分筹码仍在成本附近"
    elif below_90_band:
        signal = "价格低于90%筹码下界，处于历史套牢密集区"
    elif cost_deviation_pct > 10:
        signal = f"价格高于均成本{cost_deviation_pct:.1f}%，筹码整体盈利"
    elif cost_deviation_pct <= 0:
        signal = "价格低于均成本，整体套牢状态"
    else:
        signal = f"价格在90%筹码区间内，均成本偏离{cost_deviation_pct:.1f}%"

    return ChipAnalysis(
        code=code,
        date=summary.date,
        current_price=current_price,
        avg_cost=summary.avg_cost,
        profitable_pct=summary.profitable_pct,
        concentration=summary.concentration,
        range_70_lower=summary.range_70_lower,
        range_70_upper=summary.range_70_upper,
        range_90_lower=summary.range_90_lower,
        range_90_upper=summary.range_90_upper,
        above_90_band=above_90_band,
        below_90_band=below_90_band,
        cost_deviation_pct=cost_deviation_pct,
        chip_spread_90=chip_spread_90,
        chip_lock_level=_chip_lock_level(summary.concentration),
        signal_summary=signal[:80],
    )


def load_and_analyze(
    code: str,
    current_price: float,
    conn: Any,
    date: str | None = None,
) -> ChipAnalysis:
    """Load latest chip_summary from DuckDB and return ChipAnalysis.

    Raises ChipDataUnavailable if no data found for code.
    """
    from engine.agent.chip_fetcher import ChipBar, ChipDataUnavailable, ChipSummary

    if date is not None:
        row = conn.execute(
            "SELECT code, date, avg_cost, profitable_pct, concentration, "
            "range_70_lower, range_70_upper, range_90_lower, range_90_upper "
            "FROM chip_summary WHERE code=? AND date=? ORDER BY date DESC LIMIT 1",
            [code, date],
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT code, date, avg_cost, profitable_pct, concentration, "
            "range_70_lower, range_70_upper, range_90_lower, range_90_upper "
            "FROM chip_summary WHERE code=? ORDER BY date DESC LIMIT 1",
            [code],
        ).fetchone()

    if row is None:
        raise ChipDataUnavailable(f"{code} has no chip data")

    code_db, date_db, avg_cost, profitable_pct, concentration, r70lo, r70hi, r90lo, r90hi = row
    date_str = str(date_db)

    try:
        bar_rows = conn.execute(
            "SELECT price_lower, price_upper, chip_ratio "
            "FROM chip_distribution WHERE code=? AND date=?",
            [code, date_db],
        ).fetchall()
        bars = [ChipBar(price_lower=r[0], price_upper=r[1], chip_ratio=r[2]) for r in bar_rows]
    except Exception:
        bars = []

    summary = ChipSummary(
        code=str(code_db),
        date=date_str,
        avg_cost=float(avg_cost),
        profitable_pct=float(profitable_pct),
        concentration=float(concentration),
        range_70_lower=float(r70lo),
        range_70_upper=float(r70hi),
        range_90_lower=float(r90lo),
        range_90_upper=float(r90hi),
        bars=bars,
    )
    return analyze_chip(code, current_price, summary)
