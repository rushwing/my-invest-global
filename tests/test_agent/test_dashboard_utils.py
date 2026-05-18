"""TC-031-01..03 — Dashboard pure-function utilities (no Streamlit)."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import pytest

_analysis_mod = pytest.importorskip(
    "app.pages.analysis",
    reason="app.pages.analysis not yet implemented (pending req_impl)",
)
_schemas_mod = pytest.importorskip("engine.schemas")

format_signals_df = _analysis_mod.format_signals_df
load_latest_for_ui = _analysis_mod.load_latest_for_ui
action_code_label = _analysis_mod.action_code_label

HoldingCategory = _schemas_mod.HoldingCategory
StockSignal = _schemas_mod.StockSignal


def _signal(code: str = "300308", name: str = "中际旭创", action_code: str = "hold_add"):
    return StockSignal(
        code=code,
        name=name,
        category=HoldingCategory.ELASTIC,
        technical_score=70.0,
        fundamental_score=75.0,
        sentiment_score=65.0,
        composite_score=70.0,
        action="持有加仓",
        action_code=action_code,
        signals={},
    )


# ── TC-031-01 ──────────────────────────────────────────────────────────────────


class TestFormatSignalsDf:
    """TC-031-01: format_signals_df returns DataFrame with required columns."""

    _REQUIRED = {"code", "name", "composite_score", "action_code", "change_pct"}

    def test_columns_present(self):
        sig = _signal()
        df = format_signals_df([sig], {"300308": 2.3})
        assert self._REQUIRED <= set(df.columns)

    def test_change_pct_formatted(self):
        sig = _signal()
        df = format_signals_df([sig], {"300308": 2.3})
        assert df.loc[0, "change_pct"] == "+2.30%"

    def test_negative_change_pct(self):
        sig = _signal()
        df = format_signals_df([sig], {"300308": -1.5})
        assert df.loc[0, "change_pct"] == "-1.50%"

    def test_empty_signals_empty_df(self):
        df = format_signals_df([], {})
        assert len(df) == 0

    def test_missing_code_in_snapshot_defaults_to_zero(self):
        sig = _signal(code="300308")
        df = format_signals_df([sig], {})  # no 300308 in snapshot
        assert df.loc[0, "change_pct"] == "+0.00%"


# ── TC-031-02 ──────────────────────────────────────────────────────────────────


class TestLoadLatestForUi:
    """TC-031-02: load_latest_for_ui returns correct structure from mock session."""

    def _make_mock_state(self):
        from engine.agent.state import FrozenMarketSnapshot

        from engine.schemas import PortfolioSummary

        snap = FrozenMarketSnapshot(
            session_id="ui-session-1",
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
        return {
            "snapshot": snap,
            "kg_subgraph": {"300308": ["光通信"]},
            "rag_chunks": {"300308": ["年报摘要"]},
            "signals": [_signal(), _signal(code="688561", name="奇安信")],
            "reasoning": {"300308": "AI板块受益"},
            "errors": [],
            "session_id": "ui-session-1",
        }

    def test_returns_dict_with_signals(self):
        state = self._make_mock_state()
        with patch("engine.agent.session_store.load_latest_session", return_value=state):
            result = load_latest_for_ui("fake.duckdb")
        assert result is not None
        assert len(result["signals"]) == 2

    def test_returns_reasoning(self):
        state = self._make_mock_state()
        with patch("engine.agent.session_store.load_latest_session", return_value=state):
            result = load_latest_for_ui("fake.duckdb")
        assert "reasoning" in result

    def test_returns_none_when_no_session(self):
        with patch("engine.agent.session_store.load_latest_session", return_value=None):
            result = load_latest_for_ui("fake.duckdb")
        assert result is None

    def test_captured_at_present(self):
        state = self._make_mock_state()
        with patch("engine.agent.session_store.load_latest_session", return_value=state):
            result = load_latest_for_ui("fake.duckdb")
        assert "captured_at" in result


# ── TC-031-03 ──────────────────────────────────────────────────────────────────


class TestActionCodeLabel:
    """TC-031-03: action_code_label returns correct Chinese labels."""

    def test_hold_add(self):
        assert action_code_label("hold_add") == "持有加仓"

    def test_strong_add(self):
        assert action_code_label("strong_add") == "强烈加仓"

    def test_hold(self):
        assert action_code_label("hold") == "持有"

    def test_reduce(self):
        assert action_code_label("reduce") == "减仓"

    def test_stop_loss(self):
        assert action_code_label("stop_loss") == "止损"

    def test_unknown_code_returns_input(self):
        assert action_code_label("unknown_code") == "unknown_code"
