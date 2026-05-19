"""REQ-016: Tab 1 持仓总览."""
from __future__ import annotations

import streamlit as st


def render_tab1() -> None:
    from app.data_loader import compute_portfolio_metrics, load_latest_holdings, load_macro_state

    holdings_df = load_latest_holdings()
    macro = load_macro_state()
    state = macro.get("state", "yellow")

    if holdings_df is None or holdings_df.empty:
        st.info("暂无持仓数据。请在侧边栏录入持仓。")
        return

    metrics = compute_portfolio_metrics(holdings_df, state)
    col1, col2, col3 = st.columns(3)
    col1.metric("总市值", f"¥{metrics['total_mv']:,.0f}")
    col2.metric(
        f"弹性仓位（目标 {metrics['elastic_target']}%）",
        f"{metrics['elastic_pct']:.1f}%",
        delta=f"{metrics['elastic_pct'] - metrics['elastic_target']:.1f}%",
    )
    col3.metric("白马仓位", f"{metrics['white_pct']:.1f}%")

    st.dataframe(
        metrics["df"][["code", "name", "category", "market_value", "pct"]].rename(columns={
            "code": "代码", "name": "名称", "category": "类别",
            "market_value": "市值", "pct": "仓位%",
        }),
        use_container_width=True,
        hide_index=True,
    )
