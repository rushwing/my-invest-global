# my-invest-global — Project Scope

## Overview

**my-invest-global** is a personal AI infrastructure stock portfolio advisor. It consumes structured data produced by Codex agents, runs a three-signal scoring engine, and outputs daily strategy briefs and per-stock action recommendations — all in Chinese, targeting A-share AI infrastructure holdings.

**Tool positioning:** Advisory only. Every recommendation traces back to an auditable rule. No automated order execution.

**Division of labor:**

| Responsibility | Owner |
|---|---|
| Data collection (news / reports / KOL digests) | Codex Daily/Weekly Agent |
| Holdings OCR (screenshot → structured CSV) | Codex OCR Agent |
| Price history fetch (AkShare / yfinance) | This tool (engine/data_agent/) |
| Macro indicator collection (FRED / SEC EDGAR / Yahoo global / AKShare macro) | This tool (engine/macro_agent/) |
| Three-signal scoring | This tool (engine/signals/) |
| LLM strategy brief synthesis | This tool (engine/synthesis/) |
| Dashboard visualization | This tool (app/) |

**Personal use only** — no multi-user auth, no SaaS deployment, no real-time tick data.

---

## Use Cases

### UC-1 每日策略简报 (Daily Strategy Brief)

**Trigger:** Codex agent drops `daily_news_{YYYYMMDD}.json` + `holdings_{YYYYMMDD}.csv` into `data/agent_input/`. watchdog fires the pipeline.

**Pipeline:**
1. Validate and ingest agent_input files → DuckDB
2. Fetch latest price data for all holdings (AkShare for A-shares, yfinance for US)
3. Compute Signal A (technical) + Signal B (fundamental) + Signal C (sentiment) for each holding
4. Apply portfolio framework check: current 白马/弹性 ratio vs. target
5. Detect special overrides: stop-loss trigger (弹性股 -20%), target-price alert (upside <5%)
6. Call Claude API with structured prompt (≤3000 tokens) → strategy brief (≤800 tokens)
7. Write `data/processed/signals_{date}.json` + `data/processed/recommendations_{date}.md`

**Output:** Markdown strategy brief with three sections: market judgment / per-stock actions / risk alerts

**Constraints:**
- LLM only synthesizes — all numerical scoring done by rule engine first
- Each recommendation must reference the signal(s) driving it
- API call budget: one call per day, ≤4000 tokens total

---

### UC-2 仓位检查 (Portfolio Balance Check)

**Trigger:** User uploads a new holdings screenshot; Codex OCR agent produces `holdings_{date}.csv`.

**Pipeline:**
1. Load holdings CSV → compute 白马股/弹性股 market value split
2. Determine macro state (Green/Yellow/Red) from latest CapEx signal
3. Compare current ratio to target ratio for macro state
4. Emit rebalance recommendation if |deviation| > 10%
5. Flag any single elastic stock exceeding 8% of total portfolio

**Output:** Streamlit Tab 1 — pie chart + deviation table + rebalance prompt

---

### UC-3 个股深度分析 (Single Stock Deep Dive)

**Trigger:** User selects a ticker in the Streamlit dropdown.

**Pipeline:**
1. Load 180-day price history from DuckDB (or fetch if missing)
2. Compute full pandas-ta indicator set: MACD, RSI, Bollinger Bands
3. Load fundamental data from `data_china_aidc.md` (static, quarterly update)
4. Load latest news items for this ticker from DuckDB (sourced from Codex daily_news)
5. Render Plotly 3-pane chart + fundamental summary card + news feed

**Output:** Streamlit Tab 3 — interactive technical chart, fundamental card, news timeline

---

## Data Contracts

### Inputs (written by Codex agents)

**`data/agent_input/daily_news_{YYYYMMDD}.json`**

| Field | Type | Notes |
|---|---|---|
| `schema_version` | str | "1.0" |
| `date` | str | YYYY-MM-DD |
| `generated_at` | str | ISO-8601 with tz |
| `source_agents` | list[str] | e.g. ["yahoo_finance", "eastmoney"] |
| `items[].id` | str | UUID-v4 |
| `items[].title` | str | |
| `items[].summary` | str | ≤200 chars |
| `items[].url` | str | |
| `items[].published_at` | str | ISO-8601 |
| `items[].source` | str | |
| `items[].tickers_mentioned` | list[str] | Mix of A-share codes and US tickers |
| `items[].sentiment` | str | positive / negative / neutral |
| `items[].category` | str | us_ai_infra / cn_ai_infra / cn_policy / macro / sector_other |
| `items[].relevance_score` | float | 0.0–1.0 |
| `items[].is_overnight_us` | bool | true if US market closed after A-share close |

**`data/agent_input/weekly_report_{YYYYWW}.json`**

| Field | Type | Notes |
|---|---|---|
| `schema_version` | str | "1.0" |
| `week` | str | YYYYWW (ISO week) |
| `date_range` | list[str] | [start, end] ISO dates |
| `industry_reports[].title` | str | |
| `industry_reports[].source` | str | broker name |
| `industry_reports[].key_points` | list[str] | ≤5 bullet points |
| `industry_reports[].affected_tickers` | list[str] | |
| `industry_reports[].sentiment` | str | positive / negative / neutral |
| `kol_digests[].author` | str | |
| `kol_digests[].platform` | str | |
| `kol_digests[].summary` | str | |
| `kol_digests[].tickers_mentioned` | list[str] | |
| `kol_digests[].sentiment` | str | |

**`data/agent_input/kol_digest_{YYYYMMDD}.json`**

Same structure as `kol_digests` array in weekly_report, wrapped in a dated envelope.

**`data/agent_input/holdings_{YYYYMMDD}.csv`**

| Column | Type | Example |
|---|---|---|
| `schema_version` | str | "1.0" |
| `date` | str | 2026-05-13 |
| `code` | str | 300308 |
| `name` | str | 中际旭创 |
| `cost_price` | float | 850.00 |
| `current_price` | float | 1008.00 |
| `quantity` | int | 100 |
| `market_value` | float | 100800.00 |
| `pnl_pct` | str | +18.59% |
| `pnl_amount` | float | 15800.00 |
| `category` | str | 白马股 / 弹性股 |
| `sector` | str | 光通信 / 半导体 / etc. |

### Outputs (written by this tool)

**`data/processed/signals_{YYYYMMDD}.json`** — per-stock scores + action codes + portfolio summary

**`data/processed/recommendations_{YYYYMMDD}.md`** — Claude API output, Markdown format

---

## Portfolio Framework

### 2/3 白马股 + 1/3 弹性股

| Category | Target Weight | Characteristics |
|---|---|---|
| 白马股 (Blue-chip) | ~67% | Sector #1 leaders, Tier-1/2 scarcity, daily volume >100M CNY, institutional coverage |
| 弹性股 (High-beta) | ~33% | Early-stage or transitioning, market cap <50B, Beta >1.5, single position ≤8% of total |

### Macro CapEx Gate (三色门控)

| State | Trigger | 弹性股 Target |
|---|---|---|
| Green (增长) | Big-4 cloud CapEx guidance QoQ ≥ +5% | 38–40% |
| Yellow (平稳) | QoQ −5% ~ +5% | 33% (baseline) |
| Red (收缩) | QoQ < −10% | 20% |

### Dynamic Rebalance Triggers

| Trigger | Direction | Magnitude |
|---|---|---|
| Cloud CapEx guidance raised (quarterly) | 弹性股 ↑ | +7%, max 40% |
| Cloud CapEx guidance cut >10% | 弹性股 ↓ | −13%, floor 20% |
| Sector-wide drawdown >15% (no fundamental change) | 白马股 ↑ | +7%, max 75% |
| Sector breaks prior high with volume | 弹性股 ↑ | +5%, max 38% |
| Single elastic position loss >20% | Stop-loss alert | Recommend reduce/exit |
| Single holding reaches 80% of target price | Take-profit alert | Recommend 30–50% trim |
| Single elastic position exceeds 10% of total | Rebalance alert | Recommend trim to <8% |

Rebalance fires when `|current_ratio − target_ratio| > 10%`.

---

## Signal Engine

### Signal A — Technical (weight: 30%)

Computed via `pandas-ta` on daily + weekly OHLCV data (fetched from AkShare/yfinance, cached in Parquet).

| Indicator | Parameters | Signal Logic | Max Points |
|---|---|---|---|
| MACD | 12/26/9 | Daily golden cross +15, death cross −15; weekly ×1.5 multiplier | 30 |
| RSI | 14-day | <30 oversold +10; >70 overbought −10; neutral 0 | 10 |
| Bollinger Bands | 20-day, 2σ | Near lower band +10; near upper band −5; mid 0 | 10 |
| Volume-price | 5-day avg vol | Volume surge + up +10; shrink + down −5; else 0 | 10 |
| Weekly trend | 13-week MA | Price crosses above MA +10; below −10 | 10 |

Score normalized to 0–100. A-share special handling: suspended days → score paused; limit-up days → RSI/BB signals suspended.

### Signal B — Fundamental (weight: 40%)

Sourced from `data_china_aidc.md` (static research data, quarterly update) + holdings cost basis.

| Factor | Scoring | Max Points |
|---|---|---|
| Scarcity tier | Tier-1=25, Tier-2=18, Tier-3=10, Tier-4=3 | 25 |
| Target price upside | (target−current)/current × 100, capped at 30 | 30 |
| Q1 earnings beat | Revenue growth×0.3 + profit growth×0.7, normalized | 25 |
| Sector ranking | #1=20, #2=13, #3=7, other=2 | 20 |

Special overrides: if current price > target price → upside factor = 0, trigger "target price alert". If elastic stock loss > 20% → emit "stop_loss" override regardless of composite score.

### Signal C — Sentiment (weight: 30%)

Sourced from Codex agent JSON files in `data/agent_input/`.

| Factor | Source | Max Points |
|---|---|---|
| Overnight US leading indicator | daily_news (is_overnight_us=true) | 40 |
| Ticker-specific news sentiment | daily_news filtered by tickers_mentioned | 30 |
| KOL sentiment | kol_digest | 20 |
| Broker report update | weekly_report | 10 |

**Overnight US weighting:**
```
NVDA: 35%  (optical modules / PCB chain)
AVGO: 20%  (network ASIC / switch chain)
VRT:  20%  (liquid cooling chain)
ANET: 15%  (AI ethernet / network equipment)
MU:   10%  (HBM memory / storage chain)
```

Score = Σ(weight × clip(pct_change × 10, −40, 40) + 20), normalized to 0–40.

### Fusion and Action Mapping

```
Composite = A × 0.30 + B × 0.40 + C × 0.30

≥ 75  → strong_add    (强烈建议加仓)
60–74 → hold_add      (建议持有/小幅加仓)
40–59 → hold          (观望)
< 40  → reduce        (考虑减仓)

Overrides (take priority over composite):
  弹性股 loss > 20%          → stop_loss
  Upside to target < 5%      → take_profit_alert
  Macro state = Red          → all elastic stocks downgraded to hold
```

---

## Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| Language | Python ≥3.12 | pandas-ta requires 3.12+ |
| Indicator engine | pandas-ta 0.3.14b+ | Lightweight vs full Qlib; all needed indicators in one lib |
| Data storage | DuckDB ≥1.0 + Parquet | OLAP on time-series; zero server; fast Parquet queries |
| Price data | AkShare ≥1.12 (A-share), yfinance ≥0.2 (US) | Free, no account required |
| Agent interface | File system (JSON/CSV) + watchdog ≥4.0 | Zero coupling; Codex just writes files |
| LLM synthesis | Anthropic SDK ≥0.25 (claude-sonnet-4-6) | Best Chinese; structured output; 200K context |
| Dashboard | Streamlit ≥1.32 + Plotly ≥5.18 | Fastest to prototype; native pandas; browser UI |
| Schema validation | Pydantic ≥2.0 | Agent input validation; typed config |
| Config | python-dotenv ≥1.0 | .env-based secrets |
| Logging | loguru ≥0.7 | Structured, colored |
| Package management | uv | Fast resolver; uv.lock for reproducibility |

See `docs/adr/` for full decision rationale on each selection.

---

## Out of Scope (v1)

- Automated order execution or brokerage API integration
- Real-time tick data for A-shares (macro indicators use 5–60 min intraday polling — in scope via engine/macro_agent/)
- Web search or live data scraping (delegated to Codex agents)
- Multi-user authentication or remote deployment
- US stock holdings (A-share focus; US tickers only as leading indicators)
- ML model training (LightGBM factor model deferred until 2+ years of labeled data)
- Backtesting framework (advisory tool, not trading system)
- Mobile app
