"""REQ-020: My Invest Global — Phase 7 Dashboard entry point."""
from __future__ import annotations

import streamlit as st
from dotenv import load_dotenv

from app.auth import is_unlocked
from app.components.tab1_overview import render_tab1
from app.components.tab2_brief import render_tab2
from app.components.tab3_stock import render_tab3
from app.components.tab4_signals import render_tab4
from app.data_loader import DB_PATH
from app.sidebar import render_sidebar
from app.styles import inject_global_css


def render_locked_mask() -> None:
    st.markdown(
        """<div style="position:fixed;inset:0;z-index:999;backdrop-filter:blur(8px);
                        display:flex;align-items:center;justify-content:center;">
             <div style="background:#1C1C2E;border:1px solid #2A2A3E;border-radius:12px;
                         padding:32px;text-align:center;">
               <div style="font-size:32px;">🔒</div>
               <div style="color:#9AA0AC;margin-top:8px;">点击左侧解锁持仓数据</div>
             </div>
           </div>""",
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.markdown(
        '<span style="color:#00C47A;font-size:12px;">● 已解锁</span>',
        unsafe_allow_html=True,
    )


def main() -> None:
    load_dotenv()
    st.set_page_config(
        page_title="My Invest Global · A股 AI 基建",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_global_css()

    if not is_unlocked():
        render_sidebar(locked=True)
        render_locked_mask()
        st.stop()

    render_sidebar(locked=False)
    render_header()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["持仓总览", "每日策略简报", "个股深度分析", "信号仪表盘", "回测"]
    )
    with tab1:
        render_tab1()
    with tab2:
        render_tab2()
    with tab3:
        render_tab3()
    with tab4:
        render_tab4()

    # ── Backtest tab (REQ-035) ────────────────────────────────────────────────
    with tab5:
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
