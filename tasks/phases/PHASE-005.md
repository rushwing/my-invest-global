---
phase_id: phase-5
title: 仓位框架与信号融合
status: draft
priority: P0
---

## Goal

实现 2/3 白马 + 1/3 弹性仓位框架校验，融合三信号为综合评分，应用宏观门控和特殊覆盖规则，生成每日 `signals_{date}.json` 输出文件。这是分析引擎的总调度层。

## In Scope

- `engine/portfolio/framework.py`：
  - `check_portfolio_balance(holdings_df: pd.DataFrame, macro_state: str) -> dict`
  - 宏观门控目标：Green=0.38, Yellow=0.33, Red=0.20（弹性股目标权重）
  - 触发条件：`|current_ratio - target_ratio| > 0.10`
  - 返回：`{"rebalance_needed": bool, "direction": str, "deviation": float, "target_elastic": float}`
  - 单只弹性股市值超 10% 总仓位 → 单独触发 `position_too_large` 提示
- `engine/portfolio/macro_gate.py`：
  - `MacroState` 枚举：`GREEN / YELLOW / RED`
  - `get_macro_state(capex_signals: list[dict]) -> MacroState`：基于 CapEx 指引变化计算（初版：从 weekly_report 的 macro 类别新闻中解析；人工可覆盖）
  - 提供手动覆盖接口：`set_macro_state_override(state: MacroState)`（写入本地 `data/cache/macro_state.json`）
- `engine/runner.py`：
  - `run_daily_pipeline(date: str) -> SignalsFile`
  - 调度顺序：
    1. 加载当日 holdings（从 DuckDB）
    2. 对每只持仓股并行（`ThreadPoolExecutor`）计算 Signal A + B + C
    3. 融合：`composite = A * 0.30 + B * 0.40 + C * 0.30`
    4. 映射 action_code（≥75 → strong_add，60–74 → hold_add，40–59 → hold，<40 → reduce）
    5. 应用特殊覆盖（stop_loss / take_profit_alert / macro_red 降级）
    6. 调用 `check_portfolio_balance()`
    7. 写入 `data/processed/signals_{date}.json`（符合 ADR-002 的 `SignalsFile` schema）
  - `scripts/run_pipeline.py`：命令行入口，`uv run python scripts/run_pipeline.py --date 2026-05-13`
- `tests/test_runner.py`：端到端集成测试，使用完整 fixture（holdings + news + price），验证输出 JSON 结构和 action_code 正确性

## Out of Scope

- Claude API 调用（属于 PHASE-006）
- Streamlit 展示（属于 PHASE-007）
- 实际交易执行（永不实现）

## Exit Criteria

- `uv run python scripts/run_pipeline.py --date 2026-05-13` 对测试 fixture 输出有效 `signals_20260513.json`
- 输出 JSON 通过 `SignalsFile` Pydantic schema 校验
- `uv run pytest tests/test_runner.py -v` 全部通过，覆盖：normal path、stop_loss override、macro Red 降级、portfolio rebalance 触发
- `check_portfolio_balance` 在弹性股比例 = 43% 时正确触发 `reduce_elastic` 提示

## Dependencies

phase-2（技术信号）；phase-3（基本面信号）；phase-4（情绪信号）

## Notes

`run_daily_pipeline` 是幂等的：同一日期重复运行会覆盖输出文件，不报错。宏观门控初版使用手动覆盖（用户运行 `python -m engine.portfolio.macro_gate --set green`），自动从新闻解析 CapEx 信号是后续优化项。ThreadPoolExecutor 并行计算各股票信号时，限制最大并发为 5，避免 AkShare 触发频率限制。
