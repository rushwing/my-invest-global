"""REQ-017 / REQ-041: Tab 2 每日策略简报."""
from __future__ import annotations

import streamlit as st

# ── T+1 rebalance summary bar ─────────────────────────────────────────────────

def _count_signals(signals: list) -> dict[str, int]:
    reduce_codes = {"reduce", "stop_loss"}
    add_codes    = {"strong_add", "hold_add", "buy", "add"}
    n_reduce = sum(1 for s in signals if s.get("action_code") in reduce_codes)
    n_add    = sum(1 for s in signals if s.get("action_code") in add_codes)
    return {"reduce": n_reduce, "add": n_add}


def render_t1_rebalance_bar(signals: list) -> None:
    counts = _count_signals(signals)
    total_actionable = len(signals)

    cells = [
        {"label": "今日可操作", "value": f"{total_actionable} 只", "tone": "text",    "icon": "✓"},
        {"label": "建议减仓",   "value": f"{counts['reduce']} 只", "tone": "bear",    "icon": "↓"},
        {"label": "建议加仓",   "value": f"{counts['add']} 只",    "tone": "bull",    "icon": "↑"},
        {"label": "T+1 锁仓",  "value": "— 只",                   "tone": "neutral", "icon": "🔒"},
    ]
    tone_color = {"bull": "#00C47A", "bear": "#E84040", "neutral": "#F5A623", "text": "#E8EAED"}

    parts = []
    for cell in cells:
        c = tone_color[cell["tone"]]
        parts.append(
            f'<div style="flex:1;padding:14px 16px;display:flex;align-items:center;gap:10px;'
            f'border-right:1px solid #2A2A3E;">'
            f'<div style="width:30px;height:30px;background:{c}18;border:1px solid {c}44;'
            f'border-radius:6px;display:flex;align-items:center;justify-content:center;'
            f'font-size:13px;color:{c};flex-shrink:0;">{cell["icon"]}</div>'
            f'<div>'
            f'<div style="font-size:10px;color:#9AA0AC;letter-spacing:0.06em;margin-bottom:2px;">'
            f'{cell["label"]}</div>'
            f'<div style="font-size:16px;font-weight:600;color:{c};'
            f'font-family:JetBrains Mono,monospace;">{cell["value"]}</div>'
            f'</div></div>'
        )

    st.markdown(
        '<div style="display:flex;background:#1C1C2E;border:1px solid #2A2A3E;'
        'border-radius:8px;overflow:hidden;margin-bottom:8px;">'
        + "".join(parts)
        + '</div>',
        unsafe_allow_html=True,
    )

    col_hint, col_btn = st.columns([4, 1])
    with col_hint:
        st.caption("T+1 锁仓数据将在调仓分析页实现后填入")
    with col_btn:
        if st.button("→ 进入调仓分析", key="_t2_jump_rebalance", use_container_width=True):
            st.session_state["active_tab"] = 4
            st.info("调仓分析页（Tab 5）正在开发中，敬请期待。")


# ── Main render ───────────────────────────────────────────────────────────────

def render_tab2() -> None:
    from app.data_loader import load_latest_signals, load_recommendations
    from app.utils.runner import get_status, trigger_analysis

    # Tab-level header with per-tab action
    col_title, col_btn = st.columns([5, 1])
    with col_title:
        status = get_status()
        ts = status.get("last_analysis")
        ts_str = ts.strftime("%Y-%m-%d %H:%M") if ts else "—"
        st.markdown(
            f'<div style="font-size:12px;color:#5C616E;font-family:JetBrains Mono,monospace;'
            f'margin-bottom:4px;">分析于 {ts_str}</div>',
            unsafe_allow_html=True,
        )
    with col_btn:
        if st.button("▶ 分析自选", key="_t2_watchlist", use_container_width=True,
                     help="仅对自选（category=自选）股票运行分析"):
            trigger_analysis()
            st.rerun()

    # Content
    recs = load_recommendations()
    signals = load_latest_signals() or []

    if recs:
        st.markdown(recs, unsafe_allow_html=False)
    elif signals:
        st.subheader("今日信号")
        for s in signals:
            st.write(s)
    else:
        st.info("暂无策略简报。点击顶部 [▶ 运行分析] 生成。")

    # T+1 rebalance summary bar (show only when signals exist)
    if signals:
        st.divider()
        st.markdown(
            '<div style="font-size:11px;color:#9AA0AC;letter-spacing:0.06em;'
            'margin-bottom:6px;">今日可执行调仓 · T+1 已计入</div>',
            unsafe_allow_html=True,
        )
        render_t1_rebalance_bar(signals)
