"""Phase 9 Streamlit Dashboard — Holdings | Analysis | KG."""
from __future__ import annotations

import subprocess

DB_PATH = "data/db/aidc.duckdb"


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="AI 基建股持仓顾问", layout="wide")
    st.title("AI 基建股持仓顾问")

    tab_holdings, tab_analysis, tab_kg = st.tabs(["持仓", "AI 分析", "知识图谱"])

    # ── Holdings tab ──────────────────────────────────────────────────────────
    with tab_holdings:
        st.subheader("当前持仓")
        try:
            from engine.portfolio import check_portfolio_balance, load_holdings

            holdings = load_holdings(DB_PATH)
            if not holdings:
                st.info("暂无持仓数据（请在 data/agent_input/cn/holdings.yaml 中维护）")
            else:
                import pandas as pd

                from engine.macro_gate import get_macro_state

                macro = get_macro_state()
                df = pd.DataFrame([h.model_dump() for h in holdings])
                balance = check_portfolio_balance(df, macro_state=macro.value)
                if balance["rebalance_needed"]:
                    st.warning(
                        f"持仓比例需要再平衡（弹性股 {balance['elastic_ratio']:.1%}"
                        f" vs 目标 {balance['target_elastic']:.1%}）"
                    )
                else:
                    st.success("持仓比例正常")
                display_cols = [
                    "code", "name", "cost_price", "current_price",
                    "market_value", "pnl_pct", "category",
                ]
                st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
        except Exception as exc:
            st.error(f"持仓加载失败: {exc}")

    # ── Analysis tab ──────────────────────────────────────────────────────────
    with tab_analysis:
        from app.pages.analysis import format_signals_df, load_latest_for_ui

        col1, col2 = st.columns([3, 1])
        data = load_latest_for_ui(DB_PATH)
        if data:
            col1.caption(
                f"上次分析: {data['captured_at'].strftime('%Y-%m-%d %H:%M HKT')}"
            )
        else:
            col1.caption("暂无分析数据")

        if col2.button("Refresh 分析", type="primary"):
            with st.spinner("正在运行 AI 分析（约 30-60 秒）..."):
                result = subprocess.run(
                    [
                        "uv", "run", "python", "-m", "scripts.run_analysis",
                        "--once", "--db", DB_PATH,
                    ],
                    capture_output=True,
                    text=True,
                )
            if result.returncode == 0:
                st.success("分析完成，请刷新页面查看结果")
            else:
                st.error(f"分析失败: {result.stderr[-500:]}")
            data = load_latest_for_ui(DB_PATH)

        if data and data["signals"]:
            df = format_signals_df(data["signals"], data["change_pct_snapshot"])
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.divider()
            st.subheader("理由卡片")
            for sig in data["signals"]:
                with st.expander(
                    f"{sig.code} {sig.name} — 综合评分 {sig.composite_score:.0f}"
                ):
                    kg_ctx = data.get("kg_subgraph", {}).get(sig.code, [])
                    rag_ctx = data.get("rag_chunks", {}).get(sig.code, [])
                    reasoning = data["reasoning"].get(sig.code, "")
                    if kg_ctx:
                        st.markdown("**KG 上下文**")
                        for line in kg_ctx:
                            st.markdown(f"- {line}")
                    if rag_ctx:
                        st.markdown("**RAG 证据**")
                        for chunk in rag_ctx[:2]:
                            st.markdown(f"> {chunk[:200]}...")
                    if reasoning:
                        st.markdown(f"**AI 判断**: {reasoning}")
                    st.caption(
                        f"数据快照时间: {data['captured_at'].strftime('%Y-%m-%d %H:%M')}"
                    )
        elif data:
            st.info("分析完成但暂无信号输出")
            if data["errors"]:
                with st.expander("错误详情"):
                    for e in data["errors"]:
                        st.text(e)

    # ── KG tab ────────────────────────────────────────────────────────────────
    with tab_kg:
        st.subheader("Neo4j 知识图谱")
        st.components.v1.iframe("http://localhost:7474", height=600, scrolling=True)


if __name__ == "__main__":
    main()
