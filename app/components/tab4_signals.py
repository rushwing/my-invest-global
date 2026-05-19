"""REQ-019: Tab 4 信号仪表盘."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ELASTIC_TARGETS: dict[str, int] = {"green": 38, "yellow": 33, "red": 20}


# ── Pure helpers (tested) ─────────────────────────────────────────────────────


def gauge_color(deviation: float) -> str:
    if abs(deviation) > 10:
        return "#E84040"
    if abs(deviation) > 5:
        return "#F5A623"
    return "#00C47A"


def chip_color(score: int) -> str:
    if score >= 70:
        return "#00C47A"
    if score >= 50:
        return "#F5A623"
    return "#E84040"


def trigger_row_style(status: str) -> str:
    if status == "triggered":
        return "background:#E8404020;color:#E84040;border-left:3px solid #E84040;"
    if status == "watch":
        return "color:#F5A623;"
    return "color:#9AA0AC;"


def render_scarcity_chip_html(
    code: str,
    name: str,
    rank: int,
    score: int,
    owned: bool,
    warn: bool,
    flow_values: list[float],
) -> str:
    color = chip_color(score)
    tier_cls = f"tier-{rank}"
    signal_text = "强势区间" if score >= 70 else ("震荡整理" if score >= 50 else "弱势区间")
    owned_icon = "◉ " if owned else ""
    warn_icon = " ⚠" if warn else ""
    strip_cells = "".join(build_flow_strip_cells(flow_values))

    return f"""<div style="border:1px solid #2A2A3E;border-radius:8px;padding:10px;
                           background:#1C1C2E;margin-bottom:8px;">
  <div class="chip-header" style="display:flex;align-items:center;margin-bottom:4px;">
    <span class="tier-badge {tier_cls}">Tier {rank}</span>
    <span class="rationale">{score:.0f}分 · {signal_text}</span>
  </div>
  <div style="font-size:14px;font-weight:600;color:{color};">
    {owned_icon}{name}{warn_icon}
  </div>
  <div style="font-size:11px;color:#9AA0AC;">{code}</div>
  <div class="flow-strip">{strip_cells}</div>
</div>"""


def build_flow_strip_cells(flow_values: list[float]) -> list[str]:
    cells: list[str] = []
    for v in flow_values[-5:]:
        cls = "pos" if v > 0 else "neg"
        cells.append(f'<span class="flow-cell {cls}" title="{v:.1f}亿"></span>')
    # Pad left with neutral cells if < 5 values
    while len(cells) < 5:
        cells.insert(0, '<span class="flow-cell neutral"></span>')
    return cells


def handle_enter_cta(code: str) -> None:
    st.session_state["tab3_code"] = code
    st.rerun()


def build_fund_flow_bar(fund_flow_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if fund_flow_df.empty or "trade_date" not in fund_flow_df.columns:
        fig.update_layout(
            plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
            font=dict(color="#E8EAED"), height=200,
        )
        return fig

    daily = (
        fund_flow_df.groupby("trade_date")["main_net_inflow"]
        .sum()
        .reset_index()
        .sort_values("trade_date")
    )
    colors = ["#00C47A" if v >= 0 else "#E84040" for v in daily["main_net_inflow"]]
    fig.add_trace(go.Bar(
        x=daily["trade_date"], y=daily["main_net_inflow"],
        marker_color=colors, name="主力净流入",
    ))
    fig.update_layout(
        plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
        font=dict(color="#E8EAED"), height=200,
        margin=dict(l=0, r=0, t=20, b=0),
        showlegend=False,
    )
    return fig


def build_breadth_scatter(breadth_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if not breadth_df.empty and "date" in breadth_df.columns and "up_ratio" in breadth_df.columns:
        fig.add_trace(go.Scatter(
            x=breadth_df["date"], y=breadth_df["up_ratio"],
            line=dict(color="#4F8EF7", width=1.5), name="涨跌比",
        ))
    fig.add_shape(
        type="line", x0=0, x1=1, xref="paper",
        y0=0.5, y1=0.5, line=dict(color="#888", dash="dot", width=1),
    )
    fig.update_layout(
        plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
        font=dict(color="#E8EAED"), height=200,
        margin=dict(l=0, r=0, t=20, b=0),
        yaxis=dict(range=[0, 1]),
        showlegend=False,
    )
    return fig


# ── Render function ───────────────────────────────────────────────────────────


def render_tab4() -> None:
    from app.data_loader import (
        compute_portfolio_metrics,
        compute_trigger_status,
        load_cloud_capex,
        load_fund_flow_5d,
        load_latest_holdings,
        load_macro_state,
        load_market_breadth,
        load_rebalance_history,
        load_scarcity_matrix,
    )

    macro = load_macro_state()
    state = macro.get("state", "yellow")

    holdings_df = load_latest_holdings()
    holding_codes: list[str] = (
        list(holdings_df["code"].dropna().unique())
        if holdings_df is not None and not holdings_df.empty
        else []
    )

    # ── MacroCyclePanel ──────────────────────────────────────────────────────
    st.subheader("宏观 CapEx 周期状态")

    # Dual chart header
    fund_flow_df = load_fund_flow_5d(holding_codes, days=20)
    breadth_df = load_market_breadth(days=20)
    col_left, col_right = st.columns(2)
    with col_left:
        st.caption("持仓主力净流入（近20日）")
        st.plotly_chart(build_fund_flow_bar(fund_flow_df), use_container_width=True)
    with col_right:
        st.caption("涨跌家数比（近20日）")
        st.plotly_chart(build_breadth_scatter(breadth_df), use_container_width=True)

    # Traffic light
    light_colors = {"green": "#00C47A", "yellow": "#F5A623", "red": "#E84040"}
    lights_html = "".join(
        f'<span style="display:inline-block;width:18px;height:18px;border-radius:50%;'
        f'background:{light_colors[s]};margin:0 6px;'
        f'{"box-shadow:0 0 16px 4px " + light_colors[s] if s == state else "opacity:0.25"}'
        f'"></span><span style="font-size:12px;color:#9AA0AC;">{label}</span>'
        for s, label in [("red", "收缩"), ("yellow", "平稳"), ("green", "增长")]
    )
    st.markdown(
        f'<div style="padding:12px 0;">{lights_html}</div>',
        unsafe_allow_html=True,
    )

    # CapEx table
    capex_df = load_cloud_capex()
    if not capex_df.empty:
        capex_df = capex_df.copy()
        capex_df["YoY"] = ((capex_df["fy2026_est"] - capex_df["fy2025"]) / capex_df["fy2025"]).map(
            lambda x: f"+{x:.1%}" if x >= 0 else f"{x:.1%}"
        )
        st.dataframe(
            capex_df.rename(columns={
                "vendor": "云厂商", "fy2025": "FY2025A ($B)", "fy2026_est": "FY2026E ($B)",
            }),
            use_container_width=True,
            hide_index=True,
        )

    # Manual override
    with st.expander("手动覆盖宏观状态"):
        from engine.macro_gate import MacroState, set_macro_state_override
        selected = st.selectbox("覆盖状态", ["green", "yellow", "red"],
                                index=["green", "yellow", "red"].index(state),
                                key="macro_override_select")
        if st.button("应用覆盖", key="macro_override_btn"):
            set_macro_state_override(MacroState(selected))
            st.cache_data.clear()
            st.rerun()

    st.divider()

    # ── Gauge + Triggers ─────────────────────────────────────────────────────
    st.subheader("仓位再平衡仪表盘")

    if holdings_df is not None and not holdings_df.empty:
        metrics = compute_portfolio_metrics(holdings_df, state)
        elastic_pct = metrics["elastic_pct"]
        elastic_target = float(metrics["elastic_target"])
        deviation = elastic_pct - elastic_target
        g_color = gauge_color(deviation)

        col_g, col_t = st.columns([1, 2])
        with col_g:
            st.markdown(
                f"""<div style="text-align:center;padding:20px;">
                  <div style="font-size:32px;font-weight:700;color:{g_color};">{elastic_pct:.1f}%</div>
                  <div style="font-size:12px;color:#9AA0AC;">弹性仓位（目标 {elastic_target:.0f}%）</div>
                  <div style="font-size:14px;color:{g_color};margin-top:4px;">
                    偏差 {deviation:+.1f}%
                  </div>
                </div>""",
                unsafe_allow_html=True,
            )
        with col_t:
            triggers_df = compute_trigger_status(holdings_df, state)
            for _, row in triggers_df.iterrows():
                style = trigger_row_style(row["status"])
                st.markdown(
                    f'<div style="padding:6px 10px;margin:2px 0;border-radius:4px;font-size:12px;{style}">'  # noqa: E501
                    f'<b>{row["trigger"]}</b> — {row["direction"]} {row["magnitude"]}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.info("暂无持仓数据，无法计算仓位偏差。")

    st.divider()

    # ── ScarcityMatrix ───────────────────────────────────────────────────────
    st.subheader("板块紧缺度矩阵")

    scarcity_df = load_scarcity_matrix()
    if scarcity_df.empty:
        st.info("暂无稀缺性矩阵数据（data/processed/scarcity_matrix.json 不存在）。")
    else:
        flow_map: dict[str, list[float]] = {}
        if not fund_flow_df.empty:
            for code, grp in fund_flow_df.groupby("code"):
                flow_map[str(code)] = list(grp.sort_values("trade_date")["main_net_inflow"].tail(5))

        tier_cols = st.columns(4)
        for tier in range(1, 5):
            tier_df = scarcity_df[scarcity_df["rank"] == tier]
            with tier_cols[tier - 1]:
                tier_color = {1: "#FF7A1A", 2: "#F5A623", 3: "#9AA0AC", 4: "#4F8EF7"}[tier]
                st.markdown(
                    f'<div style="font-size:12px;font-weight:600;color:{tier_color};margin-bottom:8px;">'  # noqa: E501
                    f'Tier {tier}</div>',
                    unsafe_allow_html=True,
                )
                for _, row in tier_df.iterrows():
                    code = str(row["code"])
                    html = render_scarcity_chip_html(
                        code=code,
                        name=str(row.get("name", code)),
                        rank=int(row.get("rank", tier)),
                        score=int(row.get("composite_score", 50)),
                        owned=bool(row.get("owned", False)),
                        warn=bool(row.get("warn", False)),
                        flow_values=flow_map.get(code, []),
                    )
                    st.html(html)
                    if st.button("进入 →", key=f"enter_{code}", use_container_width=True):
                        handle_enter_cta(code)

    st.divider()

    # ── History Timeline ─────────────────────────────────────────────────────
    st.subheader("历史再平衡时间线")
    history_df = load_rebalance_history()
    if history_df.empty:
        st.info("暂无历史再平衡记录。")
    else:
        st.dataframe(
            history_df.sort_values("date", ascending=False),
            column_config={
                "date":   st.column_config.DateColumn("日期"),
                "action": st.column_config.TextColumn("操作"),
                "reason": st.column_config.TextColumn("原因"),
            },
            use_container_width=True,
            hide_index=True,
        )
