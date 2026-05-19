"""REQ-017: Tab 2 每日策略简报."""
from __future__ import annotations

import streamlit as st


def render_tab2() -> None:
    from app.data_loader import load_latest_signals, load_recommendations

    recs = load_recommendations()
    signals = load_latest_signals()

    if recs:
        st.markdown(recs, unsafe_allow_html=False)
    elif signals:
        st.subheader("今日信号")
        if isinstance(signals, list):
            for s in signals:
                st.write(s)
        else:
            st.json(signals)
    else:
        st.info("暂无策略简报。运行 AI 分析后自动生成。")
