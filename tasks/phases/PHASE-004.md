---
phase_id: phase-4
title: 情绪信号引擎
status: draft
priority: P0
---

## Goal

实现 Signal C（情绪/新闻），权重 30%。从 DuckDB 中的 `news_items` 和 `weekly_reports` 表读取 Codex agent 输出，计算隔夜美股先行指标、个股新闻情绪、KOL 情绪和机构研报更新四个子因子，输出情绪评分 0–100。

## In Scope

- `engine/signals/sentiment.py`：
  - `compute_sentiment_score(code: str, date: str) -> dict`
  - 子因子计算：
    1. **隔夜美股先行指标（满分 40）：**
       - 从 `news_items` 读取 `is_overnight_us=true` 的当日新闻，提取 NVDA/AVGO/VRT/ANET/MU 的 `pct_change`（从 news summary 中解析，或从 price_fetcher 的 US 数据拉取）
       - 加权：NVDA 35%, AVGO 20%, VRT 20%, ANET 15%, MU 10%
       - `score = Σ(weight × clip(pct_change × 10, −40, 40) + 20)`，归一化到 0–40
    2. **个股新闻情绪（满分 30）：**
       - 从 `news_items` 筛选 `tickers_mentioned` 包含 `code` 的当日新闻
       - positive=30, neutral=15, negative=0；多条新闻取加权平均（按 `relevance_score`）
    3. **KOL 情绪（满分 20）：**
       - 从 `weekly_reports` 读取最近一周的 `kol_digests`，筛选 `tickers_mentioned` 包含 `code`
       - positive=20, neutral=10, negative=0；多条取均值
    4. **机构研报更新（满分 10）：**
       - 从 `weekly_reports` 读取最近一周 `industry_reports`，筛选 `affected_tickers` 包含 `code`
       - 有新研报且 positive=10；有研报但 negative=0；无研报=5
  - 返回结构：`{"sentiment_score": int, "factors": {"overnight_us": float, "news": float, "kol": float, "broker": float}, "overnight_catalysts": [str]}`
- `engine/data/us_price_parser.py`：从 news summary 文本中用正则提取美股涨跌幅（如 "NVDA +8.2%"），作为隔夜指标的数据来源（减少 yfinance 调用）
- `tests/test_sentiment.py`：用 DuckDB fixture 数据覆盖各子因子边界情况（无新闻、全 positive、全 negative、混合情绪）

## Out of Scope

- 实时新闻爬取（Codex agent 负责）
- 社交媒体实时情绪（Codex agent 负责）
- 大V账号管理（由 Codex agent 维护 KOL 列表）

## Exit Criteria

- `uv run pytest tests/test_sentiment.py -v` 全部通过
- 情绪分在 0–100 范围内
- 无 DuckDB 中相关新闻时，情绪分优雅降级为 50（中性基准），不报错
- 隔夜美股计算在测试 fixture 中验证：NVDA +8% → overnight_us 分接近满分 40

## Dependencies

phase-1（DuckDB news_items 和 weekly_reports 表已存在并可查询）；phase-2（price_fetcher 的 US ticker 功能，用于隔夜美股数据备选来源）

## Notes

情绪信号是三信号中最容易出现"无数据"的情况（Codex agent 可能某天没有输入）。所有子因子都需要有 fallback 默认值（中性分）。隔夜美股的涨跌幅优先从新闻 summary 解析，如解析失败则调用 yfinance 获取前一交易日收盘价变化。
