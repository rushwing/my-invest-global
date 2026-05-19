"""Phase 11 — 仪表盘筹码面板 (REQ-039).

Streamlit page: render_chip_panel + chip_panel_page.
build_chip_chart is a pure Plotly function, testable without Streamlit.
"""

from __future__ import annotations

import streamlit as st

from engine.agent.chip_analysis import ChipAnalysis
from engine.agent.chip_fetcher import ChipSummary
from engine.agent.chip_screenshot_parser import parse_chip_screenshot


def build_chip_chart(summary: ChipSummary, current_price: float):
    """Build a Plotly horizontal bar chart of chip distribution.

    Pure function — no Streamlit calls.
    Colors: green (#00C47A) below current price, red (#E84040) at/above.
    """
    import plotly.graph_objects as go

    mids = [(b.price_lower + b.price_upper) / 2 for b in summary.bars]
    ratios = [b.chip_ratio for b in summary.bars]
    colors = ["#00C47A" if m < current_price else "#E84040" for m in mids]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=ratios,
            y=mids,
            orientation="h",
            marker={"color": colors},
            showlegend=False,
        )
    )

    fig.update_layout(
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font={"color": "#ffffff"},
        xaxis={"title": "筹码占比"},
        yaxis={"title": "价格"},
        margin={"l": 50, "r": 20, "t": 20, "b": 40},
    )

    fig.add_shape(
        type="line",
        x0=0, x1=1, xref="paper",
        y0=current_price, y1=current_price, yref="y",
        line={"color": "#ffffff", "width": 1, "dash": "dash"},
        label={"text": f"现价 {current_price}"},
    )
    fig.add_shape(
        type="line",
        x0=0, x1=1, xref="paper",
        y0=summary.avg_cost, y1=summary.avg_cost, yref="y",
        line={"color": "#ffdd57", "width": 1, "dash": "dot"},
        label={"text": f"均成本 {summary.avg_cost}"},
    )

    return fig


def render_chip_panel(
    code: str,
    current_price: float,
    analysis: ChipAnalysis,
    summary: ChipSummary | None = None,
) -> None:
    """Render chip analysis metrics + signal card + optional histogram."""
    cols = st.columns(4)

    delta_profitable = "⚠ 高浮盈" if analysis.profitable_pct >= 0.95 else None
    with cols[0]:
        st.metric("获利比例", f"{analysis.profitable_pct * 100:.1f}%", delta=delta_profitable)
    with cols[1]:
        st.metric("均成本", f"¥{analysis.avg_cost:.2f}")
    with cols[2]:
        st.metric("集中度", f"{analysis.concentration:.1f}%")
    with cols[3]:
        st.metric("偏离度", f"{analysis.cost_deviation_pct:+.1f}%")

    if analysis.above_90_band:
        st.error(analysis.signal_summary)
    elif analysis.below_90_band:
        st.warning(analysis.signal_summary)
    else:
        st.info(analysis.signal_summary)

    if summary is not None and summary.bars:
        st.plotly_chart(build_chip_chart(summary, current_price))


def chip_panel_page() -> None:
    """Full Streamlit page entry point for chip analysis."""
    st.title("筹码分析")

    code = st.selectbox("股票代码", ["688143", "000001", "300308", "600036"])
    current_price = st.number_input("当前价格", min_value=0.01, value=10.0, step=0.01)
    source = st.radio("数据源", ["akshare数据", "截图解析（OCR）"])

    if source == "截图解析（OCR）":
        uploaded = st.file_uploader("上传筹码截图（同花顺PC端）", type=["png", "jpg", "jpeg"])
        if st.button("解析") and uploaded is not None:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(uploaded.read())
                tmp_path = tmp.name
            analysis = parse_chip_screenshot(tmp_path, code=str(code))
            render_chip_panel(str(code), float(current_price), analysis)
        elif uploaded is None:
            st.warning("请上传同花顺筹码分布截图（PC端）")
    else:
        if st.button("获取筹码数据"):
            from engine.agent.chip_fetcher import ChipDataUnavailable, fetch_chip_summary
            try:
                summary = fetch_chip_summary(str(code))
                from engine.agent.chip_analysis import analyze_chip
                analysis = analyze_chip(str(code), float(current_price), summary)
                render_chip_panel(str(code), float(current_price), analysis, summary)
            except ChipDataUnavailable as exc:
                st.error(f"数据获取失败：{exc}")
