"""REQ-023: Tab 1 持仓总览 + Holdings CRUD."""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

_EDITOR_COLS = ["code", "name", "category", "cost_price", "current_price", "quantity"]


def _enrich(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in _EDITOR_COLS:
        if col not in df.columns:
            df[col] = None
    df["cost_price"]    = pd.to_numeric(df["cost_price"],    errors="coerce").fillna(0.0)
    df["current_price"] = pd.to_numeric(df["current_price"], errors="coerce").fillna(0.0)
    df["quantity"]      = pd.to_numeric(df["quantity"],      errors="coerce").fillna(0).astype(int)
    df["market_value"]  = df["current_price"] * df["quantity"]
    mask = df["cost_price"] > 0
    df["pnl_pct"] = 0.0
    df.loc[mask, "pnl_pct"] = (
        (df.loc[mask, "current_price"] - df.loc[mask, "cost_price"])
        / df.loc[mask, "cost_price"] * 100
    )
    return df


def _normalize_codes(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure code column is string, A-share 6-digit codes are zero-padded."""
    if "code" not in df.columns:
        return df
    df = df.copy()
    df["code"] = (
        df["code"].astype(str).str.strip()
        .apply(lambda c: c.zfill(6) if c.isdigit() and len(c) <= 6 else c)
    )
    return df


def _init_state() -> None:
    if "t1_holdings_full" not in st.session_state:
        from app.data_loader import load_latest_holdings
        raw = load_latest_holdings()
        df = (
            _normalize_codes(raw.reindex(columns=_EDITOR_COLS).copy())
            if raw is not None and not raw.empty
            else pd.DataFrame(columns=_EDITOR_COLS)
        )
        st.session_state["t1_holdings_full"] = df
        st.session_state["t1_holdings_saved"] = df.copy()


def _pbar_html(pct: float, target: float, color: str) -> str:
    c = min(max(pct, 0.0), 100.0)
    t = min(max(target, 0.0), 100.0)
    return (
        f'<div style="margin-top:8px;position:relative;">'
        f'<div style="height:4px;background:#2A2A3E;border-radius:2px;overflow:hidden;">'
        f'<div style="width:{c:.1f}%;height:4px;background:{color};border-radius:2px;"></div>'
        f'</div>'
        f'<div style="position:absolute;top:-3px;left:{t:.1f}%;width:2px;height:10px;'
        f'background:#E8EAED;border-radius:1px;margin-left:-1px;"></div>'
        f'</div>'
    )


def _render_kpi_row(df: pd.DataFrame, metrics: dict) -> None:
    total_mv       = metrics["total_mv"]
    elastic_pct    = metrics["elastic_pct"]
    elastic_target = metrics["elastic_target"]
    white_pct      = metrics["white_pct"]
    white_target   = 100.0 - elastic_target

    total_cost = float((df["cost_price"] * df["quantity"]).sum()) if not df.empty else 0.0
    unrealized = total_mv - total_cost
    unr_pct    = unrealized / total_cost * 100 if total_cost > 0 else 0.0
    pnl_color  = "#00C47A" if unrealized >= 0 else "#E84040"
    pnl_sign   = "+" if unrealized >= 0 else ""

    e_dev   = elastic_pct - elastic_target
    e_color = "#00C47A" if abs(e_dev) <= 5 else ("#F5A623" if abs(e_dev) <= 10 else "#E84040")
    e_sign  = "+" if e_dev >= 0 else ""

    w_dev   = white_pct - white_target
    w_color = "#4F8EF7" if abs(w_dev) <= 5 else ("#F5A623" if abs(w_dev) <= 10 else "#E84040")
    w_sign  = "+" if w_dev >= 0 else ""

    CARD  = "background:#1C1C2E;border:1px solid #2A2A3E;border-radius:8px;padding:16px 18px;"
    LABEL = "font-size:10px;color:#9AA0AC;letter-spacing:0.06em;margin-bottom:6px;"
    VAL   = "font-size:20px;font-weight:600;color:#E8EAED;font-family:JetBrains Mono,monospace;"
    SUB   = "font-size:11px;font-family:JetBrains Mono,monospace;margin-top:3px;"
    FLEX  = "display:flex;align-items:baseline;gap:8px;"

    c1, c2, c3 = st.columns(3)
    c1.markdown(
        f'<div style="{CARD}"><div style="{LABEL}">总市值</div>'
        f'<div style="{VAL}">¥{total_mv:,.0f}</div>'
        f'<div style="{SUB}color:{pnl_color};">{pnl_sign}¥{unrealized:,.0f}'
        f'&nbsp;&nbsp;({pnl_sign}{unr_pct:.1f}%)</div></div>',
        unsafe_allow_html=True,
    )
    c2.markdown(
        f'<div style="{CARD}"><div style="{LABEL}">弹性仓位（目标 {elastic_target}%）</div>'
        f'<div style="{FLEX}"><div style="{VAL}">{elastic_pct:.1f}%</div>'
        f'<div style="{SUB}color:{e_color};">{e_sign}{e_dev:.1f}%</div></div>'
        + _pbar_html(elastic_pct, elastic_target, e_color)
        + '</div>',
        unsafe_allow_html=True,
    )
    c3.markdown(
        f'<div style="{CARD}"><div style="{LABEL}">白马仓位（目标 {white_target:.0f}%）</div>'
        f'<div style="{FLEX}"><div style="{VAL}">{white_pct:.1f}%</div>'
        f'<div style="{SUB}color:{w_color};">{w_sign}{w_dev:.1f}%</div></div>'
        + _pbar_html(white_pct, white_target, w_color)
        + '</div>',
        unsafe_allow_html=True,
    )


def _render_charts(df: pd.DataFrame, metrics: dict) -> None:
    import plotly.graph_objects as go

    col_donut, col_map = st.columns([2, 3])

    with col_donut:
        cat_mv = (
            df.groupby("category")["market_value"].sum()
            .reset_index()
            .sort_values("market_value", ascending=False)
        )
        cat_colors = {"白马股": "#4F8EF7", "弹性股": "#00C47A", "自选": "#F5A623"}
        fig = go.Figure(go.Pie(
            labels=cat_mv["category"],
            values=cat_mv["market_value"],
            hole=0.62,
            marker=dict(
                colors=[cat_colors.get(c, "#9AA0AC") for c in cat_mv["category"]],
                line=dict(color="#0E1117", width=2),
            ),
            textinfo="label+percent",
            textfont=dict(size=11, color="#E8EAED"),
            hovertemplate="%{label}<br>¥%{value:,.0f} (%{percent})<extra></extra>",
        ))
        fig.update_layout(
            showlegend=False,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            height=200,
            annotations=[dict(
                text=f"¥{metrics['total_mv']:,.0f}",
                x=0.5, y=0.5,
                font=dict(size=11, color="#E8EAED", family="JetBrains Mono"),
                showarrow=False,
            )],
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_map:
        valid = df[df["market_value"] > 0].copy()
        if valid.empty:
            st.caption("暂无市值数据")
            return
        valid["label"] = valid.apply(
            lambda r: f"{r.get('name') or r['code']}<br>{r['code']}", axis=1
        )
        valid["clipped_pnl"] = valid["pnl_pct"].clip(-20, 20)
        fig2 = go.Figure(go.Treemap(
            labels=valid["label"],
            values=valid["market_value"],
            parents=[""] * len(valid),
            customdata=valid[["code", "pnl_pct", "market_value"]].values,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "市值: ¥%{customdata[2]:,.0f}<br>"
                "浮盈: %{customdata[1]:.2f}%<extra></extra>"
            ),
            marker=dict(
                colors=valid["clipped_pnl"],
                colorscale=[[0.0, "#3D1515"], [0.5, "#1C1C2E"], [1.0, "#0D3320"]],
                cmid=0, cmin=-20, cmax=20, showscale=False,
            ),
            textfont=dict(color="#E8EAED", size=11),
        ))
        fig2.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            height=200,
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})


def _df_changed(a: pd.DataFrame, b: pd.DataFrame) -> bool:
    if a is None or b is None:
        return True
    if a.shape != b.shape:
        return True
    try:
        cols = [c for c in _EDITOR_COLS if c in a.columns and c in b.columns]
        return not (
            a[cols].reset_index(drop=True).fillna("")
            .equals(b[cols].reset_index(drop=True).fillna(""))
        )
    except Exception:
        return True


def _render_editor_section() -> None:
    from app.sidebar import save_holdings

    full: pd.DataFrame = st.session_state["t1_holdings_full"]

    # ── Section header: filter pills + action buttons ─────────────────────────
    col_filter, col_btns = st.columns([6, 3])

    with col_filter:
        st.markdown(
            '<span style="font-size:13px;font-weight:600;color:#E8EAED;'
            'display:inline-block;margin-bottom:6px;">自选/持仓</span>',
            unsafe_allow_html=True,
        )
        cat_filter = st.radio(
            "分类", ["全部", "白马股", "弹性股", "自选"],
            horizontal=True, label_visibility="collapsed", key="t1_cat_filter",
        )

    with col_btns:
        b_csv, b_save = st.columns(2)
        if b_csv.button("↑ 导入 CSV", key="_t1_csv_btn", use_container_width=True):
            st.session_state["_t1_show_csv"] = not st.session_state.get("_t1_show_csv", False)

        saved = st.session_state.get("t1_holdings_saved")
        dirty = _df_changed(full, saved)
        lbl = "● 保存" if dirty else "保存快照"
        if b_save.button(
            lbl, type="primary" if dirty else "secondary",
            key="_t1_save_btn", use_container_width=True,
        ):
            save_holdings(full[_EDITOR_COLS].copy(), date.today())
            st.cache_data.clear()
            st.session_state["t1_holdings_saved"] = full.copy()
            st.success("持仓已保存")
            st.rerun()

    # ── CSV import panel ───────────────────────────────────────────────────────
    if st.session_state.get("_t1_show_csv"):
        uploaded = st.file_uploader(
            "CSV（列：code / name / category / cost_price / current_price / quantity）",
            type=["csv"], key="_t1_csv_up",
        )
        if uploaded is not None:
            try:
                csv_df = pd.read_csv(uploaded, dtype={"code": str}).reindex(columns=_EDITOR_COLS)
                if "code" in csv_df.columns:
                    csv_df["code"] = (
                        csv_df["code"].astype(str).str.strip()
                        .apply(lambda c: c.zfill(6) if c.isdigit() and len(c) <= 6 else c)
                    )
                merged = (
                    pd.concat([full, csv_df], ignore_index=True)
                    .drop_duplicates(subset=["code"], keep="last")
                    .reset_index(drop=True)
                )
                st.session_state["t1_holdings_full"] = merged
                st.session_state["_t1_show_csv"] = False
                st.success(f"已导入 {len(csv_df)} 行")
                st.rerun()
            except Exception as exc:
                st.error(f"解析失败: {exc}")

    # ── Build display df ───────────────────────────────────────────────────────
    if cat_filter == "全部":
        display_df = full[_EDITOR_COLS].copy().reset_index(drop=True)
    else:
        display_df = (
            full[full["category"] == cat_filter][_EDITOR_COLS]
            .copy().reset_index(drop=True)
        )

    # Append read-only computed columns
    cp = pd.to_numeric(display_df["current_price"], errors="coerce").fillna(0.0)
    cs = pd.to_numeric(display_df["cost_price"],    errors="coerce").fillna(0.0)
    qt = pd.to_numeric(display_df["quantity"],      errors="coerce").fillna(0).astype(int)
    display_df["market_value"] = cp * qt
    display_df["pnl_pct"] = 0.0
    mask = cs > 0
    display_df.loc[mask, "pnl_pct"] = (cp[mask] - cs[mask]) / cs[mask] * 100

    # ── Data editor ────────────────────────────────────────────────────────────
    edited = st.data_editor(
        display_df,
        column_config={
            "code":          st.column_config.TextColumn("代码"),
            "name":          st.column_config.TextColumn("名称"),
            "category":      st.column_config.SelectboxColumn(
                                 "类别", options=["白马股", "弹性股", "自选"]),
            "cost_price":    st.column_config.NumberColumn("成本价", format="%.2f"),
            "current_price": st.column_config.NumberColumn("现价", format="%.2f"),
            "quantity":      st.column_config.NumberColumn("数量", step=1),
            "market_value":  st.column_config.NumberColumn("市值", format="%.0f", disabled=True),
            "pnl_pct":       st.column_config.NumberColumn("浮盈%", format="%.2f%%", disabled=True),
        },
        num_rows="dynamic",
        use_container_width=True,
        key=f"t1_editor_{cat_filter}",
        hide_index=True,
    )

    # Sync edits back into full df (base columns only)
    edited_base = edited[_EDITOR_COLS].copy()
    if cat_filter == "全部":
        st.session_state["t1_holdings_full"] = edited_base.reset_index(drop=True)
    else:
        other = full[full["category"] != cat_filter][_EDITOR_COLS].copy()
        st.session_state["t1_holdings_full"] = (
            pd.concat([other, edited_base], ignore_index=True)
        )

    # ── Tab 3 navigation shortcut ──────────────────────────────────────────────
    codes = [
        str(c) for c in st.session_state["t1_holdings_full"]["code"].dropna()
        if str(c).strip()
    ]
    if codes:
        nav1, nav2, _ = st.columns([2, 1, 4])
        nav_code = nav1.selectbox(
            "跳转至个股分析", ["—"] + codes,
            key="_t1_nav_code", label_visibility="visible",
        )
        if nav2.button("→ 分析", key="_t1_nav_go") and nav_code != "—":
            st.session_state["tab3_code"] = nav_code
            st.info(f"已预选 {nav_code}，请切换至「个股深度分析」标签页查看。")


def render_tab1() -> None:
    from app.data_loader import compute_portfolio_metrics, load_macro_state

    macro = load_macro_state()
    state = macro.get("state", "yellow")

    _init_state()

    full_df = st.session_state["t1_holdings_full"]
    df = _enrich(full_df)

    if df.empty:
        metrics: dict = {
            "total_mv": 0.0, "elastic_pct": 0.0, "white_pct": 0.0,
            "elastic_target": 33, "white_mv": 0.0, "elastic_mv": 0.0, "df": df,
        }
    else:
        metrics = compute_portfolio_metrics(df, state)

    _render_kpi_row(df, metrics)

    if not df.empty and metrics["total_mv"] > 0:
        _render_charts(df, metrics)

    st.markdown('<hr style="border-color:#2A2A3E;margin:8px 0 12px;">', unsafe_allow_html=True)

    _render_editor_section()
