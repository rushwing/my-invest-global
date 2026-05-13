---
phase_id: phase-7
title: Streamlit 仪表盘
status: draft
priority: P1
---

## Goal

实现 Streamlit 四 Tab 仪表盘，可视化展示持仓总览、每日策略简报、个股深度技术图和信号仪表盘。支持 watchdog 文件变化自动触发数据刷新，Plotly 3 子图实现 MACD/RSI/布林带技术图。

## In Scope

- `app/dashboard.py`：主入口（`streamlit run app/dashboard.py`），`main()` 注册到 `pyproject.toml` 的 `advisor` 脚本
- `app/components/`：各 Tab 的组件模块
  - `tab1_overview.py`：持仓总览
    - 左栏：Plotly 饼图（白马 vs 弹性，当前 vs 目标）
    - 右栏：Plotly Treemap（持仓盈亏热力图，颜色=盈亏%，面积=市值）
    - 底部：`st.dataframe` 仓位偏差表（代码 / 名称 / 类别 / 市值 / 占比 / 目标占比 / 偏差 / 建议）
  - `tab2_brief.py`：每日策略简报
    - 顶部卡片组：隔夜美股先行指标（NVDA/AVGO/VRT/ANET/MU 涨跌色标）
    - 中部：`st.dataframe` 综合信号评分表（分数色阶：≥75 红 / 60–74 琥珀 / 40–59 灰 / <40 蓝）
    - 底部：`st.markdown` 渲染 `recommendations_{date}.md`
  - `tab3_stock.py`：个股深度
    - 下拉选择持仓标的
    - Plotly 3 子图（`make_subplots(rows=3, shared_xaxes=True, row_heights=[0.5, 0.25, 0.25])`）：
      - 上：K 线（Candlestick）+ 布林带（Scatter）+ 成交量（Bar）
      - 中：MACD 快线/慢线（Scatter）+ MACD 柱状图（Bar）
      - 下：RSI 曲线（Scatter）+ 超买超卖水平线（shape）
    - 左栏（35%）：基本面摘要卡片（紧缺度 / 目标价 / 行业排名 / Q1 财报）
    - 右栏（65%）：相关新闻 feed（来自 DuckDB news_items，按时间倒序，情绪色标）
  - `tab4_signals.py`：信号仪表盘
    - 左栏：宏观 CapEx 周期状态卡片（Green/Yellow/Red 颜色指示）+ 手动覆盖按钮
    - 右栏：板块紧缺度矩阵表（Tier-1 橙 / Tier-2 琥珀 / Tier-3 灰 / Tier-4 蓝）
    - 底部：白马/弹性仓位建议图（当前 vs 目标，含动态调整区间）
- `app/state.py`：
  - 使用 `st.session_state` 管理：选中日期、选中标的、宏观状态
  - `load_latest_data(date: str) -> dict`：从 DuckDB 加载当日数据，缓存（`@st.cache_data(ttl=60)`）
- 侧边栏：日期选择（`st.date_input`，默认今日）/ 宏观状态显示 / 手动刷新按钮 / 数据最后更新时间

## Out of Scope

- 实时 tick 行情（每日批量场景不需要）
- 用户认证（个人本地使用）
- 移动端适配（桌面浏览器优先）
- `streamlit_autorefresh`（使用手动刷新按钮替代，避免不必要的 DuckDB 读取）

## Exit Criteria

- `uv run advisor`（或 `uv run streamlit run app/dashboard.py`）启动无报错
- Tab 1 在有测试 holdings 数据时显示饼图 + Treemap + 偏差表（不空白）
- Tab 2 在有 `recommendations_{date}.md` 时正确渲染 Markdown
- Tab 3 在选择 "300308" 时显示 Plotly 3 子图，MACD/RSI/布林带数据正确
- Tab 4 在宏观状态 = Green 时显示绿色指示器，切换覆盖后状态持久化到 `data/cache/macro_state.json`
- 刷新按钮触发后数据在 ≤5 秒内更新（本地 DuckDB 查询）

## Dependencies

phase-5（`signals_{date}.json` 输出）；phase-6（`recommendations_{date}.md` 输出）；phase-2（price_history 表供 Tab 3 使用）；phase-3（fundamental_loader 供 Tab 3 基本面卡片使用）

## Notes

Tab 3 的 Plotly 图使用 `use_container_width=True` 适应侧边栏折叠时的宽度变化。布林带用半透明填充（`fill='tonexty'`）而非两条实线，视觉更清晰。新闻 feed 的情绪色标用 `st.markdown` 的 HTML 行内样式（green/red/gray），不依赖外部 CSS。
