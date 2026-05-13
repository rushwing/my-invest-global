---
phase_id: phase-2
title: 技术信号引擎
status: draft
priority: P0
---

## Goal

实现 Signal A（技术分析），权重 30%。使用 pandas-ta 计算 MACD、RSI、布林带、量价和周线趋势五个指标，处理 A 股特殊情况（停牌/涨停），输出归一化到 0–100 的技术评分。

## In Scope

- `engine/data/price_fetcher.py`：
  - `fetch_a_share(code: str, days: int = 180) -> pd.DataFrame`：使用 AkShare 拉取日线 OHLCV，写入 `price_history` 表（upsert）；缓存命中（数据库中有当日数据）则跳过网络请求
  - `fetch_weekly(code: str, weeks: int = 52) -> pd.DataFrame`：聚合日线为周线（每周末收盘价）
  - 支持 US ticker（yfinance）：`fetch_us(ticker: str, days: int = 30) -> pd.DataFrame`（仅用于隔夜美股先行指标计算，非持仓）
- `engine/signals/technical.py`：
  - `compute_technical_score(code: str, date: str) -> dict`
  - 指标计算（均使用 pandas-ta）：
    - MACD (12/26/9)：日线金叉/死叉，周线优先级×1.5
    - RSI-14：<30 超卖 +10，>70 超买 −10，中性 0
    - 布林带 (20日, 2σ)：下轨附近 +10，上轨附近 −5，中轨 0
    - 量比 (5日均量)：放量上涨 +10，缩量下跌 −5，其他 0
    - 13周均线穿越：上穿 +10，下穿 −10
  - 原始分加总 → 归一化到 0–100
  - A 股特殊处理：停牌日（当日无成交量 & 价格不变）→ 返回 `None`（标记"暂停"）；涨停日（涨幅≥9.9%）→ RSI/布林带因子得 0（不参与加分）
  - 返回结构：`{"technical_score": int, "signals": {"macd_golden_cross": bool, "rsi_14": float, ...}, "suspended": bool, "limit_up": bool}`
- `tests/test_technical.py`：用预先录制的价格 fixture 数据（不依赖网络）覆盖各指标边界情况、停牌处理、涨停处理

## Out of Scope

- 基本面信号（属于 PHASE-003）
- 情绪信号（属于 PHASE-004）
- 周报/新闻数据读取（PHASE-001 已入库，此处只读 price_history 表）

## Exit Criteria

- `uv run python -c "from engine.signals.technical import compute_technical_score; print(compute_technical_score('300308', '2026-05-13'))"` 返回有效 dict（需要有测试数据在 DuckDB）
- `uv run pytest tests/test_technical.py -v` 全部通过，覆盖：正常分数计算、停牌返回 None、涨停 RSI/BB 得 0
- 技术分在 0–100 范围内（fixture 数据验证）
- 不发生网络请求（fixture 数据直接写入 DuckDB，price_fetcher 缓存命中）

## Dependencies

phase-1（DuckDB price_history 表、数据库连接）

## Notes

pandas-ta 需要 Python ≥3.12（已在 pyproject.toml 中约束）。周线数据由日线聚合，不单独从 AkShare 拉取周线接口（避免数据不一致）。停牌判断用"当日成交量=0 且收盘价=前日收盘价"的启发式规则，而非依赖交易所停牌标志（后者需付费数据源）。
