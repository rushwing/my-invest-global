"""Portfolio allocation checks for the 2/3 white-horse + 1/3 elastic framework."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import pandas as pd

MacroState = Literal["green", "yellow", "red"]

TARGET_ELASTIC_BY_MACRO_STATE: dict[MacroState, float] = {
    "green": 0.38,
    "yellow": 0.33,
    "red": 0.20,
}


def check_portfolio_balance(
    holdings_df: pd.DataFrame,
    macro_state: MacroState = "yellow",
    tolerance: float = 0.10,
) -> dict[str, Any]:
    """Check whether elastic/white-horse allocation has drifted beyond tolerance.

    The tolerance is an absolute percentage-point band around the dynamic target:
    green=38%, yellow=33%, red=20% elastic allocation.
    """

    if macro_state not in TARGET_ELASTIC_BY_MACRO_STATE:
        valid = ", ".join(TARGET_ELASTIC_BY_MACRO_STATE)
        msg = f"macro_state must be one of: {valid}"
        raise ValueError(msg)
    if tolerance < 0:
        raise ValueError("tolerance must be non-negative")

    required_columns = {"category", "market_value"}
    missing_columns = required_columns - set(holdings_df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"holdings_df missing required columns: {missing}")

    total_market_value = float(holdings_df["market_value"].sum())
    target_elastic = TARGET_ELASTIC_BY_MACRO_STATE[macro_state]
    target_white_horse = 1 - target_elastic

    if total_market_value <= 0:
        return {
            "rebalance_needed": False,
            "direction": "none",
            "macro_state": macro_state,
            "total_market_value": total_market_value,
            "elastic_market_value": 0.0,
            "white_horse_market_value": 0.0,
            "elastic_ratio": 0.0,
            "white_horse_ratio": 0.0,
            "target_elastic": target_elastic,
            "target_white_horse": target_white_horse,
            "deviation": -target_elastic,
            "tolerance": tolerance,
        }

    elastic_market_value = float(
        holdings_df.loc[holdings_df["category"] == "弹性股", "market_value"].sum()
    )
    white_horse_market_value = float(
        holdings_df.loc[holdings_df["category"] == "白马股", "market_value"].sum()
    )
    elastic_ratio = elastic_market_value / total_market_value
    white_horse_ratio = white_horse_market_value / total_market_value
    deviation = elastic_ratio - target_elastic
    rebalance_needed = abs(deviation) > tolerance

    direction = "none"
    if rebalance_needed:
        direction = "reduce_elastic" if deviation > 0 else "add_elastic"

    return {
        "rebalance_needed": rebalance_needed,
        "direction": direction,
        "macro_state": macro_state,
        "total_market_value": total_market_value,
        "elastic_market_value": elastic_market_value,
        "white_horse_market_value": white_horse_market_value,
        "elastic_ratio": elastic_ratio,
        "white_horse_ratio": white_horse_ratio,
        "target_elastic": target_elastic,
        "target_white_horse": target_white_horse,
        "deviation": deviation,
        "tolerance": tolerance,
    }


_HOLDINGS_YAML = Path("data/agent_input/cn/holdings.yaml")


def load_holdings(db_path: str = "") -> list:
    """Load current holdings from data/agent_input/cn/holdings.yaml.

    Returns list[HoldingRow]. Returns [] if the file doesn't exist yet.
    The db_path parameter is accepted for interface compatibility but unused;
    holdings are maintained as a YAML file, not in DuckDB.
    """
    import yaml

    from engine.schemas import HoldingRow

    if not _HOLDINGS_YAML.exists():
        return []
    data = yaml.safe_load(_HOLDINGS_YAML.read_text())
    return [HoldingRow(**row) for row in (data.get("holdings") or [])]


def compute_portfolio_summary(holdings: list) -> Any:
    """Compute PortfolioSummary from a list of HoldingRow objects."""
    from engine.macro_gate import get_macro_state
    from engine.schemas import HoldingCategory, PortfolioSummary

    macro = get_macro_state()
    target_elastic = TARGET_ELASTIC_BY_MACRO_STATE.get(macro.value, 0.33)
    target_white_horse = 1.0 - target_elastic

    total = sum(h.market_value for h in holdings)
    if total <= 0:
        return PortfolioSummary(
            total_market_value=0.0,
            white_horse_ratio=0.0,
            elastic_ratio=0.0,
            target_white_horse=target_white_horse,
            target_elastic=target_elastic,
            rebalance_needed=False,
        )

    elastic_mv = sum(
        h.market_value for h in holdings if h.category == HoldingCategory.ELASTIC
    )
    white_horse_mv = sum(
        h.market_value for h in holdings if h.category == HoldingCategory.WHITE_HORSE
    )
    elastic_ratio = elastic_mv / total
    white_horse_ratio = white_horse_mv / total
    rebalance_needed = abs(elastic_ratio - target_elastic) > 0.10

    return PortfolioSummary(
        total_market_value=total,
        white_horse_ratio=white_horse_ratio,
        elastic_ratio=elastic_ratio,
        target_white_horse=target_white_horse,
        target_elastic=target_elastic,
        rebalance_needed=rebalance_needed,
    )

