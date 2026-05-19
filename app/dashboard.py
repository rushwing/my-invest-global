"""Phase 9 Streamlit Dashboard — Holdings | Analysis | KG."""
from __future__ import annotations

import subprocess

DB_PATH = "data/db/aidc.duckdb"


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="AI 基建股持仓顾问", layout="wide")
    st.title("AI 基建股持仓顾问")

    tab_holdings, tab_analysis, tab_kg, tab_backtest = st.tabs(
        ["持仓", "AI 分析", "知识图谱", "回测"]
    )

    # ── Holdings tab ──────────────────────────────────────────────────────────
    with tab_holdings:
        st.subheader("当前持仓")
        try:
            import pandas as pd

            from engine.macro_gate import get_macro_state
            from engine.portfolio import (
                check_portfolio_balance,
                load_holdings,
                load_holdings_raw,
            )

            sub_merged, sub_huaxi, sub_xinan = st.tabs(["合并视图", "华西证券", "西南证券"])

            _DISPLAY_COLS = [
                "code", "name", "account", "cost_price", "current_price",
                "market_value", "pnl_pct", "category",
            ]

            with sub_merged:
                holdings = load_holdings(DB_PATH)
                if not holdings:
                    st.info("暂无持仓数据（请在 data/agent_input/cn/holdings.yaml 中维护）")
                else:
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
                    st.dataframe(df[_DISPLAY_COLS], use_container_width=True, hide_index=True)

            def _account_tab(account_name: str) -> None:
                raw = load_holdings_raw(DB_PATH)
                rows = [h for h in raw if h.account == account_name]
                if not rows:
                    st.info(f"{account_name} 暂无持仓")
                    return
                df_raw = pd.DataFrame([h.model_dump() for h in rows])
                total_mv = df_raw["market_value"].sum()
                total_pnl = df_raw["pnl_amount"].sum()
                col_mv, col_pnl = st.columns(2)
                col_mv.metric("账户总市值", f"¥{total_mv:,.0f}")
                col_pnl.metric("账户总盈亏", f"¥{total_pnl:+,.2f}")
                cols = [c for c in _DISPLAY_COLS if c != "account"]
                st.dataframe(df_raw[cols], use_container_width=True, hide_index=True)

            with sub_huaxi:
                _account_tab("华西证券")

            with sub_xinan:
                _account_tab("西南证券")

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
            st.subheader("推理卡片")
            source_index = data.get("source_index", {})
            for sig in data["signals"]:
                action_icon = {
                    "strong_add": "🟢", "hold_add": "🟢", "hold": "🟡",
                    "reduce": "🔴", "stop_loss": "🔴", "take_profit_alert": "🟠",
                }.get(sig.action_code, "⚪")
                with st.expander(
                    f"{action_icon} {sig.code} {sig.name}"
                    f" — 综合 {sig.composite_score:.0f}分  {sig.action}"
                ):
                    # Sub-score breakdown
                    col_t, col_f, col_s = st.columns(3)
                    with col_t:
                        st.metric("技术面", f"{sig.technical_score:.0f}")
                        st.progress(sig.technical_score / 100)
                        if sig.technical_reasoning:
                            st.caption(sig.technical_reasoning)
                    with col_f:
                        st.metric("基本面", f"{sig.fundamental_score:.0f}")
                        st.progress(sig.fundamental_score / 100)
                        if sig.fundamental_reasoning:
                            st.caption(sig.fundamental_reasoning)
                    with col_s:
                        st.metric("情绪面", f"{sig.sentiment_score:.0f}")
                        st.progress(sig.sentiment_score / 100)
                        if sig.sentiment_reasoning:
                            st.caption(sig.sentiment_reasoning)

                    # Source traceability panel
                    idx = source_index.get(sig.code, {})
                    cited = sig.sources_cited or list(idx.keys())
                    visible = {ref: idx[ref] for ref in cited if ref in idx}
                    if not visible:
                        visible = idx  # fallback: show all sources
                    if visible:
                        with st.expander("原始数据来源"):
                            for ref, content in visible.items():
                                tag = (
                                    "🔵" if ref.startswith("S") else
                                    "🟢" if ref.startswith("T") else
                                    "🟣" if ref.startswith("K") else
                                    "🟤" if ref.startswith("R") else
                                    "⬛" if ref.startswith("M") else "⚪"
                                )
                                st.markdown(f"`{ref}` {tag} {content}")

                    st.caption(
                        f"数据快照: {data['captured_at'].strftime('%Y-%m-%d %H:%M HKT')}"
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

    # ── Backtest tab ──────────────────────────────────────────────────────────
    with tab_backtest:
        st.subheader("策略回测")
        try:
            from engine.portfolio import load_holdings

            holdings = load_holdings(DB_PATH)
            code_options = (
                [f"{h.code} {h.name}" for h in holdings] if holdings else ["300308 示例"]
            )
        except Exception:
            code_options = ["300308 示例"]

        col_code, col_strategy, col_run = st.columns([2, 2, 1])
        selected = col_code.selectbox("股票", code_options, key="bt_code")
        strategy = col_strategy.selectbox("策略", ["ma_cross", "macd_cross"], key="bt_strategy")

        if col_run.button("运行回测", type="primary"):
            code = selected.split()[0]
            with st.spinner("拉取数据并运行回测..."):
                try:
                    from app.pages.backtest import format_backtest_result
                    from engine.agent.technical_fetcher import fetch_ohlcv
                    from engine.backtest.runner import run_backtest

                    df_ohlcv = fetch_ohlcv(code, start="2023-01-01")
                    result = run_backtest(code=code, strategy=strategy, df=df_ohlcv)
                    summary = format_backtest_result(result)

                    m1, m2, m3 = st.columns(3)
                    m1.metric("累计收益率", f"{result.total_return:.2%}")
                    m2.metric("最大回撤", f"{result.max_drawdown:.2%}")
                    m3.metric("胜率", f"{result.win_rate:.2%}")

                    st.caption(
                        f"基准收益（买入持有）: {result.benchmark_return:.2%}"
                        f"  |  交易次数: {result.num_trades}"
                    )
                    st.line_chart(result.equity_curve, use_container_width=True)
                    st.dataframe(summary, use_container_width=True, hide_index=True)
                except Exception as exc:
                    st.error(f"回测失败: {exc}")


if __name__ == "__main__":
    main()
