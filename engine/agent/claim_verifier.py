from __future__ import annotations

from dataclasses import dataclass

from engine.agent.state import FrozenMarketSnapshot
from engine.schemas import StockSignal

_PRICE_TOLERANCE = 0.20


@dataclass
class ClaimViolation:
    code: str
    field: str
    claimed_value: str
    actual_value: str


def verify_signals(
    signals: list[StockSignal],
    snapshot: FrozenMarketSnapshot,
) -> list[ClaimViolation]:
    """Cross-check signal numeric claims against snapshot values.

    Returns empty list if all signals are clean.
    Violations do NOT block output — caller writes them to state["errors"].
    """
    violations: list[ClaimViolation] = []
    for sig in signals:
        actual_price = snapshot.price_snapshot.get(sig.code)
        if actual_price is not None and actual_price > 0:
            claimed = sig.signals.get("claimed_price")
            if claimed is not None:
                deviation = abs(float(claimed) - actual_price) / actual_price
                if deviation > _PRICE_TOLERANCE:
                    violations.append(
                        ClaimViolation(
                            code=sig.code,
                            field="price",
                            claimed_value=str(claimed),
                            actual_value=str(actual_price),
                        )
                    )
    return violations
