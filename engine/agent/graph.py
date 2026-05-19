from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, StateGraph

from engine.agent.nodes import (
    kg_retrieval,
    portfolio_analyzer,
    rag_retrieval,
    signal_ranker,
    technical_fetcher,
)
from engine.agent.state import AnalysisState
from engine.kg.query import KGQuerier


def build_graph(
    *,
    kg_querier: KGQuerier | None = None,
    retriever_fn: Callable[[str, int], list[str]] | None = None,
    llm: ChatAnthropic | None = None,
) -> Any:
    """Build and compile the LangGraph StateGraph. Returns compiled graph."""
    builder: StateGraph = StateGraph(AnalysisState)

    builder.add_node("portfolio_analyzer", portfolio_analyzer)
    builder.add_node("technical_fetcher", technical_fetcher)
    builder.add_node(
        "kg_retrieval",
        lambda s: kg_retrieval(s, kg_querier=kg_querier),
    )
    builder.add_node(
        "rag_retrieval",
        lambda s: rag_retrieval(s, retriever_fn=retriever_fn),
    )
    builder.add_node(
        "signal_ranker",
        lambda s: signal_ranker(s, llm=llm),
    )

    builder.set_entry_point("portfolio_analyzer")
    builder.add_edge("portfolio_analyzer", "technical_fetcher")
    builder.add_edge("technical_fetcher", "kg_retrieval")
    builder.add_edge("kg_retrieval", "rag_retrieval")
    builder.add_edge("rag_retrieval", "signal_ranker")
    builder.add_edge("signal_ranker", END)

    return builder.compile()
