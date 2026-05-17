---
phase_id: phase-7
title: Streamlit 仪表盘
status: draft
priority: P1
branch: feat/PHASE-007-dashboard
design_handoff: docs/design/dashboard/design_handoff_dashboard/
---

## Goal

实现 Streamlit 四 Tab 仪表盘，可视化展示持仓总览、每日策略简报、个股深度技术图和信号仪表盘。包含：本地口令认证门控（bcrypt + session_state）、可收起侧边栏持仓编辑器（st.data_editor + CSV导入）、watchdog 文件变化自动刷新、Plotly 4 子图技术图（price+BB / volume / MACD / RSI）。高保真设计稿见 `docs/design/dashboard/design_handoff_dashboard/`。

## Design Handoff

| 文件 | 内容 |
|---|---|
| `design-system.jsx` | TOKENS / SIGNAL enum / 可复用组件（KPICard, SignalBadge, Tag, TableRow, HeatCell） |
| `tab1-holdings.jsx` | Tab 1 持仓总览：AllocationDonut / HoldingsHeatmap / DeviationTable / KPIRow |
| `tab2-brief.jsx` | Tab 2 每日策略简报：MacroBanner / StrategyBrief / ScoreTable / USLeadingChart / MappingPanel |
| `tab3-stock-depth.jsx` | Tab 3 个股深度分析：TripleChart (4-pane SVG) / FundamentalCard / NewsTimeline |
| `tab4-signals.jsx` | Tab 4 信号仪表盘：MacroCyclePanel / ScarcityMatrix / Gauge / RebalanceTriggers / HistoryTimeline |
| `holdings-editor.jsx` | 侧边栏持仓编辑器（收起56px轨 + 展开420px面板） |
| `holdings-editor-auth.jsx` | 认证流程 5 Artboard 状态图（locked/login/error/unlocked/collapsed-unlocked） |
| `README.md` | 设计规范、约束、P1–P7 实现计划 |

**实现约束（pixel-perfect 匹配设计）：**
- 所有数字 span 必须使用 `tabular-nums` + JetBrains Mono
- 卡片 padding：12px（覆盖 Streamlit 默认值）
- 颜色 token：bg=#0E1117, surface=#1C1C2E, accent=#4F8EF7, bull=#00C47A, neutral=#F5A623, bear=#E84040

## In Scope

### 认证与侧边栏（REQ-014, REQ-015）
- 本地口令认证门控：`.env` 存 bcrypt hash，session_state["unlocked"] 控制主区域可见性
- 收起态（56px）：头像圆圈（initials "W"）+ 状态指示（绿点=已解锁 / 锁图标=未解锁）+ 脏数据指示点
- 展开态（420px）：状态栏（快照日期 + 来源徽章 + 保存/撤销）+ CSV导入 dropzone + 可编辑表格 + 汇总栏
- 可编辑列：code, name, category（白马股/弹性股下拉）, cost_price, current_price, quantity, market_value（只读，自动=price×qty）
- 保存：写入 `data/agent_input/cn/holdings_{YYYYMMDD}.csv` → st.rerun()

### Tab 1 持仓总览（REQ-016）
- 页头：日期 + 市场状态指示 + 总市值 + 总盈亏
- AllocationDonut：px.pie() 环形图 + 内圈文字 + 偏差徽章（bull/neutral/bear）
- KPI 行：3 卡片（白马MV, 弹性MV, 最大单一弹性占比，>8% 显示红色）
- HoldingsHeatmap：px.treemap()，颜色=盈亏%（bear→bull），标签=name+code+pnl%
- DeviationTable：st.dataframe，|dev|>5% 黄色行 / >10% 红色行，按|偏差|降序排列

### Tab 2 每日策略简报（REQ-017）
- MacroBanner：宏观状态 pill + CapEx 描述 + NVDA/AVGO/VRT/ANET/MU 隔夜涨跌 chip
- StrategyBrief：3 个 st.expander（市场判断 / 个股操作 / 风险提示），风险区用 AlertBox（danger/warn/info）
- ScoreTable：st.column_config.ProgressColumn 进度条（A/B/C 列）+ 综合分数着色 + stop_loss 行红色
- USLeadingChart：px.bar() 水平双向柱（center=0）+ 3 条摘要统计
- MappingPanel：美→中板块映射表，预期回报区间着色

### Tab 3 个股深度分析（REQ-018）
- 股票选择工具栏：st.selectbox + 快速切换按钮 + 日期范围单选（1M/3M/6M/1Y）
- Plotly 4 子图：make_subplots(rows=4, shared_xaxes=True)
  - row1：价格 + BB(20,2σ) + MA13W
  - row2：成交量柱状图
  - row3：MACD 柱 + 快/慢线 + 金叉/死叉标记（绿/红圆圈）
  - row4：RSI(14) + 超买/超卖阴影区
- FundamentalCard：Tier 徽章 + 价格块（现价/目标/上涨空间）+ 指标网格 + 机构评级堆叠柱
- NewsTimeline：情绪点 + 相关度条 + 来源标签，最多 8 条
- 指标读数条：MA20, MA13W, MACD, RSI(14) 最新值

### Tab 4 信号仪表盘（REQ-019）
- MacroCyclePanel：3 态交通灯（激活态发光）+ Big-4 云 CapEx 表（MSFT/AMZN/GOOG/META YoY）
- ScarcityMatrix：4 列 st.columns，Tier 1–4；股票 chip 按 composite_score 着色（≥70 绿/50-70 黄/<50 红）；◉ = 持有 / ⚠ = 警告
- RebalanceTriggers：白马/弹性仓位半圆仪表盘（±5% 着色，±10% 触发）+ 7 触发器状态表
- HistoryTimeline：st.dataframe 按日期降序 + Plotly scatter 可视化时间线（可选）
- 手动宏观覆盖按钮：调用 set_macro_state_override()

### 基础设施（REQ-013, REQ-020）
- `app/dashboard.py`：认证门控 → 渲染侧边栏 → 路由 4 个 Tab
- `app/data_loader.py`：load_latest_holdings / load_latest_signals / load_recommendations / load_news_for_ticker / load_ohlcv（@st.cache_data(ttl=300)）
- REQ-013 全局 CSS 层：通过 st.markdown(unsafe_allow_html=True) 注入设计 token + Google Fonts

## Out of Scope

- 实时 tick 行情（每日批量场景不需要）
- 多用户认证或远程部署（单用户本地口令在范围内）
- 移动端适配（桌面浏览器优先）
- `streamlit_autorefresh`（使用 watchdog + st.rerun() 替代）

## Exit Criteria

- `uv run streamlit run app/dashboard.py` 启动无报错，显示登录表单
- 正确口令 → 侧边栏解锁，4 个 Tab 无错误渲染
- 侧边栏编辑持仓并保存 → Tab 1 Treemap 在下一次 rerun 反映新市值
- Tab 3 选择 "300308" → RSI 线在 [0,100] 内，BB upper > mid > lower
- Tab 4 宏观状态 = GREEN → 弹性仓位仪表盘目标显示 38%；切换为 RED → 显示 20%
- `uv run pytest tests/test_dashboard*.py -v` 所有集成测试通过

## Dependencies

- REQ-001（MacroState enum）
- REQ-004（run_daily_pipeline）
- REQ-006 / REQ-007（MacroStorage）
- phase-5（signals_{date}.json 输出）
- phase-6（recommendations_{date}.md 输出）
- phase-2（price_history 表供 Tab 3 使用）
- phase-3（fundamental_loader 供 Tab 3 基本面卡片使用）

## REQ Breakdown

| REQ | 标题 | 优先级 | 状态 |
|---|---|---|---|
| REQ-013 | Design System + 全局 CSS 层 | P1 | draft |
| REQ-014 | 本地口令认证门控 | P1 | draft |
| REQ-015 | 持仓编辑侧边栏 | P1 | draft |
| REQ-016 | Tab 1 持仓总览 | P1 | draft |
| REQ-017 | Tab 2 每日策略简报 | P1 | draft |
| REQ-018 | Tab 3 个股深度分析 | P2 | draft |
| REQ-019 | Tab 4 信号仪表盘 | P2 | draft |
| REQ-020 | 集成与数据接线 | P1 | draft |

## Branch Strategy

所有 REQ-013–020 在分支 `feat/PHASE-007-dashboard` 上工作。不得合并或 rebase 到 `feat/REQ-008`、`feat/REQ-009`、`feat/REQ-010`、`feat/REQ-011`、`feat/REQ-012`。PHASE-007 全部 REQ 达到 pr_draft 后，提交单一 PR。

## Notes

- Tab 3 Plotly 图使用 `use_container_width=True`，适应侧边栏折叠时的宽度变化
- 布林带：半透明填充（`fill='tonexty'`），视觉更清晰
- scoreColor 阈值：≥75=bull, ≥60=accent, ≥40=textMuted, <40=bear（实现使用 40 而非设计稿中的 45）
- LLM 归因：`claude-sonnet-4-6`（设计稿误写为 GPT-4，实现中纠正）
- cloud CapEx 列名：fy2025 / fy2026_est（设计稿用 q4_25/q1_26，实现中规范化）
