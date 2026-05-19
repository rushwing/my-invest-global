from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from engine.agent.state import AnalysisState, FrozenMarketSnapshot
from engine.kg.query import KGQuerier
from engine.schemas import StockSignal

_SIGNAL_RANKER_SYSTEM = (
    "你是一个专业的A股投资助手。根据持仓快照、KG知识图谱上下文和年报RAG检索结果，"
    "对每只股票生成投资信号。\n"
    "\n"
    "每只股票的分析输入会附带带编号的数据源（S=快照数据, K=KG图谱, R=RAG年报, M=宏观）。\n"
    "在 technical_reasoning / fundamental_reasoning / sentiment_reasoning 中，"
    "必须用 [Sn] [Kn] [Rn] [M] 标注推理依据的来源编号。\n"
    "\n"
    "输出严格的JSON数组，每个元素包含：\n"
    "- code: 股票代码（6位数字）\n"
    "- name: 股票名称\n"
    "- category: 持仓类别（白马股 或 弹性股）\n"
    "- technical_score: 技术面评分 0-100（基于价格、成本、涨跌幅）\n"
    "- fundamental_score: 基本面评分 0-100（基于板块景气、年报数据）\n"
    "- sentiment_score: 情绪面评分 0-100（基于KG机构持仓、宏观状态）\n"
    "- composite_score: 综合评分 0-100\n"
    "- action: 操作建议（中文）\n"
    "- action_code: 操作代码（strong_add/hold_add/hold/reduce/stop_loss/take_profit_alert）\n"
    "- technical_reasoning: 技术面推理（1-2句，引用数据源编号）\n"
    "- fundamental_reasoning: 基本面推理（1-2句，引用数据源编号）\n"
    "- sentiment_reasoning: 情绪面推理（1-2句，引用数据源编号）\n"
    "- sources_cited: 本条信号实际引用的数据源编号列表，如 [\"S1\",\"S3\",\"M\"]\n"
    "\n"
    "只输出JSON数组，不要包含任何解释文字。"
)


def _build_source_index(
    code: str,
    kg_items: list[str],
    rag_items: list[str],
    macro_state: str,
) -> dict[str, str]:
    """Build numbered source index for one stock. Returns {ref: labelled_content}."""
    index: dict[str, str] = {}
    s_n = 1
    for item in kg_items:
        index[f"S{s_n}"] = f"[快照] {item}"
        s_n += 1
    index["M"] = f"[宏观] 宏观状态: {macro_state}"
    k_n = 1
    for item in kg_items[s_n - 1:]:  # KG facts appended after snapshot entries
        index[f"K{k_n}"] = f"[KG] {item}"
        k_n += 1
    r_n = 1
    for chunk in rag_items:
        index[f"R{r_n}"] = f"[RAG] {chunk[:120]}"
        r_n += 1
    return index


def _format_sources_for_prompt(index: dict[str, str]) -> str:
    return "\n".join(f"  {ref}: {content}" for ref, content in index.items())


def portfolio_analyzer(state: AnalysisState) -> dict[str, Any]:
    """Extract holding context strings from snapshot. No external calls."""
    snap: FrozenMarketSnapshot = state["snapshot"]
    context: dict[str, list[str]] = {}
    for h in snap.holdings:
        context[h.code] = [
            f"持仓成本: {h.cost_price:.2f}",
            f"当前价格: {h.current_price:.2f}",
            f"市值: {h.market_value:.0f}",
            f"板块: {h.sector}",
        ]
    return {"kg_subgraph": context, "rag_chunks": {}, "source_index": {}, "errors": []}


def kg_retrieval(
    state: AnalysisState,
    *,
    kg_querier: KGQuerier | None = None,
) -> dict[str, Any]:
    """Query KG for each holding. Skips on error (degraded mode)."""
    snap = state["snapshot"]
    kg_subgraph: dict[str, list[str]] = dict(state.get("kg_subgraph", {}))  # type: ignore[arg-type]
    errors: list[str] = list(state.get("errors", []))  # type: ignore[arg-type]

    if kg_querier is None:
        return {"kg_subgraph": kg_subgraph, "errors": errors}

    for h in snap.holdings:
        question = f"{h.name}（{h.code}）属于哪些板块和主题概念？有哪些机构持仓？"
        result = kg_querier.query(question)
        if result.error:
            errors.append(f"KG[{h.code}]: {result.error}")
        else:
            existing = kg_subgraph.get(h.code, [])
            kg_subgraph[h.code] = existing + [result.answer]

    return {"kg_subgraph": kg_subgraph, "errors": errors}


def rag_retrieval(
    state: AnalysisState,
    *,
    retriever_fn: Callable[[str, int], list[str]] | None = None,
) -> dict[str, Any]:
    """Retrieve RAG chunks for each holding. Skips if no retriever injected."""
    snap = state["snapshot"]
    rag_chunks: dict[str, list[str]] = {}
    errors: list[str] = list(state.get("errors", []))  # type: ignore[arg-type]

    if retriever_fn is None:
        return {"rag_chunks": rag_chunks, "errors": errors}

    for h in snap.holdings:
        try:
            rag_chunks[h.code] = retriever_fn(h.name, 5)
        except Exception as exc:
            errors.append(f"RAG[{h.code}]: {exc}")

    return {"rag_chunks": rag_chunks, "errors": errors}


def signal_ranker(
    state: AnalysisState,
    *,
    llm: ChatAnthropic | None = None,
) -> dict[str, Any]:
    """Synthesize StockSignals using LLM. Injectable for unit tests."""
    snap = state["snapshot"]
    errors: list[str] = list(state.get("errors", []))  # type: ignore[arg-type]
    kg_subgraph: dict[str, list[str]] = state.get("kg_subgraph", {})  # type: ignore[arg-type]
    rag_chunks: dict[str, list[str]] = state.get("rag_chunks", {})  # type: ignore[arg-type]

    if llm is None:
        import os
        kwargs: dict = {"model": "claude-sonnet-4-6", "max_tokens": 4096}
        if base := os.environ.get("ANTHROPIC_API_BASE"):
            kwargs["base_url"] = base
        llm = ChatAnthropic(**kwargs)  # type: ignore[call-arg]

    # Build per-stock source index and format for prompt
    source_index: dict[str, dict[str, str]] = {}
    stocks_section = ""
    for h in snap.holdings:
        kg_items = kg_subgraph.get(h.code, [])
        rag_items = rag_chunks.get(h.code, [])
        # First 4 kg_items are always snapshot entries from portfolio_analyzer
        snap_items = kg_items[:4]
        kg_extra = kg_items[4:]
        idx: dict[str, str] = {}
        for i, item in enumerate(snap_items, 1):
            idx[f"S{i}"] = f"[快照] {item}"
        idx["M"] = f"[宏观] 宏观状态: {snap.macro_state}"
        for i, item in enumerate(kg_extra, 1):
            idx[f"K{i}"] = f"[KG] {item}"
        for i, chunk in enumerate(rag_items, 1):
            idx[f"R{i}"] = f"[RAG] {chunk[:120]}"
        source_index[h.code] = idx

        stocks_section += (
            f"\n--- {h.code} {h.name} ({h.category}) ---\n"
            f"{_format_sources_for_prompt(idx)}\n"
        )

    user_content = (
        f"宏观状态: {snap.macro_state}\n"
        f"持仓数量: {len(snap.holdings)}\n"
        f"\n各股票数据源:\n{stocks_section}"
    )

    try:
        response = llm.invoke(
            [SystemMessage(content=_SIGNAL_RANKER_SYSTEM), HumanMessage(content=user_content)]
        )
        text = str(response.content).strip()
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].lstrip()
        raw = json.loads(text)
        signals: list[StockSignal] = []
        reasoning: dict[str, str] = {}
        for item in raw:
            tech_r = item.pop("technical_reasoning", "")
            fund_r = item.pop("fundamental_reasoning", "")
            sent_r = item.pop("sentiment_reasoning", "")
            cited = item.pop("sources_cited", [])
            item.pop("signals", None)
            item.pop("reasoning", None)
            sig = StockSignal(
                **item,
                signals={},
                technical_reasoning=tech_r,
                fundamental_reasoning=fund_r,
                sentiment_reasoning=sent_r,
                sources_cited=cited,
            )
            signals.append(sig)
            reasoning[sig.code] = "\n".join(filter(None, [tech_r, fund_r, sent_r]))

        from engine.agent.claim_verifier import verify_signals

        violations = verify_signals(signals, snap)
        for v in violations:
            errors.append(
                f"ClaimViolation[{v.code}][{v.field}]:"
                f" claimed={v.claimed_value} actual={v.actual_value}"
            )
        return {
            "signals": signals,
            "reasoning": reasoning,
            "source_index": source_index,
            "errors": errors,
        }
    except Exception as exc:
        errors.append(f"signal_ranker: {exc}")
        return {"signals": [], "reasoning": {}, "source_index": source_index, "errors": errors}
