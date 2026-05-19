"""TC-027-01..04 — FrozenMarketSnapshot frozen model + AnalysisState TypedDict."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest

_state_mod = pytest.importorskip(
    "engine.agent.state",
    reason="engine.agent.state not yet implemented (pending req_impl)",
)
_schemas_mod = pytest.importorskip("engine.schemas")

FrozenMarketSnapshot = _state_mod.FrozenMarketSnapshot
AnalysisState = _state_mod.AnalysisState
build_snapshot = _state_mod.build_snapshot

HoldingRow = _schemas_mod.HoldingRow
HoldingCategory = _schemas_mod.HoldingCategory
PortfolioSummary = _schemas_mod.PortfolioSummary


def _holding(**kwargs) -> HoldingRow:
    defaults: dict = {
        "schema_version": "1.0",
        "date": date(2026, 5, 18),
        "code": "300308",
        "name": "中际旭创",
        "cost_price": 50.0,
        "current_price": 55.0,
        "quantity": 100,
        "market_value": 5500.0,
        "pnl_pct": "+10.0%",
        "pnl_amount": 500.0,
        "category": HoldingCategory.ELASTIC,
        "sector": "光通信",
        "notes": "",
    }
    defaults.update(kwargs)
    return HoldingRow(**defaults)


def _summary(**kwargs) -> PortfolioSummary:
    defaults: dict = {
        "total_market_value": 5500.0,
        "white_horse_ratio": 0.0,
        "elastic_ratio": 1.0,
        "target_white_horse": 0.67,
        "target_elastic": 0.33,
        "rebalance_needed": True,
    }
    defaults.update(kwargs)
    return PortfolioSummary(**defaults)


def _snapshot(**kwargs) -> FrozenMarketSnapshot:
    defaults: dict = {
        "holdings": (_holding(),),
        "macro_state": "green",
        "portfolio_summary": _summary(),
        "price_snapshot": {"300308": 55.0},
        "change_pct_snapshot": {"300308": 10.0},
    }
    defaults.update(kwargs)
    return FrozenMarketSnapshot(**defaults)


# ── TC-027-01 ──────────────────────────────────────────────────────────────────


class TestFrozenMutation:
    """TC-027-01: FrozenMarketSnapshot rejects field assignment."""

    def test_mutation_raises(self):
        from pydantic import ValidationError

        snap = _snapshot()
        with pytest.raises((ValidationError, TypeError)):
            snap.holdings = ()  # type: ignore[misc]

    def test_session_id_immutable(self):
        from pydantic import ValidationError

        snap = _snapshot()
        with pytest.raises((ValidationError, TypeError)):
            snap.session_id = "new-id"  # type: ignore[misc]


# ── TC-027-02 ──────────────────────────────────────────────────────────────────


class TestBuildSnapshot:
    """TC-027-02: build_snapshot returns correct snapshot under mocked dependencies."""

    def _run(self, holdings):
        from engine.macro_gate import MacroState

        with (
            patch("engine.portfolio.load_holdings", create=True, return_value=holdings),
            patch(
                "engine.macro_gate.get_macro_state",
                return_value=MacroState.GREEN,
            ),
            patch(
                "engine.portfolio.compute_portfolio_summary",
                create=True,
                return_value=_summary(),
            ),
        ):
            return build_snapshot("fake.duckdb")

    def test_holdings_length(self):
        h1 = _holding(code="300308")
        h2 = _holding(code="688561", name="奇安信")
        snap = self._run([h1, h2])
        assert len(snap.holdings) == 2

    def test_macro_state_is_string(self):
        snap = self._run([_holding()])
        assert isinstance(snap.macro_state, str)
        assert snap.macro_state in ("green", "yellow", "red")

    def test_session_id_non_empty(self):
        snap = self._run([_holding()])
        assert snap.session_id != ""

    def test_price_snapshot_populated(self):
        h = _holding(code="300308", current_price=55.0)
        snap = self._run([h])
        assert snap.price_snapshot.get("300308") == 55.0

    def test_pnl_pct_parsed_to_float(self):
        h = _holding(code="300308", pnl_pct="+10.0%")
        snap = self._run([h])
        assert snap.change_pct_snapshot.get("300308") == pytest.approx(10.0)

    def test_pnl_pct_invalid_defaults_to_zero(self):
        h = _holding(code="300308", pnl_pct="N/A")
        snap = self._run([h])
        assert snap.change_pct_snapshot.get("300308") == 0.0


# ── TC-027-03 ──────────────────────────────────────────────────────────────────


class TestAnalysisStateKeys:
    """TC-027-03: AnalysisState TypedDict contains all required keys."""

    _REQUIRED = {
        "snapshot",
        "kg_subgraph",
        "rag_chunks",
        "signals",
        "reasoning",
        "errors",
        "session_id",
    }

    def test_all_keys_present(self):
        annotations = AnalysisState.__annotations__
        assert self._REQUIRED <= set(annotations.keys())


# ── TC-027-04 ──────────────────────────────────────────────────────────────────


class TestSnapshotSerialization:
    """TC-027-04: FrozenMarketSnapshot serializes to JSON without error."""

    def test_model_dump_no_exception(self):
        snap = _snapshot()
        result = snap.model_dump()
        assert isinstance(result, dict)

    def test_holdings_serialized_as_list(self):
        snap = _snapshot()
        result = snap.model_dump()
        assert isinstance(result["holdings"], (list, tuple))
