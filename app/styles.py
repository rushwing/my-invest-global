"""REQ-013: Global CSS design tokens injected via st.markdown."""
from __future__ import annotations

import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
  --bg:           #0E1117;
  --surface:      #1C1C2E;
  --surface-alt:  #161623;
  --accent:       #4F8EF7;
  --bull:         #00C47A;
  --neutral:      #F5A623;
  --bear:         #E84040;
  --stop:         #FF0000;
  --text-primary: #E8EAED;
  --text-muted:   #9AA0AC;
  --border:       #2A2A3E;
}

body, .stApp {
  background-color: var(--bg);
  font-family: 'Noto Sans SC', sans-serif;
  color: var(--text-primary);
}

.mono-num { font-family: 'JetBrains Mono', monospace; font-feature-settings: "tnum"; }

.kpi-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px;
}
.signal-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}
.tag { display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 11px; }

.tier-badge { padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.tier-badge.tier-1 { background: #FF7A1A; color: #fff; }
.tier-badge.tier-2 { background: #F5A623; color: #000; }
.tier-badge.tier-3 { background: #9AA0AC; color: #000; }
.tier-badge.tier-4 { background: #4F8EF7; color: #fff; }
.rationale { font-size: 11px; color: #9AA0AC; margin-left: 6px; }

.flow-strip { margin-top: 6px; }
.flow-cell { display: inline-block; width: 8px; height: 20px; margin: 0 1px; border-radius: 2px; }
.flow-cell.pos { background: #00C47A; }
.flow-cell.neg { background: #E84040; }
.flow-cell.neutral { background: #888; }

[data-testid="stSidebar"] { background-color: var(--surface); }
[data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace; }
div[data-testid="stVerticalBlock"] > div { padding-top: 0; }
</style>
"""


def inject_global_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
