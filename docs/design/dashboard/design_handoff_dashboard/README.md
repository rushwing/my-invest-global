# Design Handoff: my-invest-global Dashboard · v3

> **Target codebase**: `my-invest-global` · Streamlit 1.32+ · Plotly · Python 3.12
> **Spec source**: `docs/adr/ADR-005-frontend-dashboard.md` · `methodology.md` · `engine/schemas.py`
> **Suggested install location**: drop this folder at `docs/design/dashboard/` in the project repo.
> **Version**: v3 — adds GlobalActionBar + 5-tab navigation + Tab 5 调仓分析 + T+1 settlement rules

---

## 0. What's new in v3

This iteration restructures the dashboard around a **single GlobalActionBar** and adds a 5th tab for actionable rebalancing. Read this before §1 if you've seen v2.

### Decisions resolved in this iteration

| # | Decision | Choice |
|---|---|---|
| Q1 | Holdings editor surface | **Inline table in Tab 1** (sidebar retired) |
| Q2 | Per-tab header vs global bar | **Single GlobalActionBar** owns refresh / run / timestamps / auth |
| Q3 | Tab labels | **Shortened** (`持仓总览 / 每日简报 / 个股分析 / 信号仪表盘 / 调仓分析`) |
| Q4 | Tab 3 vs new Tab 5 | **Coexist** — Tab 3 = single-stock research, Tab 5 = today's actionable decisions |
| Q5 | Mock API behavior | **setTimeout simulation** in prototype; real `POST /api/*` endpoints documented below |

### Major new pieces

1. **`GlobalActionBar`** — 44px sticky top strip used by all 5 tabs. Holds logo, 5 tab pills, system status (LIVE / 盘后 / 数据异常), cache countdown, refresh button, run-analysis button, auth indicator + lock button. **6 documented states.** Replaces the per-tab "ROW 1 header strips" from v2.
2. **Tab 1 持仓总览 v3** — inline 10-column editable holdings table with new `T+1 可用` column. KPI cards now include target-marker progress bars.
3. **Tab 2 每日简报 v3** — adds **T+1 调仓摘要条** (4 cells + CTA to Tab 5) and `操作 → 进入分析` column on the score table.
4. **Tab 5 调仓分析** — entirely new tab. Multi-stock selector → analysis cards → focused K-line + **筹码分布 (chip distribution histogram)** → today's executable operation list (T+1-aware) → collapsible history.
5. **T+1 settlement rules** — first-class treatment everywhere stocks are listed. Three states: `bought_today` / `partial` / `all_available`.

### Retired in v3

- **Holdings editor sidebar** (collapsed 56px ↔ expanded 420px) — fully replaced by Tab 1's inline table. Auth indicator/lock now in GlobalActionBar.
- **Per-tab `[↻ 刷新行情]` + `[▶ 运行分析]` buttons** — moved to GlobalActionBar (single source of truth).
- **Old `Tab1Holdings` / `Tab2DailyBrief`** components — superseded by `Tab1HoldingsV2` / `Tab2BriefV2`.

### Carry-overs (legacy in this drop)

- **Tab 3 个股深度** + **Tab 4 信号仪表盘** still render with their internal tab bar. Marked as "待整合 GAB" in artboard 05/06 — next refactor pass should drop their internal `TabBar` and prepend `<GlobalActionBar activeTab={2|3} />` exactly like Tab 1/2/5.
- **Login form spec** (auth artboards) — visual copy / inputs / security notes still apply, but should be reimplemented as a **full-screen centered modal** (not a sidebar). GlobalActionBar owns the unlock state indicator + lock button. See §6.6.

---

## 1. Overview

This bundle is the **visual design reference** for the 5-tab personal stock advisor dashboard described in `ADR-005-frontend-dashboard.md`. It contains:

- An HTML/React clickable canvas with 8 sections (design system + GAB spec + 5 tabs + auth ref)
- All design tokens, type scale, component specs the Streamlit implementation should match
- T+1 settlement business rules + chip distribution visualization

### About these files

The `.html` + `.jsx` files are **design mockups, not production code**. React prototypes via inline Babel. Re-implement in **Streamlit + Plotly** (per ADR-005). Where Streamlit defaults clash with the spec, **override via custom CSS** — don't water down the visual.

## 2. Fidelity

**Hi-fi.** Pixel-perfect — match colors / typography / spacing / dimensions exactly. Specific guidance:

- **12px card padding** is intentional — do not loosen to Streamlit's default 1rem
- **JetBrains Mono with tabular-nums** for every numeric value
- **44px GlobalActionBar** height is fixed
- **Status colors are semantic** — never reuse green for "click me" or red for "danger zone backgrounds"

## 3. How to view

Open `index.html` in any modern browser. 8 sections on the dark canvas:

| # | Section | Artboards |
|---|---------|-----------|
| 01 | Design System Spec | tokens, type, components |
| 02 | GlobalActionBar (6 states) | Normal / Refreshing / Analyzing / Both / Error / Locked + live interactive |
| 03 | Tab 1 持仓总览 v3 | full screen with GAB on top |
| 04 | Tab 2 每日简报 v3 | full screen with GAB |
| 05 | Tab 3 个股深度 (legacy) | TODO: replace internal tab bar with GAB |
| 06 | Tab 4 信号仪表盘 (legacy) | TODO: replace internal tab bar with GAB |
| 07 | Tab 5 调仓分析 (new) | full screen with GAB |
| 08 | Auth (legacy reference) | login form spec — re-host as full-screen modal |

Pan with click-drag, zoom with scroll, double-click any artboard for fullscreen focus, ←/→ to step between.

## 4. Design Tokens

### 4.1 Colors

```css
/* Surfaces */
--bg:           #0E1117;
--surface:      #1C1C2E;
--surface-alt:  #161623;
--border:       rgba(255,255,255,0.06);
--border-strong:rgba(255,255,255,0.12);

/* Text */
--text:         #E8EAED;
--text-muted:   #9AA0AC;
--text-dim:     #5C616E;

/* Brand */
--accent:       #4F8EF7;

/* Status / signals */
--bull:         #00C47A;
--neutral:      #F5A623;
--bear:         #E84040;
--stop:         #FF0000;

/* Signal action codes — engine/schemas.py StockSignal.action_code */
--sig-strong-add: #00C47A;
--sig-hold-add:   #4F8EF7;
--sig-hold:       #888888;
--sig-reduce:     #E84040;
--sig-stop-loss:  #FF0000;

/* Scarcity tier — methodology.md §2.1 */
--tier-1: #FF7A1A;
--tier-2: #F5A623;
--tier-3: #9AA0AC;
--tier-4: #4F8EF7;

/* PnL heat gradient */
/* linear-gradient(90deg, var(--bear) 0%, #2a2a3a 50%, var(--bull) 100%) */
/* Maps -20% → 0 → +20% */
```

### 4.2 Typography

| Token | Family | Size / line-height | Weight | Use |
|---|---|---|---|---|
| Display | Noto Sans SC | 22-28 / 32 | 600 | Page titles |
| H1 | Noto Sans SC | 18 / 24 | 600 | Card section titles |
| H2 | Noto Sans SC | 14-15 / 20 | 600 | Card titles |
| Body | Noto Sans SC | 12-13 / 18 | 400 | Default text |
| Label | Noto Sans SC / JetBrains Mono | 10-11 / 14 | 500 | Field labels (uppercase 0.06em) |
| Mono Big | JetBrains Mono | 18-26 / 28 | 600-700 | KPIs, prices, PnL% |
| Mono | JetBrains Mono | 12-13 / 18 | 500 | All numeric cells, codes |

**All numbers must have**: `font-variant-numeric: tabular-nums` for column alignment.

### 4.3 Spacing

Scale: 4 / 8 / 12 / 16 / 20 / 24 / 28 px. Card padding default **12px**, page padding **24-28px**, card gap **12px**, GAB padding-x **16-20px**.

### 4.4 Radii

| Element | Radius |
|---|---|
| Badge / tag / status pill | 3-4 px |
| Card | 6-8 px |
| Modal | 8-12 px |
| Pill button | 999px (full round) |

## 5. Component Specs

### 5.1 GlobalActionBar (44px sticky top)

Layout: `flex row, height 44px, surface bg, border-bottom 1px border, padding 0 16px 0 20px, gap 10px`

**Left section** (logo + name):
- 24×24 rounded-4 icon, dark teal bg `#1C3A3A` + 1px green border, white chart-line SVG glyph
- `MY INVEST` JetBrains Mono 11px / 600 / accent + `GLOBAL` 11px / muted

**Center section** (5 tab pills, gap 4):
- Each pill: padding 5×11, radius 5, `01–05` mono number prefix (textDim or accent when active), Chinese label
- Active: accent 15% bg + 1px accent 50% border + bold text + accent number prefix
- Inactive: transparent bg + transparent border + muted text

**Right section** (gap 8):
- SystemStatus: 6px dot + 10px mono label
  - `live`: bull, pulsing glow + `LIVE · A股盘中`
  - `closed`: text-dim + `盘后`
  - `error`: bear + `数据异常`
- CacheCountdown: 10px mono `↻ MM:SS 前` in surfaceAlt pill, or `刷新中…` when refreshing
- Refresh button: 28×28 ghost icon button (refresh SVG); spinner when loading; bear bg+border when errored
- Run button: 28×28 primary accent icon button (play SVG); spinner when loading
- Separator (1px × 20px)
- AuthIndicator: 6px bull/bear dot + `已解锁`/`已锁定` 10px mono; locked variant hides the 锁定 button
- Lock button (visible only when unlocked): 28px height ghost button with lock icon + `锁定`

**Analyzing state**: 2px progress strip pinned to `bottom: -1` of the bar, accent 22% bg, animated 34% sliding sweep.

**Props interface**:
```ts
interface GlobalActionBarProps {
  activeTab: 0 | 1 | 2 | 3 | 4;
  onTabChange: (tab: number) => void;
  onRefresh: () => Promise<void>;
  onRunAnalysis: () => Promise<void>;
  onLock: () => void;
  isRefreshing: boolean;
  isAnalyzing: boolean;
  marketStatus: 'live' | 'closed' | 'error';
  lastUpdated: Date | null;
  isUnlocked: boolean;
  errored?: boolean;
  countdown?: string; // e.g. "03:24"
}
```

### 5.2 T+1 Availability Badge

Three states, always rendered as a single pill or a pill + mini bar:

- **bought_today**: neutral tint pill + lock SVG glyph + label `今日买入`. Tooltip on hover: `T+1 锁仓 · {tomorrow_date} 可操作`.
- **partial**: bull tint pill `X/Y 手可用` + below it a 60×3 mini progress bar filled to `available/total` ratio.
- **all_available**: bull tint pill with leading 4px solid dot + label `全部可用`.

Rendering location: holdings table column, brief item rows, analysis card rows.

### 5.3 KPI Card (Tab 1)

- Padding 12, radius 8, surface bg, 1px border
- Label (11 muted) → big value (22 mono 600, bull or text) → sub (10 dim mono)
- **KpiBar variant** for proportions (弹性 / 白马 仓位):
  - Adds a 4px high progress bar below the value, filled to `pct%`
  - **1.5px white tick at the target percentage** — this is mandatory; it's the only way to read deviation at a glance

### 5.4 Editable Holdings Table (Tab 1, ROW 5)

10 columns, total min-width 1140px:

| Col | Width | Type | Editable | Notes |
|---|---|---|---|---|
| 代码 | 80 | mono | no | Clickable underline → Tab 3 |
| 名称 | 110 | text | yes | |
| 类别 | 100 | pill dropdown | yes | 白马股 / 弹性股 / 自选 |
| 成本价 | 84 | mono right | yes | ¥X.XX |
| 现价 | 84 | mono right | no | Color bull/bear vs cost |
| 数量 | 70 | int right | yes | |
| 市值 | 100 | mono right | no | Computed = price × qty (×100 for 手) |
| 浮盈% | 84 | mono right | no | Color bull/bear |
| T+1 可用 | 116 | badge | no | See §5.2 |
| 操作 | 80 | icons | — | ✎ edit + × delete |

**Row states** (mutually exclusive precedence: stop_loss > selected > dirty > normal):

| State | Background | Left border |
|---|---|---|
| normal | transparent | 2px transparent |
| dirty (any cell modified) | `rgba(245,166,35,0.07)` | 2px neutral |
| selected | `rgba(79,142,247,0.08)` | 2px accent |
| stop_loss | `rgba(232,64,64,0.07)` + name in bear | 2px transparent |

**Dirty cells** (individual): yellow tint background `rgba(245,166,35,0.15)`, 1px neutral 28% border top+bottom, 4px neutral dot in top-right corner of cell.

**Add row**: dashed top border, `+ 添加持仓` accent text, "name lookup chip" on the right showing what would auto-resolve when 6 digits are typed.

### 5.5 Allocation Donut (Tab 1, ROW 3 left)

- 180×180 SVG, R=70, stroke=18
- Outer dashed circle at R+14 = target indicator
- 1.5px white tick at exactly 67%
- Ring colors: accent if `|deviation| < 5%`, neutral 5-10%, bear >10%
- Center: `总市值` 10px label + `¥XX.X` 18px mono white + `万元` 9px dim sub
- Legend right: 2 rows × (10px color square + label + percentage on right + `目标 X%` sub)

### 5.6 Treemap Heatmap (Tab 1, ROW 3 right)

- 6-cell compact grid: 2 rows × 3 cols (proportions 2.2 : 1.2 : 1 for col widths to give the biggest holding the largest cell)
- Each cell: stock name 14px white, code 9px white/60, PnL% 20px white mono bold at bottom
- Background gradient (PnL → color): linear interpolation in alpha, capped 15-70%
  - Positive: `rgba(0,196,122, 0.15 + |t| * 0.55)` where t = pnl/20 clamped [-1, 1]
  - Negative: `rgba(232,64,64, 0.15 + |t| * 0.55)`
- Border: matching bull/bear at 55% alpha
- Click → emit `onStockSelect(code)` → Tab 3

### 5.7 Score Table Row (Tab 2, ROW 4)

7 columns: 股票 / 技术A / 基本面B / 情绪C / 综合 / 建议 / 操作

- A/B/C cells: mini horizontal layout = `32px mono right-aligned score | 4px progress bar filled to score%`
- Color tiers for progress + composite text:
  - ≥75 bull · 60-75 accent · 45-60 grey · 30-45 neutral · <30 bear
- 综合 column: 18px mono bold colored by tier
- 操作 column: `进入分析 →` link in accent
- `stop_loss` row: full row bear-tint 12% background

### 5.8 T+1 Rebalance Summary Bar (Tab 2, ROW 5)

5 cells, separated by 1px borders, all heights match:
1. `今日可操作` (text color)
2. `建议减仓 N 只` (bear) with sub-line stock codes
3. `建议加仓 N 只` (bull) with sub
4. `T+1 锁仓 N 只` (neutral) with sub
5. CTA cell: accent tinted bg + `进入调仓分析 →` accent button

Each metric cell: 32×32 colored square icon (16% tint bg + 28% border) + label / value / sub stacked.

### 5.9 Analysis Cards (Tab 5, Section A — horizontal scroll)

240px wide × variable height cards in a `display: flex; gap: 12; overflow-x: auto` strip.

Card anatomy (top to bottom):
1. **Header row**: Tier badge (T1/T2/T3/T4 small pill) + stock name + code + action badge (top-right, e.g. `减仓`)
2. **Price block**: 18px mono current price + small grey `成本 ¥X.XX` right-aligned + below: bull/bear `浮盈 ±X.XX%` spanning full width
3. **T+1 row**: T+1 badge (24px min-height even when empty for alignment)
4. **Scores grid** (top + bottom dashed border): 4 columns: 技术 / 基本面 / 情绪 / 综合(big bold)
5. **Recommendation**: 11px muted, 1-2 lines, `min-height: 32`
6. **Action button**: full-width, primary accent for executable, surface-alt + greyed + lock prefix `🔒 T+1 锁仓` when disabled

**Focused state**: surface bg (vs surface-alt), 1px accent 53% border + 2px accent 13% outer shadow.

### 5.10 Chip Distribution (Tab 5, Section B right)

This is the new visual element. **A horizontal bar histogram with price on the Y axis and % of shares on the X axis.**

- Canvas 380×320, plot area `left=50, right=14, top=10, bottom=26`
- **Y-axis** (price): ticks at min/max + key levels (current, cost), labeled `¥XXX` in mono dim (or text for current/cost)
- **X-axis** (share %): 0 to maxPct (~7%), labeled at 0/2/4/6%
- **Bucket bars**: ~33 horizontal bars (price step ~12), each width = `(pct / maxPct) * plotW`, height = `((plotH) / count) - 1`
- **Fill colors by price zone** (relative to current price + cost basis):
  - `price > current`: `var(--text-dim)` at 0.28 alpha (解套压力 — overhead supply)
  - `cost < price ≤ current`: `var(--bull)` at 0.55 alpha (获利筹码)
  - `price ≤ cost`: `var(--bear)` at 0.55 alpha (亏损筹码)
- **Current price line**: bear color, 1.2px dashed `4 3`, with a labeled rounded-rect on the right edge: `现价 ¥XXX`
- **Cost basis line**: text-muted, 1px dashed `3 3`, labeled rounded-rect: `成本 ¥XXX`
- **Metric chips** (3 in a row below): 筹码集中度 / 获利盘 / 套牢/解套压力 — each in a `surface-alt` rounded rect, 9px dim label + 13px mono colored value
- **Legend** (small): swatch boxes showing the 3 zones with their alpha levels

### 5.11 K-Line Mini (Tab 5, Section B left)

Same visual language as Tab 3 chart but compact:
- 720 × ~290 px SVG
- 60 candles + MA30 line (neutral orange) + cost basis dashed line (text-muted) + MACD pane below (70px)
- Golden cross / death cross dots on MACD line
- Date-range pills `1M / 3M / 6M` in top-right (3M active by default)

### 5.12 Operation List (Tab 5, Section C)

7-column table:

| Col | Notes |
|---|---|
| 操作 | Tag pill: 买入 (bull) / 卖出 (bear) / 减仓 (bear) |
| 股票 | Name + code |
| 数量 | `N 手` right-align mono |
| 参考价 | `¥X.XX` mono |
| 预计金额 | `¥X,XXX` mono bold (= qty × price × 100) |
| 依据 | 1-line reasoning |
| 状态 | `可执行` bull pill or `T+1 锁定` neutral pill |

- **T+1 locked rows**: opacity 0.7 + `rgba(245,166,35,0.06)` bg + status pill = T+1 锁定
- **Footer band** (surface-alt): `预计调仓后弹性仓位: X.X% → Y.Y%` with arrow + `回归目标区间` tag + total trade amount on the right

## 6. Per-Tab Streamlit Implementation Notes

### 6.1 Global setup — GlobalActionBar (`global-action-bar.jsx`)

Inject as an `streamlit.components.v1.html` block at the top of every page, OR build as a custom HTML strip via `st.markdown(unsafe_allow_html=True)`. State in `st.session_state`:

```python
ss = st.session_state
ss.setdefault('active_tab', 0)
ss.setdefault('is_refreshing', False)
ss.setdefault('is_analyzing', False)
ss.setdefault('market_status', detect_market_status())  # live / closed / error
ss.setdefault('last_updated', None)
ss.setdefault('unlocked', False)  # see §6.6 auth

# After GAB is rendered, route to the active tab
TABS = [render_tab1, render_tab2, render_tab3, render_tab4, render_tab5]
TABS[ss.active_tab]()
```

The refresh / run buttons trigger long-running tasks. Use `st.spinner` + a background task (e.g. `asyncio.create_task` in a callback or a polling pattern):

```python
def on_refresh():
    ss.is_refreshing = True
    refresh_market_data()  # sync wrapper around tushare / akshare
    ss.last_updated = datetime.now()
    ss.is_refreshing = False
    st.rerun()
```

For animations (spinner, progress strip), embed the visual states in the HTML component — Python toggles the props.

### 6.2 Tab 1 持仓总览 (`tab1-holdings-v2.jsx`)

**Source data**: `data/processed/signals_{YYYYMMDD}.json` (PortfolioSummary + StockSignal list) + `data/agent_input/holdings_{YYYYMMDD}.csv` + T+1 status from `data/db/lots.sqlite` (lot-level history).

**Streamlit recipe**:
1. **GlobalActionBar at top** (see §6.1)
2. **ROW 1 page header**: `st.columns([3, 1])` — left for title strip, right for "数据时效 HIGH · 缓存 14:32" chip
3. **ROW 2 KPI cards**: `st.columns(3)` each a custom HTML block. The progress bar with target tick is impossible via `st.metric` — use custom div with `position: relative`
4. **ROW 3 Donut + Heatmap**: `st.columns([1.22, 1])`
   - Donut: `plotly.graph_objects.Pie(hole=0.55)` + manually-positioned annotation for center text + a separate `Scatter` trace for the 1.5px target tick on the outer ring (computed angle → x/y)
   - Heatmap: `plotly.express.treemap` with `color_continuous_scale=[(0, '#E84040'), (0.5, '#2a2a3a'), (1, '#00C47A')]`, click handler via `plotly_events` extension
5. **ROW 4-5 Holdings table**:
   - Header strip: `st.columns([...])` with `st.button` for `+ 添加`, file uploader for CSV import, primary save button (disabled when `dirty_count == 0`), filter pills
   - Table: `st.data_editor` with `column_config.SelectboxColumn` for 类别, `column_config.NumberColumn` for prices/qty, **computed read-only 市值 column**, custom HTML for T+1 badge column via `column_config.Column(disabled=True, ...)` and pre-rendered HTML
   - Dirty highlight: compare returned df to original; emit a `style.apply(highlight_dirty, axis=None)` per-cell
   - Save: write to `data/agent_input/holdings_{date}.csv` + validate every row with `engine.schemas.HoldingRow` before persisting
6. **T+1 column** rendering: pre-compute a `t1_status` dict from lot history, generate badge HTML in a hidden CSS class, render the column as a string with `unsafe_allow_html=True`

### 6.3 Tab 2 每日简报 (`tab2-brief-v2.jsx`)

**Source data**: `data/agent_input/daily_news_*.json` (DailyNewsItem with `is_overnight_us=true`), `data/processed/signals_*.json`, LLM-generated markdown blob from `engine/llm/brief_generator.py`.

**Streamlit recipe**:
1. **GAB at top**
2. **ROW 1 header**: page title + `分析自选` ghost button (tab-specific control — refresh / run are in GAB)
3. **Macro banner**: full-width custom HTML card with 50/50 grid. The traffic-light pills use `box-shadow: 0 0 12px <color>33` glow when active. US stock chips: tile via 5-column flex (not `st.columns` — too much gutter)
4. **Brief sections**: 3 × `st.expander("📊 市场判断")`. Apply CSS to restyle expander headers to match (chevron color, signal badge on right). Body content is markdown rendered via `st.markdown`
5. **Score table**: `st.dataframe` with `column_config.ProgressColumn` for A/B/C, `column_config.NumberColumn` for composite, custom HTML for badge + action column. OR render fully as a custom HTML table for full fidelity
6. **T+1 rebalance bar**: full-width custom HTML, 5 cells via flex. The accent CTA cell uses `st.button` with custom CSS to look like the design — click navigates by setting `ss.active_tab = 4`

### 6.4 Tab 3 个股深度 (`tab3-stock-depth.jsx`)

⚠️ Currently rendered with its **legacy internal tab bar** — please replace with `<GlobalActionBar activeTab={2} />` during your Tab 3 implementation pass to match Tab 1/2/5.

**Source data**: `tushare.pro_bar()` or akshare for OHLCV + `engine/schemas.py::StockSignal` for tier/scarcity + news items filtered to this ticker.

**Streamlit recipe**:
1. **Stock selector**: `st.selectbox` styled into a fat card (CSS override) showing all the live stats. Quick-switch chips: 5-column row of buttons
2. **Chart**: `plotly.subplots.make_subplots(rows=4, cols=1, shared_xaxes=True, row_heights=[0.5, 0.12, 0.19, 0.19], vertical_spacing=0.02)`:
   - Row 1: `Candlestick` + `Scatter` for BB upper/lower (dashed) + `Scatter` for BB middle + `Scatter` for MA13W (accent blue)
   - Row 2: `Bar` for volume (color per candle direction)
   - Row 3: `Bar` for MACD histogram + lines + golden/death cross dot markers
   - Row 4: `Scatter` for RSI + 2 dashed `add_hline` at 30/70 + `add_hrect` for overbought/oversold shading
3. **Dark template**: `fig.update_layout(template='plotly_dark', paper_bgcolor='#1C1C2E', plot_bgcolor='#161623')`
4. **Fundamental card**: custom HTML — `st.metric` can't match the 8-cell grid + ratings stacked bar
5. **News timeline**: custom HTML list, click → open `url` in new tab via `st.link_button`

### 6.5 Tab 4 信号仪表盘 (`tab4-signals.jsx`)

⚠️ Same legacy-bar caveat as Tab 3.

**Source data**: `engine/macro_gate.py::get_macro_state()`, `methodology.md §2.1` (parse into Python dict or hard-code into `SCARCITY_MATRIX` constant), `engine/portfolio.py::check_portfolio_balance()`, the 7 triggers list.

**Streamlit recipe**:
1. **Macro traffic light**: 3 columns, each a custom HTML card with a 36px circle. Glow filter on active. Don't use `st.metric`
2. **Big-4 CapEx table**: `st.dataframe` with conditional YoY column
3. **Scarcity matrix**: `st.columns(4)` and inside each a custom HTML block with tier header (3px top border) + vertical stack of chip divs
4. **Gauges**: `plotly.graph_objects.Indicator(mode='gauge+number', gauge.shape='angular')`. Tolerance band requires `gauge.steps=[{range:[target-5, target+5], color: '#00C47A44'}]`, `gauge.threshold` for target tick
5. **Trigger table**: 4-column custom HTML — `st.dataframe` can't put a colored status pill in a cell cleanly
6. **History timeline**: SVG embedded via `st.markdown`, or `Scatter(mode='markers+text')` with alternating y-coords

### 6.6 Tab 5 调仓分析 (`tab5-rebalance.jsx`)

**Source data**: `POST /api/analyze-selected → engine.rebalance.analyze(codes)`, `engine.lots.get_t1_status()`, `engine.chip_distribution.compute(code)`.

**Streamlit recipe**:
1. **Stock selector panel**: `st.columns(2)` for 当前持仓 / 自选观察. Each chip is a custom HTML `<div>` with checkbox circle + code + name + PnL + T+1 dot. Use `st.button` with empty label as a transparent overlay to capture clicks
2. **Section A — Analysis cards**: horizontal flex scroll container via custom HTML. Streamlit's `st.columns` won't scroll horizontally — render the whole strip in one `st.markdown(unsafe_allow_html=True)` block
3. **Section B left — K-line + MACD**: `make_subplots(rows=2, cols=1, row_heights=[0.7, 0.3])`. Add cost basis as `add_hline(y=cost, line_dash='dash', annotation_text='成本 ¥XX')`. Range pills [1M / 3M / 6M]: client-side filter via `st.session_state['t5_range']` rerunning the chart
4. **Section B right — Chip distribution**:
   ```python
   import plotly.graph_objects as go
   fig = go.Figure()
   buckets = compute_chip_distribution(code)  # returns list of {price, pct}
   colors = [zone_color(b.price, cost, current) for b in buckets]
   fig.add_trace(go.Bar(
       y=[b.price for b in buckets],
       x=[b.pct for b in buckets],
       orientation='h',
       marker=dict(color=colors),
       hovertemplate='价位 ¥%{y}<br>占比 %{x:.2f}%<extra></extra>',
   ))
   fig.add_hline(y=cost, line=dict(color='#9AA0AC', dash='dash'))
   fig.add_hline(y=current, line=dict(color='#E84040', dash='dash', width=1.5))
   fig.update_layout(
       template='plotly_dark',
       paper_bgcolor='#1C1C2E', plot_bgcolor='#161623',
       height=320, width=380,
       margin=dict(l=50, r=14, t=10, b=26),
       xaxis_title='持仓占比 (%)',
       yaxis_title=None,
   )
   ```
   Below the chart: 3 metric chips via custom HTML grid.
5. **Section C — Operation list**: `st.dataframe` with `column_config` per column. **T+1 locked rows** styled via `.style.apply(highlight_t1_locked)`. Footer band: custom HTML with the projected elastic % transition
6. **Section D — History timeline**: collapsed `st.expander`. Inside: simple `st.dataframe` of past actions

#### T+1 Business Rules (critical)

The `engine/lots` module must track per-lot history:

```python
# data/db/lots.sqlite
CREATE TABLE lots (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL,
  qty INTEGER NOT NULL,
  buy_date DATE NOT NULL,
  cost_price REAL NOT NULL
);

def get_t1_status(code: str, today: date) -> dict:
    lots = query("SELECT qty, buy_date FROM lots WHERE code = ?", code)
    total = sum(l['qty'] for l in lots)
    locked = sum(l['qty'] for l in lots if l['buy_date'] == today)
    available = total - locked
    if total == locked:
        return {'status': 'bought_today', 'available': 0, 'total': total}
    if locked > 0:
        return {'status': 'partial', 'available': available, 'total': total}
    return {'status': 'all_available', 'available': total, 'total': total}
```

Sell actions must subtract from `available` only — never from `locked`. The rebalance engine excludes locked lots from sell suggestions and grays out their action buttons in the UI.

### 6.7 Auth — full-screen modal (replaces sidebar)

The auth artboards in section 08 still drive the visual spec for the **login form contents** (lock icon header, monospace input, dotted-underline forgot link, 3-line security note). But the **hosting surface changes**: instead of a sidebar, render as a **full-screen centered modal on a blurred backdrop** before any tab content is shown.

```python
# app/auth.py
import hashlib, os, streamlit as st

def verify(passphrase: str) -> bool:
    expected = os.environ.get('PASSPHRASE_HASH', '')
    return bool(expected) and hashlib.sha256(passphrase.encode('utf-8')).hexdigest() == expected

# app/dashboard.py — at the very top, before ANY data loading
def render_lock_screen():
    # Full-page dark blurred backdrop + centered 420px card with:
    #   - 36×36 accent-tint icon + 'my-invest-global' title + 'v0.1 · personal advisor' sub
    #   - 12px '持仓数据受本地密语保护' copy
    #   - Lock icon + '访问密语' label
    #   - Password input (dark bg, mono font, type=password)
    #   - Error row when applicable
    #   - Accent 'Unlock' button (full width, lock icon)
    #   - Forgot link (dotted underline)
    #   - Bottom security notes (3 lines)
    pass

if not st.session_state.get('unlocked'):
    render_lock_screen()
    st.stop()

# from here down everything assumes unlocked == True
render_global_action_bar()
render_active_tab()
```

GlobalActionBar's auth indicator + 锁定 button toggles `ss.unlocked` and triggers `st.rerun()`. Browser refresh naturally clears `st.session_state`, so "session 关闭后自动锁定" is implicit.

The `.env` file holds `PASSPHRASE_HASH=<sha256 hex>`. The user generates it once via:

```bash
python -c "import hashlib; print(hashlib.sha256(input('passphrase: ').encode()).hexdigest())"
```

## 7. State & data flow

```
data/agent_input/*.json (DailyNewsFile, KolDigestFile)
data/agent_input/holdings_*.csv        ─┐
data/agent_input/macro_state.json       ├─→ engine/analysis_engine.py
data/db/lots.sqlite (T+1 lot history)   ─┘             │
                                                       ↓
                              data/processed/signals_*.json (SignalsFile)
                                                       ↓
                                            app/dashboard.py (Streamlit)
                                                       ↓
                                    GlobalActionBar + 5 tabs render from signals
```

## 8. API contracts (real endpoints to implement)

| Method | Path | Body | Returns |
|---|---|---|---|
| GET  | `/api/holdings` | — | `{ holdings: HoldingRow[], snapshot_date }` |
| POST | `/api/holdings` | `HoldingRow[]` | 204 |
| POST | `/api/holdings/import` | `FormData(file: CSV)` | `{ parsed, rows }` |
| GET  | `/api/t1-status` | — | `{ [code]: { bought_today, available_qty, total_qty, buy_date } }` |
| POST | `/api/refresh-market-data` | `{}` | `{ status, last_updated }` |
| POST | `/api/run-analysis` | `{}` | `{ session_id, signals, status }` |
| POST | `/api/analyze-watchlist` | `{}` | `{ session_id, signals }` |
| POST | `/api/analyze-selected` | `{ codes: string[] }` | `{ signals, chip_data, t1_status }` |
| GET  | `/api/chip-distribution/{code}` | — | `{ price_buckets, avg_cost, current_price, profit_pct, concentration }` |
| POST | `/api/execute-order` | `{ code, action, qty, price }` | `{ order_id, status }` ⚠ simulation only |
| GET  | `/api/brief` | — | `{ captured_at, signals, markdown }` |
| POST | `/api/lock` | `{}` | 204 (clears session) |

For a Streamlit-only deployment these can stay as Python function calls in `app/api.py` — the contract just makes the interaction surface explicit. If you later split frontend out, this list becomes the FastAPI router.

## 9. Critical constraints (do not regress)

1. **GlobalActionBar is the single source of truth** for refresh / run / auth state. Don't duplicate these controls inside individual tabs.
2. **Tabular-nums everywhere a number lives.** Without it, the `18.59%` in row N+1 misaligns with the `5.20%` in row N.
3. **No Streamlit-red `#FF4B4B`.** We use `#E84040` for bear, `#FF0000` only for hard stop_loss.
4. **Status colors are reserved.** Don't tint green to mean "active" — green = bullish. Use accent blue for "active/selected".
5. **T+1 rules enforced at engine layer**, not UI. Sell suggestions for `bought_today` lots are computed-out by `engine.rebalance`, not just hidden in the UI.
6. **Never read holdings before `ss.unlocked == True`** — auth gate sits before any `engine.*` import that touches user data.
7. **Card padding 12px**, not Streamlit's default 1rem. Override globally via injected CSS.

## 10. Files in this folder

| File | Phase | Contents |
|---|---|---|
| `index.html` | P5 | Entry point — 8 sections / artboards. Load in browser |
| `design-canvas.jsx` | foundation | Pan/zoom canvas wrapper (design-tool, do not port) |
| `design-system.jsx` | P0 | Token + component spec sheet — start here |
| `global-action-bar.jsx` | **P1** | GlobalActionBar with 6 documented states |
| `tab1-holdings-v2.jsx` | **P2** | Tab 1 v3 — inline editable table + T+1 column |
| `tab2-brief-v2.jsx` | **P3** | Tab 2 v3 — T+1 rebalance summary bar |
| `tab3-stock-depth.jsx` | carry-over | Tab 3 — legacy internal tab bar (TODO: GAB) |
| `tab4-signals.jsx` | carry-over | Tab 4 — legacy internal tab bar (TODO: GAB) |
| `tab5-rebalance.jsx` | **P4** | Tab 5 — analysis cards + K-line + chip distribution + operation list |
| `holdings-editor.jsx` | retired | sidebar holdings editor — superseded by Tab 1 inline table |
| `holdings-editor-auth.jsx` | partial | login form spec — re-host as full-screen modal (§6.6) |
| `tab1-holdings.jsx` | retired | original Tab 1 — kept as reference, not rendered in v3 |
| `tab2-brief.jsx` | retired | original Tab 2 — kept as reference, not rendered in v3 |

## 11. Suggested phase plan for Claude Code

| Phase | Scope | Effort |
|---|---|---|
| **P1** | Scaffold + tokens + auth gate · GlobalActionBar (HTML component) | 3-4 h |
| **P2** | Tab 1 持仓总览 — KPIs, donut, treemap, inline editable table with T+1 column. Wire `engine/portfolio.py::check_portfolio_balance()` | 5-7 h |
| **P3** | T+1 lot tracker (`engine/lots.py` + SQLite schema + status helpers) | 2-3 h |
| **P4** | Tab 2 每日简报 — macro banner, brief expanders, score table, T+1 rebalance summary bar | 4-5 h |
| **P5** | Tab 5 调仓分析 — selector, analysis cards, K-line, **chip distribution**, operation list. Wire `engine/rebalance.py` (T+1-aware) | 6-8 h |
| **P6** | Tab 4 信号仪表盘 — macro traffic light, scarcity matrix, gauges, history. Replace internal tab bar with GAB | 4-5 h |
| **P7** | Tab 3 个股深度 — 4-pane chart, fundamental card, news timeline. Replace internal tab bar with GAB | 5-7 h |
| **P8** | Polish · URL `?tab=N` state · auto-refresh · cross-tab nav · responsive padding | 2-3 h |

Total ≈ 31-42 hours.

---

*This handoff was generated from a hi-fi React prototype. The visual spec is authoritative; the Streamlit recipes are suggestions — choose Streamlit primitives where they fit, custom HTML/CSS where they don't.*
