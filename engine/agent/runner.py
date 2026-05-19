from __future__ import annotations

from collections.abc import Callable

from langchain_anthropic import ChatAnthropic

from engine.agent.graph import build_graph
from engine.agent.state import AnalysisState, FrozenMarketSnapshot
from engine.kg.query import KGQuerier


def run_analysis(
    snapshot: FrozenMarketSnapshot,
    *,
    kg_querier: KGQuerier | None = None,
    retriever_fn: Callable[[str, int], list[str]] | None = None,
    llm: ChatAnthropic | None = None,
) -> AnalysisState:
    """Run the full analysis pipeline. All deps injectable for unit tests."""
    graph = build_graph(kg_querier=kg_querier, retriever_fn=retriever_fn, llm=llm)
    initial: AnalysisState = {
        "snapshot": snapshot,
        "kg_subgraph": {},
        "rag_chunks": {},
        "signals": [],
        "reasoning": {},
        "errors": [],
        "session_id": snapshot.session_id,
    }
    result: AnalysisState = graph.invoke(initial)
    return result
