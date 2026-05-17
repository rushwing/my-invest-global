# Design Handoff: Streamlit Dashboard (4 Tabs)

> **Target codebase**: `my-invest-global` · Streamlit 1.32+ · Plotly · Python 3.12
> **Spec source**: `docs/adr/ADR-005-frontend-dashboard.md` · `methodology.md` · `engine/schemas.py`
> **Suggested install location**: drop this folder at `docs/design/dashboard/` in the project repo.

---

## 1. Overview

This bundle is the **visual design reference** for the 4-tab personal stock advisor dashboard described in `ADR-005-frontend-dashboard.md`. It contains:

- An HTML/React clickable canvas with 5 artboards (design system + 4 tabs)
- All design tokens, type scale, and component specs the Streamlit implementation should match
- Realistic content driven by the project's actual methodology and schemas

### About these files (read first)

The `.html` + `.jsx` files in this folder are **design mockups, not production code**. They are React prototypes using inline Babel — meant to communicate intent, not to be lifted into the codebase.

**Your job**: re-implement these designs in the project's chosen environment — **Streamlit + Plotly** (per ADR-005). Use Streamlit's `st.dataframe`, `st.plotly_chart`, custom CSS via `st.markdown(unsafe_allow_html=True)`, and `streamlit.components.v1.html` for the more complex layouts. Where Streamlit's defaults clash with the look defined here, **override via custom CSS**; do not water down the visual spec to fit Streamlit's defaults.

---

## 2. Fidelity: **High-fidelity (hifi)**

Pixel-perfect mockups with final colors, typography, spacing, dimensions, and interaction states. Match these exactly. Specific guidance:

- **Tight 12px card padding** is intentional — do not loosen to Streamlit's default 1rem.
- **JetBrains Mono with tabular-nums** for every numeric value — required for column alignment in tables.
- **Status colors are semantic** — never reuse green for "click me" or red for "danger zone" backgrounds.

---

## 3. How to view the mockups

Open `index.html` in any modern browser. You'll see a dark canvas with 5 artboards:

| # | Artboard | What it shows |
|---|----------|---------------|
| 1 | Design System Spec | All tokens (colors, type, spacing, radii) + component library |
| 2 | Tab 1 持仓总览 | Allocation donut, KPIs, holdings treemap heatmap, deviation table |
| 3 | Tab 2 每日策略简报 | Macro banner, LLM brief (3 collapsibles), signal score table, US leading chart |
| 4 | Tab 3 个股深度分析 | 4-pane K-line/MACD/RSI chart, fundamental card, news timeline |
| 5 | Tab 4 信号仪表盘 | 3-state macro traffic light, Big-4 capex, scarcity matrix, position gauges, 30-day history |

Pan with click-drag, zoom with scroll, double-click any artboard for fullscreen focus, ←/→ to step between.

---

## 4. Design Tokens

### 4.1 Colors

```css
/* Surfaces */
--bg:           #0E1117;   /* Streamlit default dark page bg */
--surface:      #1C1C2E;   /* card bg */
--surface-alt:  #161623;   /* nested bg (table headers, inner panels) */
--border:       rgba(255,255,255,0.06);
--border-strong:rgba(255,255,255,0.12);

/* Text */
--text:         #E8EAED;
--text-muted:   #9AA0AC;
--text-dim:     #5C616E;

/* Brand */
--accent:       #4F8EF7;   /* links, active tab underline, MA13W */

/* Status / signals */
--bull:         #00C47A;   /* bullish · 增长 · positive · strong_add */
--neutral:      #F5A623;   /* neutral · 平稳 · warning */
--bear:         #E84040;   /* bearish · 收缩 · reduce · negative */
--stop:         #FF0000;   /* hard stop_loss (pure red, distinct from --bear) */

/* Signal action badges (engine/schemas.py StockSignal.action_code) */
--sig-strong-add: #00C47A
--sig-hold-add:   #4F8EF7
--sig-hold:       #888888
--sig-reduce:     #E84040
--sig-stop-loss:  #FF0000

/* Scarcity tier (methodology.md §2.1) */
--tier-1: #FF7A1A   /* 极高 · orange */
--tier-2: #F5A623   /* 高 · amber */
--tier-3: #9AA0AC   /* 中 · grey */
--tier-4: #4F8EF7   /* 低 · blue */

/* PnL heat gradient */
/* linear-gradient(90deg, var(--bear) 0%, #2a2a3a 50%, var(--bull) 100%) */
/* Maps -20% → 0 → +20% */
```

### 4.2 Typography

| Token | Family | Size / line-height | Weight | Use |
|---|---|---|---|---|
| Display | Noto Sans SC | 28/32 | 600 | Page titles (持仓总览, 每日策略简报) |
| H1 | Noto Sans SC | 18/24 | 600 | Section titles inside cards |
| H2 | Noto Sans SC | 15/20 | 600 | Card titles |
| Body | Noto Sans SC | 13/18 | 400 | Default text |
| Label | Noto Sans SC | 11/14 | 500 | Field labels above values |
| Mono Big | JetBrains Mono | 22-26/28 | 600 | Hero KPIs, PnL%, large prices |
| Mono | JetBrains Mono | 13/18 | 500 | All numeric cells, codes |
| Mono Small | JetBrains Mono | 10-11/14 | 400-500 | Timestamps, axis ticks |

**Critical CSS rules for ALL numeric content** (KPIs, table cells, PnL%, percentages, codes):
```css
font-family: 'JetBrains Mono', ui-monospace, monospace;
font-variant-numeric: tabular-nums;
```

Streamlit defaults to system fonts — inject both fonts via `<head>`:

```python
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)
```

### 4.3 Spacing & radii

- Spacing scale: 4, 8, 12, 16, 20, 28 px
- Card padding default: **12px** (some headers use 16px)
- Card gap (between cards): **12px**
- Page padding: **28px**
- Radii: badge 4, tag 4-6, card 8, modal 12

### 4.4 Shadows
None on the page itself. The glowing macro traffic-light circle uses `box-shadow: 0 0 22px <color>88` only when active.

---

## 5. Component Specs

### 5.1 Tab bar (top of every page)
- Row of pills with `01` `02` `03` `04` number prefixes (JetBrains Mono, dim) + Chinese label
- Active: text bold 600, color `--text`, **2px bottom border `--accent`**, subtle 6% blue tint background
- Inactive: text 400, color `--text-muted`, transparent border
- Right side: live status chip (green dot + "LIVE · A股盘中" or "LLM · GPT-4 ready") + cache timestamp

### 5.2 KPI Card
```
┌─ 12px padding ─────────┐
│ label (11px muted)     │
│ VALUE  (22-26px mono   │
│        green/red/text) │
│ subtext (11px dim)     │
└────────────────────────┘
```
- Single border `--border`
- When the KPI exceeds an alert threshold (e.g. `最大单只占比 > 8%`), border switches to `--bear` and a `<Tag tone="bear">超阈值</Tag>` floats top-right
- Progress-bar variant: 4px tall track with a fill bar + **1.5px white tick** marking the target value

### 5.3 Signal Badge (action_code)
- Padding 4×8 (sm: 2×6)
- Background `<color>22` (13% alpha), border `<color>55` (33% alpha), text in solid color
- 5px solid dot prefix + Chinese label
- The 5 action_codes from `engine/schemas.py` map to:
  - `strong_add` → 强力加仓 / green
  - `hold_add`   → 持有加仓 / blue
  - `hold`       → 持有观望 / grey
  - `reduce`     → 减仓     / red
  - `stop_loss`  → 止损     / pure red

### 5.4 Tag (category / sector / status)
- Padding 3×8, radius 4, 11px font
- Default: blue tint (`#4F8EF733` bg, accent text)
- `muted` variant: grey tint
- Tone variants: bull/bear/neutral apply same alpha pattern as badges

### 5.5 Table
- Header row: surface-alt bg, 10px uppercase JetBrains Mono labels with 0.06em letter-spacing, muted color
- Body rows: 13px text, 11px column padding, 1px border-top between rows
- Numeric columns right-aligned, JetBrains Mono
- Row highlight: yellow tint `<neutral>14` (8%) for warning, red tint `<bear>1A` (10%) for severe
- A `stop_loss` row gets `<bear>12` (7%) full-row tint AND the stock name turns red

### 5.6 Heat cell (treemap)
- Background: PnL-gradient interpolation, with 15-70% alpha
- Border: matching bull/bear color at 55% alpha
- Padding 12×14 (tiny variants 6×8)
- Stock name in white, code+sector dim white, PnL% large white mono
- Layout: name+code top, PnL% bottom, market value sub-line if cell ≥ 110×70

### 5.7 Scarcity tier chip (Tab 4 matrix)
- Padding 7×9, radius 4, 1px border with tier color
- Score in top-right corner (color = `chipColor(score)` based on the 70/50 thresholds)
- Owned marker: blue `◉` prefix
- Bottom mini score bar (2px tall)

### 5.8 Alert box (Tab 2 risk warnings)
- Layout: 3px left border (status color) + tint background (8-10% alpha) + 1px border (40% alpha)
- 20px icon column + title + body
- Three variants: danger (止损, red), warn (止盈, yellow), info (观察, blue)

### 5.9 Donut chart (allocation)
- 200×200 SVG, R=80, stroke-width=22
- Outer dashed ring at R+16 = target indicator
- 1.5px white tick at the exact target percentage
- Center: 总市值 label + ¥XX.X 万元 (white mono)
- Ring color: accent if deviation < 5%, neutral if 5-10%, bear if > 10%

### 5.10 Semi-circular gauge (Tab 4 position)
- 200×140 viewBox, R=70, stroke-width=14
- Base half-ring: 6% white
- Tolerance band (±5% around target): green at 27% alpha
- Deviation arc (from target to current): solid status color
- 2px white tick at target apex with "目标 XX%" label
- Current value: 6px filled circle pointer + white stroke

### 5.11 Timeline (news + rebalance history)
- News timeline: vertical rail at x=36 (1px border line), each item has a 10px filled circle with surface-color border
- Each item: date + sentiment chip + headline + 3px relevance bar
- History timeline: horizontal SVG, events alternate above/below the axis (50/50 split), each connected to the axis by a 1px dashed line and a 6px filled circle with white inner dot

---

## 6. Per-Tab Implementation Notes

### Tab 1 — 持仓总览 (`tab1-holdings.jsx`)

**Source data**: `data/processed/signals_{YYYYMMDD}.json` (PortfolioSummary + StockSignal list) + `holdings_{YYYYMMDD}.csv`

**Streamlit recipe**:
1. **Header row**: `st.columns([3, 1, 1])` with title left + 2 SummaryStat cards right
2. **Tab nav**: custom HTML or `st.tabs(["持仓总览", "每日策略简报", "个股深度分析", "信号仪表盘"])`
3. **Donut**: `plotly.graph_objects.Pie(hole=0.55)` with a hidden trace adding the target tick. Center annotation via `fig.add_annotation`
4. **3 KPI cards**: `st.columns(3)` each rendering custom HTML — `st.dataframe` won't give the precise look
5. **Heatmap**: `plotly.express.treemap(values='market_value', color='pnl_pct', color_continuous_scale=[(0, '#E84040'), (0.5, '#2a2a3a'), (1, '#00C47A')])` — Plotly's treemap will squarify automatically
6. **Deviation table**: `st.dataframe` with `.style.apply(highlight_deviation, axis=1)` returning yellow/red CSS for the row when `abs(deviation) > 5/10%`

### Tab 2 — 每日策略简报 (`tab2-brief.jsx`)

**Source data**: `data/agent_input/daily_news_*.json` (DailyNewsItem with `is_overnight_us=true`), `data/processed/signals_*.json`, LLM-generated markdown blob from Claude/GPT-4 (3 sections joined as one string with headings)

**Streamlit recipe**:
1. **Macro banner**: full-width custom HTML card. The CapEx state comes from `engine/macro_gate.py::get_macro_state()`. US stock chips: tile via `<div style="display:flex; gap:8px">` (Streamlit columns add too much gutter)
2. **Collapsibles**: `st.expander("📊 市场判断")` × 3. Apply CSS to restyle the expander header to match the mockup
3. **Score table**: `st.dataframe` with column config — `column_config.ProgressColumn` for A/B/C scores, `column_config.NumberColumn` for composite, custom HTML for badge. Or render fully as a custom HTML table for full fidelity
4. **US chart**: `plotly.graph_objects.Bar(orientation='h')` with `marker.color` per-bar, bidirectional layout via `xaxis.range=[-max, +max]`

### Tab 3 — 个股深度分析 (`tab3-stock-depth.jsx`)

**Source data**: `tushare.pro_bar()` or akshare for OHLCV + `engine/schemas.py::StockSignal` for tier/scarcity + news items filtered to this ticker

**Streamlit recipe**:
1. **Stock selector**: `st.selectbox` styled into a fat card (CSS override) showing all the live stats. Quick-switch chips: 5-column row of buttons
2. **Chart**: `plotly.subplots.make_subplots(rows=4, cols=1, shared_xaxes=True, row_heights=[0.5, 0.12, 0.19, 0.19], vertical_spacing=0.02)` with:
   - Row 1: `Candlestick` + `Scatter` for BB upper/lower (dashed) + `Scatter` for BB middle + `Scatter` for MA13W (accent blue)
   - Row 2: `Bar` for volume (color per candle direction)
   - Row 3: `Bar` for MACD histogram + `Scatter` for MACD line + `Scatter` for signal line (dashed) + `Scatter(mode='markers')` for golden/death cross dots
   - Row 4: `Scatter` for RSI + 2 dashed `add_hline` at 30 and 70, with `add_hrect` for overbought/oversold shading
3. **Layout**: dark template via `fig.update_layout(template='plotly_dark', paper_bgcolor='#1C1C2E', plot_bgcolor='#161623')`
4. **Fundamental card**: custom HTML — Streamlit `st.metric` can't match the 8-cell grid + ratings stacked bar. The ratings bar is a 3-segment flex div, no Plotly needed
5. **News timeline**: render as a custom HTML list. Each item posts back the URL on click (use `st.link_button` or `<a target="_blank">`)

### Tab 4 — 信号仪表盘 (`tab4-signals.jsx`)

**Source data**: `engine/macro_gate.py::get_macro_state()`, `methodology.md` (parse the §2.1 matrix into a Python dict, or hard-code into a `SCARCITY_MATRIX` constant), `engine/portfolio.py::check_portfolio_balance()`, the 7 triggers list

**Streamlit recipe**:
1. **Macro traffic light**: 3 columns, each a custom HTML card with a 36px circle, glow filter on the active one. Don't use `st.metric` — the visual treatment matters too much
2. **Big-4 CapEx table**: `st.dataframe` with conditional YoY column (green text for positive)
3. **Scarcity matrix**: `st.columns(4)` and inside each: a custom HTML block with the tier header (3px top border) + a vertical stack of chip divs. Read tier→stock list from `methodology.md` parsing or a hard-coded Python dict; map each chip's color via the score
4. **Gauges**: `plotly.graph_objects.Indicator(mode='gauge+number', gauge.shape='angular')`. The tolerance band requires `gauge.steps=[{range:[target-5, target+5], color: '#00C47A44'}]`, and `gauge.threshold` for the target tick
5. **Trigger table**: 4-column custom HTML — `st.dataframe` won't let you put a colored status pill in a cell cleanly; just render rows with `st.markdown(unsafe_allow_html=True)`
6. **History timeline**: SVG embedded via `st.markdown` or render with Plotly using `Scatter(mode='markers+text')` with manually positioned y-coords for the alternating above/below layout

### Section 06 — Holdings Editor sidebar (`holdings-editor.jsx`)

**Purpose**: a global left-rail panel that lets the user manually edit `holdings_{YYYYMMDD}.csv` without leaving the dashboard. Always present alongside the 4 tabs.

**Two states**:
- **Collapsed**: 56px-wide rail (was 32px in v1 — upgraded to fit avatar). Contains avatar (top), vertical "持仓" label, count line, expand arrow (bottom)
- **Expanded**: 420px-wide panel with 4 stacked regions:
  1. Sticky top status bar — snapshot date pill, source badge (`手动编辑` / `CSV 导入` / `OCR 待校正`), save + undo buttons, target CSV path hint
  2. Collapsible import dropzone — accepts CSV, parses → shows "已解析 N 行" with apply button
  3. Scrollable editable table — 8 columns including class dropdown, dirty cells highlighted yellow (`rgba(245,166,35,0.18)` bg + 1px neutral border + small dot top-right)
  4. Sticky bottom summary bar — total + 白马/弹性 progress rows with target tick; 弹性 row gets red border if any single elastic stock exceeds 8%

**Streamlit recipe**:
- Streamlit's native `st.sidebar` can't be collapsed to 56px — implement as `streamlit.components.v1.html` embedded React/Svelte, OR use `st.session_state['sidebar_open']` + injected CSS overriding `[data-testid="stSidebar"] { min-width: 56px; max-width: 56px; }` when collapsed
- For the editable table use `st.data_editor` with `column_config.SelectboxColumn` for 类别, `column_config.NumberColumn` with `min_value=0` for prices/qty, computed read-only column for 市值. Style the dirty state via CSS class injection by comparing the editor's return value to the original
- Persist after click on 保存快照: write to `data/agent_input/holdings_{date}.csv` and validate with `engine.schemas.HoldingRow`

### Section 07 — Auth layer (`holdings-editor-auth.jsx`)

**Goal**: single-user local passphrase gate. Not real account/password — just a "don't show my holdings to a coworker who walks up" guard.

**5 artboards mapping to the state machine**:

| Artboard | `collapsed` | `locked` | Sidebar shows | Main content |
|---|---|---|---|---|
| A | true  | true  | 56px rail with **grey avatar + lock icon** + LOCKED label | Blurred skeleton + centered lock card |
| B | false | true  | 420px **login form** (default) | Blurred skeleton + centered lock card |
| C | false | true  | 420px **login form** with red border + error text | Blurred skeleton + centered lock card |
| D | false | false | 420px **holdings editor** | Full dashboard + green "已解锁" badge + 锁定 button |
| E | true  | false | 56px rail with **blue avatar + green dot** | Full dashboard + green "已解锁" badge + 锁定 button |

**Avatar component (collapsed rail, both states)**:
- 36px circle, accent blue `#4F8EF7` (or `#3A4258` desaturated when locked)
- White initial letter (`W` in mockup), Noto Sans SC 500, ~45% of size
- Status dot at bottom-right, 11px, `2px solid #161623` border:
  - **Unlocked**: solid green `--bull`, glowing
  - **Locked**: dark grey `#2A2E3A` with a tiny SVG lock glyph inside
- Avatar is the primary expand trigger (cursor: pointer) — the bottom ⟩ arrow is the secondary

**Login form** (420px):
- Top — app identity: 36px rounded-square icon with lock SVG (accent blue tint bg), product name "my-invest-global" in JetBrains Mono 15px/600, subtitle in Noto Sans SC 12px muted
- Center — form:
  - Label: lock icon + "访问密语" (11px muted, 0.04em letter-spacing)
  - Input: `width: 100%`, `background: #0E1117`, `border: 1.5px solid var(--border)` → switches to `var(--bear)` on error, `padding: 12px 14px`, `font-family: JetBrains Mono`, `letter-spacing: 0.1em`, `type="password"` (renders as •)
  - Error message (below input, only when error): "⨯ 密语错误，请重试" in `var(--bear)`
  - Button: full-width accent blue with unlock SVG + "解锁", 12px padding, 6px radius
  - Forgot link: 10px JetBrains Mono `var(--text-dim)`, dotted underline — "忘记密语？查看 .env 文件"
- Bottom (separated by border-top, slight darker bg): label "本地安全" + 3 lines of textDim copy:
  - 数据仅存储在本机 data/ 目录
  - 无网络同步，无云备份
  - session 关闭后自动锁定

**Unlocked badge** (top-right of main content, both unlocked artboards):
- 6px green dot with `box-shadow: 0 0 6px var(--bull)88` + Mono "已解锁"
- + ghost "锁定" button (1px border, transparent bg, lock SVG + text) that immediately re-locks

**Locked-content treatment**:
- Main area renders a `filter: blur(2px); opacity: 0.35` skeleton (rectangles where cards would be, never real numbers)
- Overlay: `position: absolute; inset: 0; background: rgba(14, 17, 23, 0.78); backdrop-filter: blur(6px)`
- Centered modal card: 56px circle with lock icon, "持仓数据已锁定", contextual hint ("点击左侧 ⟩ 或头像解锁" when collapsed, "在左侧输入密语解锁" when expanded), bottom mono label "MY-INVEST-GLOBAL · LOCAL ONLY"

**Streamlit auth recipe**:

```python
# .env (user generates this once)
PASSPHRASE_HASH=<sha256 hex of their passphrase>

# app/auth.py
import hashlib, os
from typing import Literal

def verify(passphrase: str) -> bool:
    expected = os.environ.get("PASSPHRASE_HASH", "")
    actual = hashlib.sha256(passphrase.encode("utf-8")).hexdigest()
    return bool(expected) and actual == expected

# app/dashboard.py — at the very top, before ANY data loading
import streamlit as st
from app.auth import verify

if "unlocked" not in st.session_state:
    st.session_state["unlocked"] = False

if not st.session_state["unlocked"]:
    render_login_screen()      # blurred skeleton + sidebar login form
    st.stop()                  # critical: don't load holdings, don't call engine.*

# from here down everything assumes unlocked == True
render_dashboard()
```

Key constraints:
- **Never read holdings data before `unlocked == True`** — the goal is that someone snooping the running process can't see real numbers even in memory
- `st.session_state` is cleared on browser refresh, which naturally satisfies "session 关闭后自动锁定"
- The "锁定" button does `st.session_state["unlocked"] = False; st.rerun()`
- Bad passphrase counter is optional — for a single-user local tool, just show the error and let them retry; no rate limit needed

---

## 7. State & data flow

```
data/agent_input/*.json (DailyNewsFile, KolDigestFile)  ─┐
data/agent_input/holdings_*.csv                          ├─→ engine/analysis_engine.py
data/agent_input/macro_state.json                        ─┘                │
                                                                            ↓
                                            data/processed/signals_*.json (SignalsFile)
                                                                            ↓
                                                              app/dashboard.py (Streamlit)
                                                                            ↓
                                                                 4 tabs render from signals
```

- All schemas live in `engine/schemas.py` (Pydantic v2)
- Auto-refresh: `streamlit_autorefresh.st_autorefresh(interval=60_000)` per ADR-005
- The sidebar (per ADR-005) carries date selector + macro state + refresh button — **not in these mockups** since each artboard is one tab in isolation. Add it as the global chrome around `st.tabs`

---

## 8. Interactions

| Element | Behavior |
|---|---|
| Tab bar item | Click → switch tab, update URL `?tab=N` via `st.query_params` |
| Stock chip (Tab 3 quick-switch) | Click → re-render chart pane with selected ticker |
| Date range picker (Tab 3 1M/3M/6M/1Y/全部) | Click → re-slice OHLCV |
| Expander headers (Tab 2 brief) | Click → toggle open. All 3 open by default |
| Strategy brief "↻ 立即重生成" button | Click → re-call LLM with current signals payload |
| Manual macro override (Tab 4) | Click → opens form to call `engine/macro_gate.py::set_macro_state_override()` |
| News timeline item | Click → open `url` from DailyNewsItem in new tab |
| Treemap cell (Tab 1) | Click → navigate to Tab 3 with that stock selected |
| Score table row (Tab 2) | Click → navigate to Tab 3 |

---

## 9. Critical constraints (do not regress)

1. **No emoji-only KPIs.** Where the mockup uses 🟢🟡🔴 next to a label, it's a state pill — always paired with a colored badge or solid dot. Never rely on the emoji alone for color encoding (Windows/Linux render them as outlines).
2. **Tabular-nums everywhere a number lives.** Without it, the 18.59% in row N+1 misaligns with the 5.20% in row N.
3. **Never use Streamlit's default red (#FF4B4B)**. We use `#E84040` for "bear" and `#FF0000` only for hard stop_loss.
4. **Status colors are reserved.** Don't tint a card green to mean "active" — green = bullish. Use accent blue for "active/selected".
5. **Card padding is 12px**, not the Streamlit default. Override globally:
   ```python
   st.markdown("""<style>
     [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="column"] { gap: 12px; }
     /* etc */
   </style>""", unsafe_allow_html=True)
   ```

---

## 10. Files in this folder

| File | Contents |
|---|---|
| `index.html` | Entry point — load this in a browser to see all 7 sections / 12 artboards |
| `design-canvas.jsx` | Pan/zoom canvas wrapper (do not port — design tool only) |
| `design-system.jsx` | **Spec sheet** — every token + component shown as a swatch. Reference this first |
| `tab1-holdings.jsx` | Tab 1 layout, sample HOLDINGS array, donut + heatmap + deviation table |
| `tab2-brief.jsx` | Tab 2 layout, US_STOCKS, CAPEX_STATE, SCORE_ROWS, brief sections, alerts |
| `tab3-stock-depth.jsx` | Tab 3 layout, synthetic OHLCV gen, TA indicators (BB, MACD, RSI), FUND, NEWS |
| `tab4-signals.jsx` | Tab 4 layout, MACRO_STATES, CLOUD_CAPEX, SCARCITY_MATRIX, TRIGGERS, HISTORY |
| `holdings-editor.jsx` | Section 06 — collapsible sidebar holdings editor (no auth) |
| `holdings-editor-auth.jsx` | Section 07 — auth layer (passphrase login, lock states, masked main content) |

The `.jsx` files contain hard-coded sample data that **mirrors `engine/schemas.py` shapes** — use the data structures as a template for Pydantic-validated payloads, but don't ship the sample values to prod.

---

## 11. Suggested phase plan for Claude Code

1. **P1 — Scaffold + tokens + auth gate** (2-3 hours): inject Google Fonts, write `app/styles.py::inject_dark_theme()`, set page config to dark, build `app/auth.py` (sha256 verify + `.env` PASSPHRASE_HASH). Wire the lock screen + login form (artboards A/B/C). Verify `st.stop()` keeps holdings data unreachable when locked
2. **P2 — Sidebar editor shell** (3-4 hours): build the 56px ↔ 420px sidebar toggle via embedded React component or CSS-override approach. Wire `st.data_editor` for the holdings table; persist to `data/agent_input/holdings_{date}.csv` with `HoldingRow` validation
3. **P3 — Tab 1** (4-6 hours): wire `engine/portfolio.py::check_portfolio_balance()` to donut + KPI cards. Build heatmap via Plotly treemap. Style deviation table
4. **P4 — Tab 4** (4-6 hours): static-ish data, mostly layout. Get the macro traffic-light + scarcity matrix CSS right since they're the most custom
5. **P5 — Tab 2** (3-5 hours): wire LLM brief markdown into expanders, build the score table with progress bars, US chart via Plotly
6. **P6 — Tab 3** (6-8 hours): the chart is the heavy lift. Make `make_subplots` work, then layer the indicators one at a time
7. **P7 — Polish**: cross-tab navigation, sidebar (per ADR-005), auto-refresh, URL state, lock button in every tab header

---

*This handoff was generated from a hi-fi React prototype. The visual spec is authoritative; the Streamlit recipes in §6 are suggestions — choose Streamlit primitives where they fit, custom HTML/CSS where they don't.*
