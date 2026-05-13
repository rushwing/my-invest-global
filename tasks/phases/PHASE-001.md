---
phase_id: phase-1
title: 数据管道基础
status: draft
priority: P0
---

## Goal

建立数据摄取管道：DuckDB 数据库 schema 初始化、agent_input 文件的 watchdog 监听触发器、结构化入库流程，以及历史文件回放能力（用于离线调试和回测）。

## In Scope

- `engine/db.py`：DuckDB 连接管理（单例），数据库文件路径从 `Settings.DATA_DIR` 读取
- DuckDB schema 初始化脚本（在 `engine/db.py` 的 `init_schema()` 中）：
  - `news_items` 表：对应 `DailyNewsItem` schema，主键 `(id)`
  - `holdings` 表：对应 `HoldingsRow`，主键 `(date, code)`
  - `weekly_reports` 表：存储 `industry_reports` + `kol_digests`
  - `price_history` 表：`(code, date, open, high, low, close, volume)`，主键 `(code, date)`
  - `signals` 表：对应 `StockSignal`，主键 `(date, code)`
- `engine/ingest/`：
  - `watcher.py`：watchdog `Observer` + `FileSystemEventHandler`，监听 `data/agent_input/`，新文件触发对应 ingestor
  - `news_ingestor.py`：解析 `daily_news_*.json` → 校验 → upsert `news_items`
  - `holdings_ingestor.py`：解析 `holdings_*.csv` → 校验 → upsert `holdings`
  - `weekly_ingestor.py`：解析 `weekly_report_*.json` → upsert `weekly_reports`
- `scripts/replay_input.py`：将指定日期的历史文件手动触发入库（绕过 watchdog，用于调试）
- `tests/test_ingest.py`：用测试 fixture JSON/CSV 覆盖各 ingestor 的正常路径和 schema 错误路径

## Out of Scope

- 价格数据拉取（属于 PHASE-002）
- 信号计算（属于 PHASE-002 ～ PHASE-004）
- 宏观门控状态（属于 PHASE-005）

## Exit Criteria

- `uv run python -c "from engine.db import init_schema; init_schema()"` 无报错，DuckDB 文件创建成功
- `uv run python scripts/replay_input.py --date 2026-05-13` 对 `tests/fixtures/` 中的测试文件入库无报错
- `uv run pytest tests/test_ingest.py -v` 全部通过
- `uv run python -m engine.ingest.watcher` 启动无报错，创建测试文件后日志显示触发成功

## Dependencies

phase-0（Settings 配置、Pydantic schema、目录结构）

## Notes

DuckDB 用单文件模式（`data/cache/advisor.duckdb`），不需要服务器进程。watchdog 轮询延迟约 1 秒，对每日批量场景完全够用。`replay_input.py` 是核心调试工具，应支持 `--date` 参数和 `--file` 参数两种模式。
