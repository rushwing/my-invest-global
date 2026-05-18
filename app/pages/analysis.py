from __future__ import annotations

from typing import Any

import pandas as pd

from engine.schemas import StockSignal

_ACTION_LABELS: dict[str, str] = {
    "strong_add": "强烈加仓",
    "hold_add": "持有加仓",
    "hold": "持有",
    "reduce": "减仓",
    "stop_loss": "止损",
    "take_profit_alert": "注意止盈",
}

_ACTION_COLORS: dict[str, str] = {
    "strong_add": "🟢",
    "hold_add": "🟢",
    "hold": "🟡",
    "reduce": "🔴",
    "stop_loss": "🔴",
    "take_profit_alert": "🟠",
}


def action_code_label(action_code: str) -> str:
    return _ACTION_LABELS.get(action_code, action_code)


def action_code_color(action_code: str) -> str:
    return _ACTION_COLORS.get(action_code, "⚪")


def format_signals_df(
    signals: list[StockSignal],
    change_pct_snapshot: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Convert signals to display DataFrame. Pure function, no Streamlit calls."""
    rows = []
    for s in signals:
        pct = (change_pct_snapshot or {}).get(s.code, 0.0)
        rows.append(
            {
                "code": s.code,
                "name": s.name,
                "composite_score": round(s.composite_score, 1),
                "action_code": (
                    f"{action_code_color(s.action_code)} {action_code_label(s.action_code)}"
                ),
                "change_pct": f"{pct:+.2f}%",
            }
        )
    return pd.DataFrame(rows)


def load_latest_for_ui(db_path: str) -> dict[str, Any] | None:
    """Load latest session for UI rendering. Returns None if no sessions exist."""
    from engine.agent.session_store import load_latest_session

    state = load_latest_session(db_path)
    if state is None:
        return None
    return {
        "session_id": state["session_id"],
        "captured_at": state["snapshot"].captured_at,
        "signals": state["signals"],
        "reasoning": state["reasoning"],
        "kg_subgraph": state["kg_subgraph"],
        "rag_chunks": state["rag_chunks"],
        "errors": state["errors"],
        "change_pct_snapshot": state["snapshot"].change_pct_snapshot,
    }
