"""REQ-020: My Invest Global — Phase 7 Dashboard entry point."""
from __future__ import annotations

import streamlit as st

from app.auth import is_unlocked
from app.components.tab1_overview import render_tab1
from app.components.tab2_brief import render_tab2
from app.components.tab3_stock import render_tab3
from app.components.tab4_signals import render_tab4
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

    tab1, tab2, tab3, tab4 = st.tabs(["持仓总览", "每日策略简报", "个股深度分析", "信号仪表盘"])
    with tab1:
        render_tab1()
    with tab2:
        render_tab2()
    with tab3:
        render_tab3()
    with tab4:
        render_tab4()


if __name__ == "__main__":
    main()
