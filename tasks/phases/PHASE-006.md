---
phase_id: phase-6
title: Claude API 合成层
status: draft
priority: P1
---

## Goal

将三信号评分结果和当日持仓数据通过 Claude API（claude-sonnet-4-6）合成为自然语言策略简报，控制 token 预算在 4000 tokens/天以内，输出 Markdown 文件至 `data/processed/recommendations_{date}.md`。

## In Scope

- `engine/synthesis/prompt_builder.py`：
  - `build_prompt(signals_file: SignalsFile, holdings_df: pd.DataFrame, news_items: list[DailyNewsItem]) -> str`
  - Prompt 结构（严格控制 ≤3000 tokens）：
    - 系统角色：AI 基建股策略顾问，Markdown 输出，中文，简洁专业
    - 持仓概况（总市值 / 白马比例 / 弹性比例 / 再平衡状态）
    - 各标的评分摘要（逐行：代码 | 名称 | 综合分 | 技术/基本面/情绪分 | 建议）
    - 今日关键信息（隔夜美股涨跌 + 前 3 条相关新闻 + KOL 摘要）
    - 输出要求（3 节：市场判断 / 逐标的操作建议 / 风险提示）
  - Token 估算：使用字符数启发式（中文每字约 1.5 tokens），超限时截断新闻条数
- `engine/synthesis/synthesizer.py`：
  - `generate_brief(date: str) -> str`：
    1. 读取 `signals_{date}.json` 和当日 holdings、news
    2. 调用 `build_prompt()`
    3. 调用 `anthropic.Anthropic().messages.create(model="claude-sonnet-4-6", max_tokens=800, ...)`
    4. 写入 `data/processed/recommendations_{date}.md`
    5. 写入 token 使用记录至 DuckDB `api_usage` 表（date, input_tokens, output_tokens, model）
  - 错误处理：API 超时或速率限制 → 指数退避重试 3 次；最终失败 → 写入占位 Markdown（"今日简报生成失败，请手动运行"）
- `engine/synthesis/token_tracker.py`：
  - DuckDB `api_usage` 表管理，提供月度用量查询函数
- `tests/test_prompt_builder.py`：验证 prompt 长度估算、关键信息截断逻辑（不依赖真实 API 调用）

## Out of Scope

- 流式输出（batch daily 场景无需 SSE）
- 对话式交互（工具定位是批量建议，非聊天）
- 多模型对比（固定使用 claude-sonnet-4-6）

## Exit Criteria

- `uv run python -c "from engine.synthesis.prompt_builder import build_prompt; ..."` 生成的 prompt 字符数 ≤ 6000（对应约 3000 tokens 估算）
- `uv run python scripts/run_pipeline.py --date 2026-05-13 --synthesize` 调用 Claude API 生成简报（需要真实 `ANTHROPIC_API_KEY`）
- 生成的 `recommendations_20260513.md` 包含三节内容（市场判断 / 操作建议 / 风险提示）
- `uv run pytest tests/test_prompt_builder.py -v` 全部通过（不需要 API key）
- DuckDB `api_usage` 表中记录了当次调用的 token 消耗

## Dependencies

phase-5（`SignalsFile` 输出已生成）；`ANTHROPIC_API_KEY` 环境变量已配置

## Notes

每日只运行一次（由 watchdog 触发或手动运行），是全天最高成本操作（约 0.01–0.02 USD/天）。Prompt 模板中避免放入完整的新闻原文，只放摘要（≤200 chars/条）。`--synthesize` flag 设计为可选，允许在不触发 API 的情况下只运行规则引擎（节约测试成本）。
