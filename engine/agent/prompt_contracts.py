from __future__ import annotations

from datetime import datetime
from hashlib import sha256

from engine.agent.nodes import _SIGNAL_RANKER_SYSTEM

SIGNAL_RANKER_SYSTEM_PROMPT: str = _SIGNAL_RANKER_SYSTEM
PROMPT_CONTRACT_HASH: str = sha256(SIGNAL_RANKER_SYSTEM_PROMPT.encode()).hexdigest()[:12]


def log_session_contract(session_id: str, db_path: str) -> None:
    """Append (session_id, PROMPT_CONTRACT_HASH, captured_at) to DuckDB for audit."""
    import duckdb

    con = duckdb.connect(db_path)
    try:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS prompt_audit (
                session_id   VARCHAR,
                prompt_hash  VARCHAR,
                captured_at  TIMESTAMP
            )
            """
        )
        con.execute(
            "INSERT INTO prompt_audit VALUES (?, ?, ?)",
            [session_id, PROMPT_CONTRACT_HASH, datetime.utcnow()],
        )
    finally:
        con.close()
