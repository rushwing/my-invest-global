from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import duckdb

from engine.agent.state import AnalysisState, FrozenMarketSnapshot
from engine.schemas import PortfolioSummary, StockSignal

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS analysis_sessions (
    session_id   VARCHAR PRIMARY KEY,
    captured_at  TIMESTAMP,
    state_json   JSON,
    signal_json  JSON,
    prompt_hash  VARCHAR,
    errors_json  JSON
)
"""


def _open(db_path: str) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(db_path)


def save_session(db_path: str, state: AnalysisState) -> None:
    """Upsert analysis session into DuckDB."""
    from engine.agent.prompt_contracts import PROMPT_CONTRACT_HASH

    snap = state["snapshot"]
    signal_json = json.dumps(
        [s.model_dump() for s in state["signals"]], ensure_ascii=False
    )
    state_json = json.dumps(
        {
            "kg_subgraph": state["kg_subgraph"],
            "rag_chunks": state["rag_chunks"],
            "reasoning": state["reasoning"],
        },
        ensure_ascii=False,
    )
    errors_json = json.dumps(state["errors"], ensure_ascii=False)

    con = _open(db_path)
    try:
        con.execute(_CREATE_TABLE)
        con.execute(
            """
            INSERT OR REPLACE INTO analysis_sessions
            (session_id, captured_at, state_json, signal_json, prompt_hash, errors_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                state["session_id"],
                snap.captured_at,
                state_json,
                signal_json,
                PROMPT_CONTRACT_HASH,
                errors_json,
            ],
        )
    finally:
        con.close()


def load_latest_session(db_path: str) -> AnalysisState | None:
    """Return the most recent AnalysisState or None if table is empty."""
    con = _open(db_path)
    try:
        con.execute(_CREATE_TABLE)
        row = con.execute(
            "SELECT session_id, state_json, signal_json, errors_json, captured_at "
            "FROM analysis_sessions ORDER BY captured_at DESC LIMIT 1"
        ).fetchone()
    finally:
        con.close()

    if row is None:
        return None

    session_id, state_json_str, signal_json_str, errors_json_str, captured_at = row
    state_data: dict[str, Any] = json.loads(state_json_str)
    signals = [StockSignal(**s) for s in json.loads(signal_json_str)]
    errors: list[str] = json.loads(errors_json_str)

    placeholder_snap = FrozenMarketSnapshot(
        session_id=session_id,
        captured_at=(
            captured_at if isinstance(captured_at, datetime)
            else datetime.fromisoformat(str(captured_at))
        ),
        holdings=(),
        macro_state="yellow",
        portfolio_summary=PortfolioSummary(
            total_market_value=0,
            white_horse_ratio=0,
            elastic_ratio=0,
            target_white_horse=0,
            target_elastic=0,
            rebalance_needed=False,
        ),
        price_snapshot={},
        change_pct_snapshot={},
    )
    return AnalysisState(
        snapshot=placeholder_snap,
        kg_subgraph=state_data.get("kg_subgraph", {}),
        rag_chunks=state_data.get("rag_chunks", {}),
        signals=signals,
        reasoning=state_data.get("reasoning", {}),
        errors=errors,
        session_id=session_id,
    )


def list_sessions(db_path: str, limit: int = 30) -> list[dict[str, Any]]:
    """Return metadata rows ordered by captured_at DESC."""
    con = _open(db_path)
    try:
        con.execute(_CREATE_TABLE)
        rows = con.execute(
            "SELECT session_id, captured_at, prompt_hash "
            "FROM analysis_sessions ORDER BY captured_at DESC LIMIT ?",
            [limit],
        ).fetchall()
    finally:
        con.close()
    return [
        {"session_id": r[0], "captured_at": r[1], "prompt_hash": r[2]}
        for r in rows
    ]
