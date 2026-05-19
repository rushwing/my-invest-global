---
phase_id: phase-11
title: 筹码分析
status: req_review
priority: P2
---

## Goal

对持仓标的实现筹码成本分布分析，辅助判断当前价格与市场平均持仓成本的相对位置、
获利盘比例、筹码密集区形成的压力/支撑位，以及资金集中度。

数据来源支持两条路径：
- **主路径**：akshare `stock_cyq_em` API → DuckDB 持久化
- **备用路径**：同花顺 App 截图 → Claude Vision OCR 解析

## In Scope

### Track 11a — 数据采集层（REQ-036）

- `engine/agent/chip_fetcher.py` — akshare 筹码数据采集
- DuckDB 两张新表：`chip_distribution`（逐价格档位）、`chip_summary`（每日汇总指标）
- 存储层扩展 `engine/data_agent/storage.py`

### Track 11b — 分析引擎（REQ-037）

- `engine/agent/chip_analysis.py` — ChipAnalysis Pydantic model + 信号判断
- 关键信号：价格相对90%筹码上界、平均成本偏离率、筹码集中度等级

### Track 11c — 截图OCR解析（REQ-038）

- `engine/agent/chip_screenshot_parser.py` — Claude Vision API 解析同花顺截图
- 与 Track 11b 共享 ChipAnalysis 输出模型（两条路径归一）

### Track 11d — 仪表盘集成（REQ-039）

- `app/pages/chip_panel.py` — Streamlit 筹码面板组件
- Plotly 水平筹码直方图 + 当前价格/平均成本标注线
- ChipSummaryCard：获利比例、平均成本、区间、集中度等级

## Out of Scope

- Level-2 实时 tick 筹码（仅日频 akshare 数据）
- 多股票筹码对比视图
- 历史筹码演变动画
- Bloomberg/Wind 付费数据源

## Exit Criteria

- `fetch_chip_summary('688143')` 返回含 `avg_cost`/`profitable_pct`/`concentration` 的 Pydantic model
- `analyze_chip('688143', current_price=131.60)` 返回 `ChipAnalysis` 含 `above_90_band: bool`
- `parse_chip_screenshot(image_path)` 对图4截图返回与 akshare 路径格式一致的 `ChipAnalysis`
- Tab 3 筹码面板展示水平直方图，当前价格线正确标注

## Dependencies

- PHASE-010 完成（REQ-032..035 已 merge）
- PHASE-007 Tab 3（REQ-018）— REQ-039 可先作为独立 Streamlit 页发布，待 Tab 3 实现后集成
- 环境变量：`ANTHROPIC_API_KEY`（REQ-038 Claude Vision）
