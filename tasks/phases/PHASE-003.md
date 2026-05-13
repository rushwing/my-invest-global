---
phase_id: phase-3
title: 基本面信号引擎
status: draft
priority: P0
---

## Goal

实现 Signal B（基本面），权重 40%。从静态研报数据（`data_china_aidc.md`）加载各标的的紧缺度、目标价、Q1 财报和行业排名信息，计算基本面评分，并触发目标价超越告警和止损告警。

## In Scope

- `engine/data/fundamental_loader.py`：
  - 解析 `data_china_aidc.md` Markdown 表格 → 结构化 dict（在模块加载时执行一次，结果缓存在内存）
  - 提取字段：`code`, `name`, `scarcity_tier` (1–4), `target_price`, `target_price_stale` (bool), `sector_rank`, `q1_revenue_growth`, `q1_profit_growth`, `sector`, `listing_status`
  - **目标价陈旧检测**：解析"投研目标股价"列时，若值包含 `[待更新]` 标记 → 提取数字并将 `target_price_stale=True`；解析时使用 `DataProvenance(source=broker, confidence=DataConfidence.STALE)` 附加到返回结构
  - `listing_status` 来自"股票代码"列：非六位数字（如 "未上市"）→ `ListingStatus.UNLISTED`；六位数字 → `ListingStatus.TRADEABLE`
  - 若文件格式变化导致解析失败，抛出明确异常（不静默返回空）
- `engine/signals/fundamental.py`：
  - `compute_fundamental_score(code: str, current_price: float, cost_price: float) -> dict`
  - 因子计算：
    - 紧缺度：Tier-1=25, Tier-2=18, Tier-3=10, Tier-4=3
    - 目标价上行空间：`(target - current) / current * 100`，上限 30 分；若 `current > target` → 得 0 分 + 触发 `take_profit_alert`
    - Q1 超预期：`revenue_growth * 0.3 + profit_growth * 0.7`，归一化到 0–25
    - 行业排名：#1=20, #2=13, #3=7, 其他=2
  - 特殊覆盖：若 `category="弹性股"` 且 `(cost_price - current_price) / cost_price > 0.20` → `action_code="stop_loss"`，覆盖综合分
  - 返回结构：`{"fundamental_score": int, "factors": {...}, "take_profit_alert": bool, "stop_loss": bool}`
- `tests/test_fundamental.py`：覆盖各 Tier 得分、目标价超越情况、止损触发、解析器对 data_china_aidc.md 实际内容的集成测试

## Out of Scope

- 实时财报数据拉取（使用静态研报数据，季度人工更新）
- 美股基本面（不在 A 股持仓范围内）
- 机构目标价历史跟踪

## Exit Criteria

- `uv run python -c "from engine.data.fundamental_loader import load_fundamentals; d = load_fundamentals(); print(len(d), 'stocks loaded')"` 输出 ≥20（研报中 A 股数量）
- `uv run pytest tests/test_fundamental.py -v` 全部通过，覆盖：Tier-1 标的满分 25、现价超目标价时得 0 且触发 alert、弹性股亏损 >20% 触发 stop_loss
- 基本面分在 0–100 范围内

## Dependencies

phase-0（schema 定义、Settings）；`data_china_aidc.md` 需存在于项目根目录

## Notes

`data_china_aidc.md` 是静态文件，人工季度更新。解析器应容忍表格中的空格和中文标点差异（如"---"分隔行）。`q1_revenue_growth` 和 `q1_profit_growth` 存储为浮点（如 1.92 代表 +192% YoY）。若某标的不在研报数据中（持仓中的新增股票），基本面分降级为 0 并在日志中警告。
