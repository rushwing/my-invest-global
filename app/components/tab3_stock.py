"""REQ-018: Tab 3 个股深度分析."""
from __future__ import annotations

from datetime import timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

TIER_COLORS: dict[int, str] = {
    1: "#FF7A1A",
    2: "#F5A623",
    3: "#9AA0AC",
    4: "#4F8EF7",
}

_DEFAULT_CODES = ["300308", "688041", "002230", "600745", "688256"]


def get_preselect_code() -> str | None:
    return st.session_state.get("tab3_code")


def filter_by_date_range(df: pd.DataFrame, range_str: str) -> pd.DataFrame:
    days_map = {"1M": 31, "3M": 92, "6M": 183, "1Y": 366}
    days = days_map.get(range_str, 183)
    max_date = pd.to_datetime(df["date"]).max()
    cutoff = (max_date - timedelta(days=days)).strftime("%Y-%m-%d")
    return df[df["date"].astype(str) >= cutoff].copy()


def render_fundamental_card(
    ticker: str,
    ohlcv_df: pd.DataFrame,
    scarcity_row: pd.Series | None,
    name_fallback: str | None = None,
) -> None:
    rank_val = None
    name = name_fallback or ticker
    if scarcity_row is not None:
        r = scarcity_row.get("rank")
        if r is not None and pd.notna(r):
            rank_val = int(r)
        n = scarcity_row.get("name")
        if n and pd.notna(n):
            name = str(n)

    tier_color = TIER_COLORS.get(rank_val, "#9AA0AC")
    tier_label = f"Tier-{rank_val}" if rank_val else "Tier-?"

    current_price = float(ohlcv_df["close"].iloc[-1]) if not ohlcv_df.empty else None
    price_html = (
        f'<div class="mono-num" style="font-size:22px;font-weight:700;">'
        f'¥{current_price:,.2f}</div>'
        if current_price is not None else
        '<div style="font-size:22px;color:#9AA0AC;">—</div>'
    )

    upside_html = ""
    if scarcity_row is not None and current_price is not None:
        tp = scarcity_row.get("target_price")
        if tp is not None and pd.notna(tp):
            target = float(tp)
            upside = (target - current_price) / current_price
            up_color = "#00C47A" if upside >= 0 else "#E84040"
            sign = "+" if upside >= 0 else ""
            upside_html = (
                f'<div style="font-size:12px;color:#9AA0AC;margin-top:4px;">'
                f'目标价 <span class="mono-num">¥{target:,.2f}</span>'
                f'&nbsp;<span style="color:{up_color};">{sign}{upside:.1%}</span></div>'
            )

    metrics: list[str] = []
    if scarcity_row is not None:
        for key, fmt in [("market_cap", "市值 {:.0f}亿"), ("pe", "PE {:.1f}x"), ("beta", "Beta {:.2f}")]:
            v = scarcity_row.get(key)
            if v is not None and pd.notna(v):
                val = float(v) / 1e8 if key == "market_cap" else float(v)
                metrics.append(fmt.format(val))
    if not ohlcv_df.empty and len(ohlcv_df) >= 5:
        avg_vol = ohlcv_df["volume"].tail(20).mean()
        if avg_vol >= 1e4:
            metrics.append(f"日均量 {avg_vol / 1e4:.1f}万手")
        else:
            metrics.append(f"日均量 {avg_vol:.0f}手")
    metrics_html = (
        '<div style="font-size:11px;color:#9AA0AC;margin-top:6px;">'
        + "&nbsp;·&nbsp;".join(metrics)
        + "</div>"
    ) if metrics else ""

    rating_html = ""
    if scarcity_row is not None:
        rating = scarcity_row.get("rating")
        if rating is not None and pd.notna(rating) and str(rating):
            rating_html = (
                f'<div style="font-size:11px;color:#9AA0AC;margin-top:4px;">'
                f'机构评级&nbsp;<span style="color:#E8EAED;">{rating}</span></div>'
            )

    tier_cls = f"tier-{rank_val}" if rank_val else ""
    st.markdown(
        f'<div style="border:1px solid #2A2A3E;border-radius:8px;'
        f'background:#1C1C2E;padding:16px;margin-bottom:12px;">'
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
        f'<span class="tier-badge {tier_cls}" style="background:{tier_color};color:#fff;">'
        f'{tier_label}</span>'
        f'<span style="font-size:16px;font-weight:600;">{name}</span>'
        f'<span style="font-size:12px;color:#9AA0AC;">{ticker}</span>'
        f'</div>'
        f'{price_html}{upside_html}{metrics_html}{rating_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def build_stock_chart(df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        row_heights=[0.45, 0.15, 0.25, 0.15],
        vertical_spacing=0.02,
    )

    # Row 1 — Candlestick + BB + MA65
    fig.add_trace(go.Candlestick(
        x=df["date"], open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name="K线",
        increasing_line_color="#00C47A", decreasing_line_color="#E84040",
    ), row=1, col=1)

    if "bb_upper" in df.columns and df["bb_upper"].notna().any():
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["bb_upper"],
            line=dict(width=0), showlegend=False, name="BB上轨",
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["bb_lower"],
            fill="tonexty", fillcolor="rgba(79,142,247,0.10)",
            line=dict(width=0), showlegend=False, name="BB下轨",
        ), row=1, col=1)

    if "ma65" in df.columns and df["ma65"].notna().any():
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["ma65"],
            line=dict(color="#F5A623", width=1.5), name="MA13W",
        ), row=1, col=1)

    # Row 2 — Volume
    vol_colors = [
        "#00C47A" if c >= o else "#E84040"
        for c, o in zip(df["close"], df["open"])
    ]
    fig.add_trace(go.Bar(
        x=df["date"], y=df["volume"],
        marker_color=vol_colors, showlegend=False, name="成交量",
    ), row=2, col=1)

    # Row 3 — MACD
    if "macd_hist" in df.columns and df["macd_hist"].notna().any():
        hist_vals = df["macd_hist"].fillna(0)
        hist_colors = ["#00C47A" if v >= 0 else "#E84040" for v in hist_vals]
        fig.add_trace(go.Bar(
            x=df["date"], y=hist_vals,
            marker_color=hist_colors, showlegend=False, name="MACD柱",
        ), row=3, col=1)

    if "macd" in df.columns and df["macd"].notna().any():
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["macd"],
            line=dict(color="#4F8EF7", width=1.2), name="MACD",
        ), row=3, col=1)
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["macd_signal"],
            line=dict(color="#F5A623", width=1.2), name="Signal",
        ), row=3, col=1)

        macd_valid = df.dropna(subset=["macd", "macd_signal"])
        golden = macd_valid[
            (macd_valid["macd"] > macd_valid["macd_signal"]) &
            (macd_valid["macd"].shift(1) <= macd_valid["macd_signal"].shift(1))
        ]
        death = macd_valid[
            (macd_valid["macd"] < macd_valid["macd_signal"]) &
            (macd_valid["macd"].shift(1) >= macd_valid["macd_signal"].shift(1))
        ]
        fig.add_trace(go.Scatter(
            x=golden["date"], y=golden["macd"],
            mode="markers",
            marker=dict(color="#00C47A", size=8, symbol="circle"),
            name="金叉",
        ), row=3, col=1)
        fig.add_trace(go.Scatter(
            x=death["date"], y=death["macd"],
            mode="markers",
            marker=dict(color="#E84040", size=8, symbol="circle"),
            name="死叉",
        ), row=3, col=1)

    # Row 4 — RSI
    if "rsi14" in df.columns and df["rsi14"].notna().any():
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["rsi14"],
            line=dict(color="#4F8EF7", width=1.5), name="RSI(14)",
        ), row=4, col=1)
        fig.add_hrect(y0=70, y1=100, fillcolor="rgba(232,64,64,0.08)",   line_width=0, row=4, col=1)
        fig.add_hrect(y0=0,  y1=30,  fillcolor="rgba(0,196,122,0.08)",   line_width=0, row=4, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="#E84040", line_width=0.8, row=4, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#00C47A", line_width=0.8, row=4, col=1)

    fig.update_layout(
        plot_bgcolor="#0E1117",
        paper_bgcolor="#0E1117",
        font=dict(color="#E8EAED", family="JetBrains Mono"),
        xaxis_rangeslider_visible=False,
        height=700,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    for i in range(1, 5):
        fig.update_xaxes(showgrid=False, row=i, col=1)
        fig.update_yaxes(showgrid=True, gridcolor="#2A2A3E", row=i, col=1)

    return fig


def render_news_timeline(news_df: pd.DataFrame) -> None:
    for _, row in news_df.head(8).iterrows():
        sentiment_color = {
            "positive": "#00C47A", "negative": "#E84040",
        }.get(str(row.get("sentiment", "")), "#9AA0AC")
        st.markdown(
            f"""<div style="display:flex;gap:12px;padding:8px 0;border-bottom:1px solid #2A2A3E;">
              <div style="width:8px;height:8px;border-radius:50%;background:{sentiment_color};
                          flex-shrink:0;margin-top:6px;"></div>
              <div>
                <div style="font-size:13px;">{row.get("title","")}</div>
                <div style="font-size:11px;color:#9AA0AC;margin-top:4px;">
                  {row.get("source","")} · {str(row.get("published_at",""))[:10]}
                  <span style="background:#1C1C2E;padding:2px 6px;border-radius:4px;margin-left:8px;">
                    相关度 {float(row.get("relevance_score", 0)):.0%}
                  </span>
                </div>
              </div>
            </div>""",
            unsafe_allow_html=True,
        )


def render_tab3() -> None:
    from app.data_loader import (
        compute_indicators,
        load_latest_holdings,
        load_news_for_ticker,
        load_ohlcv,
        load_scarcity_matrix,
    )

    preselect = st.session_state.pop("tab3_code", None)

    scarcity_df = load_scarcity_matrix()
    holdings_df = load_latest_holdings()

    # Build code→name map from holdings YAML as fallback for scarcity_matrix
    name_map: dict[str, str] = {}
    if holdings_df is not None and not holdings_df.empty:
        for _, row in holdings_df.iterrows():
            c = str(row.get("code", ""))
            n = str(row.get("name", ""))
            if c and n and n != "nan":
                name_map[c] = n

    if not scarcity_df.empty:
        available = list(scarcity_df["code"].unique())
    elif name_map:
        available = list(name_map.keys())
    else:
        available = _DEFAULT_CODES

    default_idx = 0
    if preselect and preselect in available:
        default_idx = available.index(preselect)

    col_sel, col_range = st.columns([3, 1])
    with col_sel:
        ticker = st.selectbox("选择股票", options=available, index=default_idx, key="tab3_ticker")
    with col_range:
        date_range = st.selectbox("日期范围", ["1M", "3M", "6M", "1Y"], index=2, key="tab3_range")

    scarcity_row = None
    if not scarcity_df.empty and ticker in scarcity_df["code"].values:
        scarcity_row = scarcity_df[scarcity_df["code"] == ticker].iloc[0]

    ohlcv_df = load_ohlcv(ticker, days=400)
    if ohlcv_df.empty:
        st.info(f"暂无 {ticker} 行情数据")
        return

    # Pass holdings name as fallback when scarcity_matrix has no entry
    name_fallback = name_map.get(ticker)
    render_fundamental_card(ticker, ohlcv_df, scarcity_row, name_fallback=name_fallback)

    df = compute_indicators(ohlcv_df)
    df_view = filter_by_date_range(df, date_range)

    st.plotly_chart(build_stock_chart(df_view), use_container_width=True)

    # Indicator strip
    if not df_view.empty:
        last = df_view.iloc[-1]
        cols = st.columns(4)
        for col, (label, key) in zip(cols, [
            ("MA13W", "ma65"), ("MACD", "macd"), ("Signal", "macd_signal"), ("RSI(14)", "rsi14"),
        ]):
            val = last.get(key)
            col.metric(label, f"{val:.2f}" if pd.notna(val) else "—")

    # News timeline
    news_df = load_news_for_ticker(ticker, limit=8)
    if not news_df.empty:
        st.subheader("相关新闻")
        render_news_timeline(news_df)
