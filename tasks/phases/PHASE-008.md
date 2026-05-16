---
phase_id: phase-8
title: 宏观指标 Agent
status: draft
priority: P1
---

## Goal

构建独立的宏观指标采集 Agent（`engine/macro_agent/`），自动化驱动 ADR-003
"宏观 CapEx 门控"，替代当前人工维护的 `data/cache/macro_state.json`。
Agent 覆盖 `docs/macro-market-indicator-matrix.md` 中 Groups I–O 的全部
30+ 指标，并通过 MCP 工具层（ADR-006 Phase 7）向 LangGraph ReAct Agent 暴露
宏观查询接口。

## In Scope

### Track 8a — 基础层（REQ-006, REQ-007）

- `engine/shared/sources/` — 宏观专用 source 模块（FRED、SEC EDGAR、
  Yahoo Global、Alpha Vantage、AKShare 宏观子集、Tushare 宏观子集）
- `engine/macro_agent/storage.py` — 4 张 DuckDB 新表（macro_indicators、
  capex_quarterly、fomc_calendar、macro_regime），遵循 ADR-007 DDL

### Track 8b — 采集层（REQ-008, REQ-009）

- `engine/macro_agent/update_class.py` — UpdateClass 八级枚举
- `engine/macro_agent/indicator_groups.py` — IndicatorGroup 枚举（I–O）+ SourcePolicy
- `engine/macro_agent/scheduler.py` — MacroScheduler（时区感知 + BLS/NBS 发布日历驱动）
- `engine/macro_agent/orchestrator.py` — MacroOrchestrator（主循环 + UpdateClass 分发）
- `scripts/refresh_macro_agent.py` — CLI 入口（`uv run refresh-macro-agent`）
- Groups I（宏观经济）、J（大宗商品）、K（美国关键指数/权益）采集实现

### Track 8c — 高级指标（REQ-010, REQ-011）

- Group L（云巨头 CapEx）：SEC EDGAR 10-Q/10-K + 单季反算 + 哈希去重
- Group M（亚太半导体）：Yahoo Finance 全球指数 + KRX 备用
- Group N（中国市场）：AKShare SGX A50/科创50 (000688.SH)/成交额 + Sina FX
- Group O（地缘政治/新闻）：CLS 电报 + Alpha Vantage 新闻情绪（预算门控）
- `engine/macro_agent/regime.py` — MacroRegime 门控计算（STALE 守卫 + 三色输出）

### Track 8d — 封装层（REQ-012）

- `engine/mcp/macro_tools.py` — 6 个 MCP 工具（Pydantic 输出校验）
- `regime.py` 自动写入 `data/cache/macro_state.json`（手动覆盖保留为逃生口）
- 集成 ADR-006 `[stale]` 标志链到 `FrozenMarketSnapshot`

## Out of Scope

- A 股股票层面指标（属于 stock-data-agent / PHASE-001）
- GDELT 实时流处理（仅关键词轮询，见 Group O 备注）
- Bloomberg Terminal / Wind 付费数据接入
- 宏观指标的回测框架（Advisory 定位，仅前向）
- Alpha Vantage 付费升级（25 req/day 免费层在 advisory 场景已足够）

## Exit Criteria

- `uv run refresh-macro-agent --once --groups I,K` 不报错，DuckDB 中
  `macro_indicators` 表存在联邦基金利率和 SOX 数据行
- `uv run refresh-macro-agent --once --groups L` 在有效 SEC EDGAR 响应时
  写入至少 1 行 `capex_quarterly`；`capex_usd` 为单季正值
- `uv run pytest tests/test_macro_agent/ -v` 全部通过（≥20 个场景）
- `engine/mcp/macro_tools.py` 中 `get_macro_state()` 返回符合 Pydantic 模型
  的 dict；STALE 字段在数据超龄时正确为 `"stale"`
- `data/cache/macro_state.json` 在 `regime.py` 计算后自动更新；手动写入该
  文件仍可覆盖（逃生口）

## Dependencies

- PHASE-001（DuckDB 存储模式、`_find_project_root()`、`AbstractSource` 基类）
- ADR-006 Phase 7（MCP Server 层框架，macro_tools.py 注册至同一 MCP 服务）
- `docs/macro-market-indicator-matrix.md`（权威数据源文档）
- 环境变量：`TUSHARE_TOKEN`（REQ-008 Tushare 宏观函数）、`FRED_API_KEY`（REQ-006 FRED）、
  `ALPHA_VANTAGE_KEY`（REQ-011 新闻情绪）

## Notes

Track 8a/8b 可并行开发（无内部依赖）。Track 8c 依赖 Track 8a（需 storage.py
中的表结构）。Track 8d 依赖 Track 8c（regime.py 需要全部指标数据落地）。

CapEx 单季反算逻辑是高风险实现点，REQ-010 要求独立验证测试（fixture 使用
已知的 MSFT 历史 10-Q 数据）。

UpdateClass `MONTHLY_FIXED` 的触发精度依赖 `release_calendar.py` 预填充
是否成功；若 BLS/NBS 日历解析失败，调度器应回退为每日轮询（安全降级）。
