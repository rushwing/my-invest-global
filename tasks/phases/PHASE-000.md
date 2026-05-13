---
phase_id: phase-0
title: 平台工程与脚手架
status: draft
priority: P0
---

## Goal

建立项目基础设施：目录结构、uv 环境配置、Pydantic schema 定义、环境变量管理、以及供 Codex agent 使用的 CLAUDE.md 工作空间入口。确保后续所有 Phase 的代码可以在统一规范下运行和测试。

## In Scope

- 项目目录结构与 `.gitkeep` 占位文件（`engine/`, `app/`, `data/agent_input/`, `data/processed/`, `data/cache/`, `tests/`）
- `.env.example`：包含所有配置项注释（`ANTHROPIC_API_KEY`, `AKSHARE_TOKEN`, `DATA_DIR`, `LOG_LEVEL`）
- `engine/config.py`：pydantic-settings `Settings` 类，从 `.env` 加载配置
- `engine/schemas/`：Pydantic v2 schema 定义
  - `agent_input.py`：`DailyNewsItem`, `DailyNewsFile`, `WeeklyReportFile`, `KolDigestFile`, `HoldingsRow`
  - `signals.py`：`StockSignal`, `PortfolioSummary`, `SignalsFile`
- `engine/__init__.py`、`app/__init__.py` 空文件
- `scripts/validate_input.py`：读取 `data/agent_input/` 中的 JSON/CSV，用 Pydantic schema 校验，输出错误报告
- `CLAUDE.md`：供 Codex agent 或 Claude Code 理解项目结构的入口文档（指向 docs/project-scope.md 和 docs/adr/）
- 确认 `uv sync` 可成功安装所有依赖（pyproject.toml 已存在）

## Out of Scope

- 业务逻辑实现（属于 PHASE-001 及以上）
- DuckDB 初始化（属于 PHASE-001）
- Streamlit 应用（属于 PHASE-007）

## Exit Criteria

- `uv run python -c "from engine.config import Settings; s = Settings(); print(s)"` 无报错
- `uv run python -c "from engine.schemas.agent_input import DailyNewsFile"` 无报错
- `uv run python scripts/validate_input.py` 对空 `data/agent_input/` 目录无崩溃，输出 "No input files found"
- `uv run pytest tests/` 对空测试套件通过（exit code 0）
- `.env.example` 包含所有 `Settings` 中引用的环境变量

## Dependencies

无（横切基础设施，无前置业务 phase）

## Notes

Pydantic schema 是 agent 接口契约的代码化表达，需严格对应 ADR-002 中定义的 JSON/CSV schema。`HoldingsRow` 的 `pnl_pct` 字段存储为 float（去掉百分号），Codex agent 写入时可带 "+" 或 "%" 前缀，由 schema 的 validator 做解析。
