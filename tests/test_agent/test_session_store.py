"""TC-030-01..04 — session_store save/load/list roundtrip (DuckDB tmp_path)."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import pytest

_store_mod = pytest.importorskip(
    "engine.agent.session_store",
    reason="engine.agent.session_store not yet implemented (pending req_impl)",
)
_state_mod = pytest.importorskip("engine.agent.state")
_schemas_mod = pytest.importorskip("engine.schemas")

save_session = _store_mod.save_session
load_latest_session = _store_mod.load_latest_session
list_sessions = _store_mod.list_sessions
FrozenMarketSnapshot = _state_mod.FrozenMarketSnapshot
AnalysisState = _state_mod.AnalysisState
HoldingRow = _schemas_mod.HoldingRow
HoldingCategory = _schemas_mod.HoldingCategory
PortfolioSummary = _schemas_mod.PortfolioSummary
StockSignal = _schemas_mod.StockSignal


def _snapshot(session_id: str = "test-session-1") -> FrozenMarketSnapshot:
    return FrozenMarketSnapshot(
        session_id=session_id,
        captured_at=datetime(2026, 5, 18, 8, 0, 0),
        holdings=(),
        macro_state="green",
        portfolio_summary=PortfolioSummary(
            total_market_value=10000.0,
            white_horse_ratio=0.5,
            elastic_ratio=0.5,
            target_white_horse=0.67,
            target_elastic=0.33,
            rebalance_needed=False,
        ),
        price_snapshot={"300308": 55.0},
        change_pct_snapshot={"300308": 2.3},
    )


def _signal() -> StockSignal:
    return StockSignal(
        code="300308",
        name="中际旭创",
        category=HoldingCategory.ELASTIC,
        technical_score=70.0,
        fundamental_score=75.0,
        sentiment_score=65.0,
        composite_score=70.0,
        action="持有加仓",
        action_code="hold_add",
        signals={},
    )


def _make_state(session_id: str = "test-session-1") -> dict:
    snap = _snapshot(session_id)
    return {
        "snapshot": snap,
        "kg_subgraph": {"300308": ["光通信板块"]},
        "rag_chunks": {"300308": ["年报摘要：光模块收入同比+45%"]},
        "signals": [_signal()],
        "reasoning": {"300308": "光通信板块受益AI数据中心建设"},
        "errors": [],
        "session_id": session_id,
    }


# ── TC-030-01 ──────────────────────────────────────────────────────────────────


class TestSaveLoadRoundtrip:
    """TC-030-01: save_session + load_latest_session roundtrip."""

    def test_session_id_matches(self, tmp_path):
        db_path = str(tmp_path / "test.duckdb")
        state = _make_state("abc-123")
        with patch("engine.agent.prompt_contracts.PROMPT_CONTRACT_HASH", "testhash123456"):
            save_session(db_path, state)
            loaded = load_latest_session(db_path)
        assert loaded is not None
        assert loaded["session_id"] == "abc-123"

    def test_signals_length_matches(self, tmp_path):
        db_path = str(tmp_path / "test.duckdb")
        state = _make_state("abc-456")
        with patch("engine.agent.prompt_contracts.PROMPT_CONTRACT_HASH", "testhash123456"):
            save_session(db_path, state)
            loaded = load_latest_session(db_path)
        assert loaded is not None
        assert len(loaded["signals"]) == len(state["signals"])

    def test_signal_code_matches(self, tmp_path):
        db_path = str(tmp_path / "test.duckdb")
        state = _make_state("abc-789")
        with patch("engine.agent.prompt_contracts.PROMPT_CONTRACT_HASH", "testhash123456"):
            save_session(db_path, state)
            loaded = load_latest_session(db_path)
        assert loaded is not None
        assert loaded["signals"][0].code == "300308"


# ── TC-030-02 ──────────────────────────────────────────────────────────────────


class TestListSessions:
    """TC-030-02: list_sessions returns results ordered by captured_at DESC."""

    def test_returns_most_recent_first(self, tmp_path):
        db_path = str(tmp_path / "test.duckdb")
        snap_old = _snapshot("session-old")
        object.__setattr__(snap_old, "captured_at", datetime(2026, 5, 17, 8, 0, 0))
        snap_new = _snapshot("session-new")
        object.__setattr__(snap_new, "captured_at", datetime(2026, 5, 18, 8, 0, 0))

        for sid, snap in [("session-old", snap_old), ("session-new", snap_new)]:
            state = _make_state(sid)
            state["snapshot"] = snap
            with patch("engine.agent.prompt_contracts.PROMPT_CONTRACT_HASH", "testhash"):
                save_session(db_path, state)

        rows = list_sessions(db_path, limit=10)
        assert len(rows) >= 2
        assert rows[0]["session_id"] == "session-new"

    def test_limit_respected(self, tmp_path):
        db_path = str(tmp_path / "test.duckdb")
        for i in range(5):
            state = _make_state(f"session-{i}")
            with patch("engine.agent.prompt_contracts.PROMPT_CONTRACT_HASH", "testhash"):
                save_session(db_path, state)
        rows = list_sessions(db_path, limit=2)
        assert len(rows) == 2


# ── TC-030-03 ──────────────────────────────────────────────────────────────────


class TestLoadLatestEmpty:
    """TC-030-03: load_latest_session returns None on empty table."""

    def test_returns_none_on_empty(self, tmp_path):
        db_path = str(tmp_path / "test.duckdb")
        result = load_latest_session(db_path)
        assert result is None


# ── TC-030-04 ──────────────────────────────────────────────────────────────────


class TestListSessionsEmpty:
    """TC-030-04: list_sessions returns empty list on empty table."""

    def test_returns_empty_list(self, tmp_path):
        db_path = str(tmp_path / "test.duckdb")
        result = list_sessions(db_path, limit=30)
        assert result == []
