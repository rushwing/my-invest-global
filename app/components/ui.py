"""REQ-013: Reusable UI primitives."""
from __future__ import annotations

import streamlit as st


def kpi_card(label: str, value: str, delta: str | None = None, delta_color: str = "bull") -> None:
    color = {"bull": "#00C47A", "bear": "#E84040", "neutral": "#F5A623"}.get(delta_color, "#9AA0AC")
    delta_html = (
        f'<div style="font-size:12px;color:{color};margin-top:4px;">{delta}</div>'
        if delta else ""
    )
    st.markdown(
        f"""<div class="kpi-card">
          <div style="font-size:11px;color:#9AA0AC;">{label}</div>
          <div class="mono-num" style="font-size:20px;margin-top:4px;">{value}</div>
          {delta_html}
        </div>""",
        unsafe_allow_html=True,
    )


def signal_badge(signal_key: str) -> str:
    colors = {
        "strong_add": "#00C47A", "hold_add": "#00C47A",
        "hold": "#F5A623",
        "reduce": "#E84040", "stop_loss": "#E84040",
        "take_profit_alert": "#FF7A1A",
    }
    color = colors.get(signal_key, "#9AA0AC")
    return f'<span class="signal-badge" style="background:{color}20;color:{color};">{signal_key}</span>'  # noqa: E501


def tag(text: str, color: str = "#4F8EF7") -> str:
    return f'<span class="tag" style="background:{color}20;color:{color};">{text}</span>'


def mono_num(value: str, prefix: str = "", suffix: str = "") -> str:
    return f'<span class="mono-num">{prefix}{value}{suffix}</span>'
