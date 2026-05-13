# ADR-002：数据管道接口设计（与 Codex Agent 对接）

- **状态**：已采纳
- **日期**：2026-05-13
- **决策者**：Daniel Wong

---

## 背景

数据采集由 Codex Agent 负责，本工具只消费结构化输出。接口设计需要：
- 对 Codex Agent 的实现侵入性最低（不要求 agent 理解本工具的内部结构）
- 支持三类数据：财经新闻 / 行业研报+大V简报 / 持仓 OCR 数据
- 可审计（每次输入文件有时间戳，历史可回溯）
- 预留未来升级路径（从文件→消息队列）

---

## 可选方案

| 方案 | Pros | Cons |
|---|---|---|
| **文件系统 JSON/CSV（选定）** | 零依赖；Codex 直接写文件；可离线调试；文件即日志 | 需要 watchdog 轮询；不支持毫秒级实时 |
| SQLite 共享数据库 | 事务安全；可查询历史；接口统一 | Codex agent 需要了解 schema；两侧耦合度高 |
| Redis Streams | 实时推送；高吞吐；发布/订阅解耦 | 需要 Redis 服务；对当前规模过重 |
| HTTP API（FastAPI） | 语言无关；标准 REST | 需要长期运行的服务器；增加部署复杂度 |
| LangChain Memory / MCP | AI-native 接口 | 标准不稳定；厂商锁定风险 |

---

## 决策

**选定：文件系统（JSON + CSV）+ watchdog 监听**

---

## 接口规约（文件契约 v1）

### 目录结构

```
data/
  agent_input/                     # Codex Agent 写入（本工具只读）
    daily_news_{YYYYMMDD}.json
    weekly_report_{YYYYWW}.json    # WW = ISO 周数，如 202620
    kol_digest_{YYYYMMDD}.json
    holdings_{YYYYMMDD}.csv
  processed/                       # 本工具写入（分析结果）
    signals_{YYYYMMDD}.json
    recommendations_{YYYYMMDD}.md
```

---

### Schema v1：daily_news_{YYYYMMDD}.json

```json
{
  "schema_version": "1.0",
  "date": "2026-05-13",
  "generated_at": "2026-05-13T06:30:00+08:00",
  "source_agents": ["yahoo_finance", "eastmoney", "tencent_finance"],
  "items": [
    {
      "id": "uuid-v4",
      "title": "NVIDIA Q1 revenue beats estimates, stock surges 8%",
      "summary": "NVDA reported Q1 2026 revenue of $44.1B, up 69% YoY...",
      "url": "https://...",
      "published_at": "2026-05-13T22:15:00-04:00",
      "source": "yahoo_finance",
      "tickers_mentioned": ["NVDA", "AMD", "300308"],
      "sentiment": "positive",
      "category": "us_ai_infra",
      "relevance_score": 0.95,
      "is_overnight_us": true
    }
  ]
}
```

**category 枚举：**
- `us_ai_infra`：美股 AI 基础设施（NVDA/AVGO/VRT 等）
- `cn_ai_infra`：A 股 AI 基建（光模块/PCB/液冷等）
- `cn_policy`：国内政策/监管（BIS 管制/国产替代/算力政策）
- `macro`：宏观（美联储/PBOC/汇率/云厂商 CapEx）
- `sector_other`：其他行业新闻

---

### Schema v1：weekly_report_{YYYYWW}.json

```json
{
  "schema_version": "1.0",
  "week": "202620",
  "date_range": ["2026-05-11", "2026-05-17"],
  "generated_at": "2026-05-13T08:00:00+08:00",
  "industry_reports": [
    {
      "title": "光模块行业周报：800G 出货量创新高",
      "source": "中信证券",
      "key_points": ["800G 出货量 QoQ +35%", "CPO 量产时间表提前至 Q3"],
      "affected_tickers": ["300308", "300502", "300394"],
      "sentiment": "positive"
    }
  ],
  "kol_digests": [
    {
      "author": "Trader韭",
      "platform": "微信公众号",
      "summary": "本周光模块板块走强原因分析...",
      "tickers_mentioned": ["300308"],
      "sentiment": "positive",
      "published_at": "2026-05-13T10:00:00+08:00"
    }
  ]
}
```

---

### Schema v1：holdings_{YYYYMMDD}.csv

```csv
schema_version,date,code,name,cost_price,current_price,quantity,market_value,pnl_pct,pnl_amount,category,sector,notes
1.0,2026-05-13,300308,中际旭创,850.00,1008.00,100,100800.00,+18.59%,+15800.00,白马股,光通信,光模块全球龙头
1.0,2026-05-13,688008,澜起科技,80.00,95.00,500,47500.00,+18.75%,+7500.00,白马股,半导体,内存接口芯片全球#1
1.0,2026-05-13,688616,星融元,75.00,85.00,300,25500.00,+13.33%,+3000.00,弹性股,网络,国产RoCE高弹性
```

**category 枚举：** `白马股` | `弹性股`

**持仓截图约定路径（OCR Agent 读取）：**
```
~/Desktop/holdings_screenshots/     # 或约定其他路径
```

---

### Schema v1：processed/signals_{YYYYMMDD}.json（本工具输出）

```json
{
  "schema_version": "1.0",
  "date": "2026-05-13",
  "generated_at": "2026-05-13T09:30:00+08:00",
  "portfolio_summary": {
    "total_market_value": 350000,
    "white_horse_ratio": 0.68,
    "elastic_ratio": 0.32,
    "target_white_horse": 0.67,
    "target_elastic": 0.33,
    "rebalance_needed": false
  },
  "stock_signals": [
    {
      "code": "300308",
      "name": "中际旭创",
      "category": "白马股",
      "technical_score": 72,
      "fundamental_score": 88,
      "sentiment_score": 85,
      "composite_score": 83,
      "action": "持有/小幅加仓",
      "action_code": "hold_add",
      "signals": {
        "macd_golden_cross": true,
        "rsi_14": 61.2,
        "target_price_upside": 0.19,
        "scarcity_tier": 1,
        "overnight_us_catalyst": "NVDA +8% 隔夜，光模块链受益"
      }
    }
  ]
}
```

**action_code 枚举：**
- `strong_add`：强烈建议加仓（综合分 ≥75）
- `hold_add`：建议持有/小幅加仓（60-74）
- `hold`：观望（40-59）
- `reduce`：考虑减仓（<40）
- `stop_loss`：止损提示（弹性股亏损 >20%）
- `take_profit_alert`：目标价警报（距目标价 ≤20%）

---

## 文件命名与版本控制

- `schema_version` 字段嵌入每个文件，允许本工具向后兼容处理旧版本
- 文件名含日期/周数，天然形成时间序列，支持历史回溯
- Codex Agent 升级 schema 时，递增 `schema_version`（如 `"1.1"`），本工具可按版本分支处理

## 未来升级路径

当需要实时推送时，文件接口可无缝升级为 Redis Streams：
- 文件契约的 JSON schema 即为消息体格式
- 本工具的消费端只需将 `watchdog` 替换为 `redis.xread`
- Codex Agent 侧只需将 `write_json()` 替换为 `redis.xadd()`
- 核心分析引擎代码**零改动**

---

## 后果

- ✅ Codex Agent 实现简单：写文件到约定路径即可，无需了解本工具内部
- ✅ 完全可离线调试：将历史文件放到 agent_input/ 即可回放
- ✅ 审计友好：每天的输入文件自动存档
- ⚠️ 多 Agent 并发写入同一文件时需加文件锁（目前单 agent 写入，暂不需要）
- ⚠️ watchdog 轮询延迟约 1 秒，对每日批量更新场景完全够用
