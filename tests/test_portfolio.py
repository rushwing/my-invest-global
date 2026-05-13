import pandas as pd

from engine.portfolio import check_portfolio_balance


def test_check_portfolio_balance_uses_dynamic_macro_target() -> None:
    holdings = pd.DataFrame(
        [
            {"category": "白马股", "market_value": 70_000},
            {"category": "弹性股", "market_value": 30_000},
        ]
    )

    result = check_portfolio_balance(holdings, macro_state="green")

    assert result["target_elastic"] == 0.38
    assert result["rebalance_needed"] is False
    assert round(result["deviation"], 2) == -0.08


def test_check_portfolio_balance_flags_large_elastic_drift() -> None:
    holdings = pd.DataFrame(
        [
            {"category": "白马股", "market_value": 40_000},
            {"category": "弹性股", "market_value": 60_000},
        ]
    )

    result = check_portfolio_balance(holdings, macro_state="yellow")

    assert result["rebalance_needed"] is True
    assert result["direction"] == "reduce_elastic"

