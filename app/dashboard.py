"""REQ-020: My Invest Global — Phase 7 Dashboard entry point."""
from __future__ import annotations

import time

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
from app.utils.runner import get_status, trigger_analysis, trigger_refresh


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


def _market_status() -> str:
    """Return 'live' during A-share trading hours (CST), else 'closed'."""
    from datetime import datetime, timedelta, timezone
    cst = timezone(timedelta(hours=8))
    now = datetime.now(cst)
    if now.weekday() >= 5:
        return "closed"
    t = now.hour * 60 + now.minute
    if (9 * 60 + 30 <= t <= 11 * 60 + 30) or (13 * 60 <= t <= 15 * 60):
        return "live"
    return "closed"


def _fmt_time(dt: object) -> str:
    from datetime import datetime
    if not isinstance(dt, datetime):
        return "—"
    return dt.strftime("%H:%M")


def render_action_bar() -> None:
    """Global action bar: system status + refresh/analyze triggers + auth indicator."""
    status = get_status()
    refresh_running  = status["refresh_status"]  == "running"
    analysis_running = status["analysis_status"] == "running"
    has_error = status["refresh_status"] == "error" or status["analysis_status"] == "error"
    market = _market_status()

    # Auto-poll every 2 s while a task is running so the UI updates on completion
    if refresh_running or analysis_running:
        time.sleep(2)
        st.rerun()

    # ── Status dot ────────────────────────────────────────────────────────────
    if market == "live" and not has_error:
        status_html = '<span style="color:#00C47A;font-size:11px;font-family:JetBrains Mono,monospace;">● LIVE · A股盘中</span>'
    elif has_error:
        status_html = '<span style="color:#E84040;font-size:11px;font-family:JetBrains Mono,monospace;">● 数据异常</span>'
    else:
        status_html = '<span style="color:#5C616E;font-size:11px;font-family:JetBrains Mono,monospace;">● 盘后</span>'

    last_refresh_str  = f"刷新 {_fmt_time(status['last_refresh'])}"  if status["last_refresh"]  else "未刷新"
    last_analysis_str = f"分析 {_fmt_time(status['last_analysis'])}" if status["last_analysis"] else "未分析"

    col_status, col_r, col_a, col_ts, col_lock = st.columns([2, 1, 1, 2, 1])

    with col_status:
        st.markdown(status_html, unsafe_allow_html=True)

    with col_r:
        label_r = "⟳ 刷新中..." if refresh_running else "↻ 刷新行情"
        if st.button(label_r, disabled=refresh_running, key="_bar_refresh", use_container_width=True):
            trigger_refresh()
            st.cache_data.clear()
            st.rerun()

    with col_a:
        label_a = "⟳ 分析中..." if analysis_running else "▶ 运行分析"
        if st.button(label_a, type="primary", disabled=analysis_running,
                     key="_bar_analyze", use_container_width=True):
            trigger_analysis()
            st.rerun()

    with col_ts:
        ts_color = "#E84040" if has_error else "#5C616E"
        error_hint = ""
        if status["refresh_error"]:
            error_hint += " · 刷新失败"
        if status["analysis_error"]:
            error_hint += " · 分析失败"
        st.markdown(
            f'<div style="font-size:11px;color:{ts_color};font-family:JetBrains Mono,monospace;'
            f'text-align:right;padding-top:6px;">'
            f'{last_refresh_str} · {last_analysis_str}{error_hint}</div>',
            unsafe_allow_html=True,
        )

    with col_lock:
        if st.button("🔒 锁定", key="_bar_lock", use_container_width=True):
            st.session_state["unlocked"] = False
            st.rerun()

    st.markdown('<hr style="margin:4px 0 8px;border-color:#2A2A3E;">', unsafe_allow_html=True)


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
    render_action_bar()

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
