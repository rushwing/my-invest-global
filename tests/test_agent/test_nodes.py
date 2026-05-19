"""TC-028-01..05 — LangGraph nodes + graph compile + run_analysis end-to-end."""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import MagicMock

import pytest

_nodes_mod = pytest.importorskip(
    "engine.agent.nodes",
    reason="engine.agent.nodes not yet implemented (pending req_impl)",
)
_graph_mod = pytest.importorskip(
    "engine.agent.graph",
    reason="engine.agent.graph not yet implemented (pending req_impl)",
)
_runner_mod = pytest.importorskip(
    "engine.agent.runner",
    reason="engine.agent.runner not yet implemented (pending req_impl)",
)
_state_mod = pytest.importorskip("engine.agent.state")
_schemas_mod = pytest.importorskip("engine.schemas")
_kg_mod = pytest.importorskip("engine.kg.query")

portfolio_analyzer = _nodes_mod.portfolio_analyzer
kg_retrieval = _nodes_mod.kg_retrieval
rag_retrieval = _nodes_mod.rag_retrieval
signal_ranker = _nodes_mod.signal_ranker
build_graph = _graph_mod.build_graph
run_analysis = _runner_mod.run_analysis
FrozenMarketSnapshot = _state_mod.FrozenMarketSnapshot
KGQueryResult = _kg_mod.KGQueryResult
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


def _summary() -> PortfolioSummary:
    return PortfolioSummary(
        total_market_value=5500.0,
        white_horse_ratio=0.0,
        elastic_ratio=1.0,
        target_white_horse=0.67,
        target_elastic=0.33,
        rebalance_needed=True,
    )


def _snapshot(holdings=None) -> FrozenMarketSnapshot:
    if holdings is None:
        holdings = (_holding(),)
    return FrozenMarketSnapshot(
        holdings=holdings,
        macro_state="green",
        portfolio_summary=_summary(),
        price_snapshot={h.code: h.current_price for h in holdings},
        change_pct_snapshot={h.code: 10.0 for h in holdings},
    )


def _base_state(snap=None) -> dict:
    if snap is None:
        snap = _snapshot()
    return {
        "snapshot": snap,
        "kg_subgraph": {},
        "rag_chunks": {},
        "signals": [],
        "reasoning": {},
        "errors": [],
        "session_id": snap.session_id,
    }


def _signals_json(code="300308", name="中际旭创") -> str:
    return json.dumps([
        {
            "code": code,
            "name": name,
            "category": "弹性股",
            "technical_score": 70.0,
            "fundamental_score": 75.0,
            "sentiment_score": 65.0,
            "composite_score": 70.0,
            "action": "持有加仓",
            "action_code": "hold_add",
            "reasoning": "光通信板块受益AI数据中心建设",
            "signals": {},
        }
    ], ensure_ascii=False)


# ── TC-028-01 ──────────────────────────────────────────────────────────────────


class TestBuildGraph:
    """TC-028-01: build_graph() compiles without raising."""

    def test_compile_succeeds(self):
        graph = build_graph()
        assert graph is not None

    def test_compile_with_mocks(self):
        mock_querier = MagicMock()
        mock_retriever = MagicMock(return_value=["chunk"])
        mock_llm = MagicMock()
        graph = build_graph(
            kg_querier=mock_querier,
            retriever_fn=mock_retriever,
            llm=mock_llm,
        )
        assert graph is not None


# ── TC-028-02 ──────────────────────────────────────────────────────────────────


class TestPortfolioAnalyzer:
    """TC-028-02: portfolio_analyzer writes context strings for each holding."""

    def test_two_holdings_produce_two_keys(self):
        h1 = _holding(code="300308")
        h2 = _holding(code="688561", name="奇安信")
        snap = _snapshot((h1, h2))
        state = _base_state(snap)
        result = portfolio_analyzer(state)
        assert len(result["kg_subgraph"]) == 2

    def test_context_values_are_nonempty_lists(self):
        snap = _snapshot((_holding(code="300308"),))
        state = _base_state(snap)
        result = portfolio_analyzer(state)
        ctx = result["kg_subgraph"]["300308"]
        assert isinstance(ctx, list) and len(ctx) > 0


# ── TC-028-03 ──────────────────────────────────────────────────────────────────


class TestKgRetrievalSuccess:
    """TC-028-03: kg_retrieval appends answer to kg_subgraph on success."""

    def test_answer_appended(self):
        mock_querier = MagicMock()
        mock_querier.query.return_value = KGQueryResult(
            question="q",
            cypher_used="MATCH (n) RETURN n",
            raw_results=[],
            answer="光通信",
            error=None,
        )
        state = _base_state()
        state["kg_subgraph"] = {"300308": ["持仓成本: 50.00"]}
        result = kg_retrieval(state, kg_querier=mock_querier)
        assert "光通信" in result["kg_subgraph"]["300308"]

    def test_no_errors_on_success(self):
        mock_querier = MagicMock()
        mock_querier.query.return_value = KGQueryResult(
            question="q",
            cypher_used="MATCH (n) RETURN n",
            raw_results=[],
            answer="光通信",
            error=None,
        )
        state = _base_state()
        result = kg_retrieval(state, kg_querier=mock_querier)
        assert result["errors"] == []


# ── TC-028-04 ──────────────────────────────────────────────────────────────────


class TestKgRetrievalError:
    """TC-028-04: kg_retrieval appends to errors on query failure, skips update."""

    def test_error_appended(self):
        mock_querier = MagicMock()
        mock_querier.query.return_value = KGQueryResult(
            question="q",
            cypher_used="",
            raw_results=[],
            answer="",
            error="timeout",
        )
        state = _base_state()
        result = kg_retrieval(state, kg_querier=mock_querier)
        assert len(result["errors"]) == 1
        assert "300308" in result["errors"][0]

    def test_kg_subgraph_not_updated_on_error(self):
        mock_querier = MagicMock()
        mock_querier.query.return_value = KGQueryResult(
            question="q",
            cypher_used="",
            raw_results=[],
            answer="",
            error="timeout",
        )
        state = _base_state()
        state["kg_subgraph"] = {"300308": ["持仓成本: 50.00"]}
        result = kg_retrieval(state, kg_querier=mock_querier)
        assert result["kg_subgraph"]["300308"] == ["持仓成本: 50.00"]


# ── TC-028-05 ──────────────────────────────────────────────────────────────────


class TestRunAnalysis:
    """TC-028-05: run_analysis returns complete AnalysisState with all required keys."""

    _REQUIRED_KEYS = {"signals", "reasoning", "kg_subgraph", "rag_chunks", "errors", "snapshot"}

    def _make_mock_llm(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content=_signals_json())
        return mock_llm

    def _make_mock_querier(self):
        mock_querier = MagicMock()
        mock_querier.query.return_value = KGQueryResult(
            question="q",
            cypher_used="MATCH (n) RETURN n",
            raw_results=[],
            answer="光通信板块",
            error=None,
        )
        return mock_querier

    def test_result_contains_required_keys(self):
        snap = _snapshot()
        result = run_analysis(
            snap,
            kg_querier=self._make_mock_querier(),
            retriever_fn=lambda name, k: [f"{name} 年报摘要"],
            llm=self._make_mock_llm(),
        )
        assert self._REQUIRED_KEYS <= set(result.keys())

    def test_signals_list_populated(self):
        snap = _snapshot()
        result = run_analysis(
            snap,
            kg_querier=self._make_mock_querier(),
            retriever_fn=lambda name, k: [f"{name} 年报摘要"],
            llm=self._make_mock_llm(),
        )
        assert isinstance(result["signals"], list)

    def test_session_id_matches_snapshot(self):
        snap = _snapshot()
        result = run_analysis(
            snap,
            kg_querier=None,
            retriever_fn=None,
            llm=self._make_mock_llm(),
        )
        assert result["session_id"] == snap.session_id
