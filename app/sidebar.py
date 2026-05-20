"""REQ-015: Holdings editor sidebar."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

_HOLDINGS_DIR = Path("data/agent_input/cn")
_COLS = ["code", "name", "category", "cost_price", "current_price", "quantity", "market_value"]


def save_holdings(df: pd.DataFrame, snapshot_date: date | None = None) -> None:
    _HOLDINGS_DIR.mkdir(parents=True, exist_ok=True)
    d = snapshot_date or date.today()
    path = _HOLDINGS_DIR / f"holdings_{d.strftime('%Y%m%d')}.csv"
    df.to_csv(path, index=False)


def render_sidebar(locked: bool = False) -> None:
    with st.sidebar:
        if locked:
            _render_locked()
        else:
            _render_editor()


def _render_locked() -> None:
    from app.auth import is_hash_configured, try_unlock
    st.markdown("### 🔒 持仓顾问")
    if not is_hash_configured():
        st.error("DASHBOARD_PASSPHRASE_HASH 未配置，无法解锁。请在 .env 中设置。")
        return
    pw = st.text_input("口令", type="password", key="_sidebar_pw")
    if st.button("解锁", type="primary", key="_sidebar_unlock"):
        if try_unlock(pw):
            st.rerun()
        else:
            st.error("口令错误")


def _render_editor() -> None:
    from app.data_loader import load_latest_holdings
    st.markdown("### 持仓编辑")

    if "holdings_editor" not in st.session_state:
        saved = load_latest_holdings()
        if saved is not None:
            saved = saved.reindex(columns=_COLS)
        st.session_state["holdings_editor"] = (
            saved if saved is not None else pd.DataFrame(columns=_COLS)
        )

    edited = st.data_editor(
        st.session_state["holdings_editor"],
        column_config={
            "code":          st.column_config.TextColumn("代码"),
            "name":          st.column_config.TextColumn("名称"),
            "category":      st.column_config.SelectboxColumn("类别", options=["白马股", "弹性股"]),
            "cost_price":    st.column_config.NumberColumn("成本价", format="%.2f"),
            "current_price": st.column_config.NumberColumn("现价", format="%.2f"),
            "quantity":      st.column_config.NumberColumn("数量", step=1),
            "market_value":  st.column_config.NumberColumn("市值", disabled=True, format="%.0f"),
        },
        num_rows="dynamic",
        use_container_width=True,
        key="holdings_data_editor",
    )
    if not edited.empty and "current_price" in edited.columns and "quantity" in edited.columns:
        edited = edited.copy()
        edited["market_value"] = (
            edited["current_price"].fillna(0) * edited["quantity"].fillna(0)
        )

    if st.button("保存", type="primary", key="_sidebar_save"):
        save_holdings(edited, date.today())
        st.cache_data.clear()
        st.rerun()
