from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, TypedDict

from pydantic import BaseModel, Field

from engine.macro_gate import get_macro_state
from engine.schemas import HoldingRow, PortfolioSummary, StockSignal


class FrozenMarketSnapshot(BaseModel, frozen=True):
    """Immutable market snapshot captured once per analysis session."""

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    captured_at: datetime = Field(default_factory=datetime.utcnow)
    holdings: tuple[HoldingRow, ...]
    macro_state: Literal["green", "yellow", "red"]
    portfolio_summary: PortfolioSummary
    price_snapshot: dict[str, float]
    change_pct_snapshot: dict[str, float]


class AnalysisState(TypedDict):
    snapshot: FrozenMarketSnapshot
    kg_subgraph: dict[str, list[str]]
    rag_chunks: dict[str, list[str]]
    signals: list[StockSignal]
    reasoning: dict[str, str]
    errors: list[str]
    session_id: str


def build_snapshot(db_path: str = "") -> FrozenMarketSnapshot:
    """Read holdings and macro state, return immutable snapshot.

    Holdings are loaded from data/agent_input/cn/holdings.yaml via
    engine.portfolio.load_holdings(). price_snapshot and change_pct_snapshot
    are populated from HoldingRow.current_price and pnl_pct (no intraday fetch).
    """
    from engine.portfolio import compute_portfolio_summary, load_holdings

    holdings = load_holdings(db_path)
    macro = get_macro_state()
    summary = compute_portfolio_summary(holdings)

    price_snap = {h.code: h.current_price for h in holdings}
    change_snap: dict[str, float] = {}
    for h in holdings:
        try:
            change_snap[h.code] = float(h.pnl_pct.rstrip("%").lstrip("+"))
        except (ValueError, AttributeError):
            change_snap[h.code] = 0.0

    return FrozenMarketSnapshot(
        holdings=tuple(holdings),
        macro_state=macro.value,
        portfolio_summary=summary,
        price_snapshot=price_snap,
        change_pct_snapshot=change_snap,
    )
