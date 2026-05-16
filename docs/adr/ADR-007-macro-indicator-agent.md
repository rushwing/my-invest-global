# ADR-007：宏观指标 Agent 架构——独立采集、UpdateClass 分类与 MCP 工具封装

- **状态**：已采纳
- **日期**：2026-05-16
- **决策者**：Daniel Wong

---

## 背景

`data_agent`（Phase 0–1）完成后，宏观指标采集需求变得迫切：

1. 投资组合框架（ADR-003）中的"宏观 CapEx 门控"当前依赖人工维护的
   `data/cache/macro_state.json`，这是一个临时方案。真正的数据驱动需要
   自动化采集 Group L（云巨头 CapEx）、Group I（美联储利率/FOMC）、
   Group K（SOX/收益率曲线）等指标。

2. 宏观指标的数据源、更新频率、时区特性与 A 股 stock-data-agent 存在
   根本性差异（详见决策一）。

3. ADR-006 确立了"四层并存"工具封装路线（CLI → FastAPI → MCP → LangGraph）。
   LangGraph ReAct Agent（Phase 9）需要工具 `get_macro_state()`、
   `get_capex_trend()` 等来驱动投资组合决策，这些工具必须有对应的 MCP Server
   层封装。

4. AKShare 和 Tushare 同时被两个 agent 使用，需要决定是否提取为共享模块。

数据源权威文档：`docs/macro-market-indicator-matrix.md`（Groups I–O，30+ 指标）。

---

## 决策一：独立 Agent，不与 stock-data-agent 合并

### 可选方案

| 方案 | 优点 | 问题 |
|------|------|------|
| 合并进 data_agent | 复用调度器、速率限制器 | 调度逻辑冲突（见下） |
| 完全独立 macro_agent | 关注点分离，生命周期独立 | 需额外 orchestrator 骨架 |

### 决策：完全独立 `engine/macro_agent/`

两个 agent 在五个维度上存在根本差异，合并代价远超共享收益：

| 维度 | stock-data-agent | macro-indicator-agent |
|------|------------------|-----------------------|
| 主要数据源 | Tencent/Eastmoney/CNINFO | FRED/SEC EDGAR/Yahoo Finance |
| 调度驱动 | A 股交易日历（CST 09:30–15:00） | 全球发布日历（5 个时区） |
| 更新粒度 | 秒/分钟/日 | 月/季度/事件驱动 |
| 数据宇宙 | 逐支股票代码 | 固定指标集合（Groups I–O） |
| 下游消费方 | 技术/基本面分析管道 | 宏观门控 + LangGraph 工具 |

stock-data-agent 的调度器强绑定 A 股交易窗口（09:30–11:30、13:00–15:00 CST）；
macro-indicator-agent 必须同时处理 KRX（KST）、TWSE（CST）、NYMEX（CT）、
NYSE（ET）、FRED（ET 发布）五套时区窗口——强行合并会让单一调度器管理 5+ 时区，
产生不可维护的复杂度。

生命周期同样不同：stock-agent 在交易时段持续运行；macro-agent 绝大多数时间空
闲，仅在发布日前后出现脉冲式高频采集。

**接受的代价**：两个 agent 目录均需独立 orchestrator 骨架。通过决策二的共享
源模块减轻重复。

---

## 决策二：部分提取 AKShare/Tushare 为共享模块

### 可选方案

| 方案 | 优点 | 问题 |
|------|------|------|
| 不提取，各自实现 | 无依赖耦合 | AKShare 宏观函数重复实现 |
| 全量提取到 shared/ | 最大复用 | 破坏 data_agent 内部 FieldGroup 绑定 |
| 仅提取宏观函数子集 | 最小改动，高内聚 | 多了一个 source 位置 |

### 决策：仅提取宏观专用函数，在 `engine/shared/sources/` 落地

```
engine/
  shared/
    __init__.py
    sources/
      __init__.py
      base_macro.py        # MacroAbstractSource — 添加 period_date, market_tz 辅助方法
      akshare_macro.py     # AKShareMacroSource：macro_china_cpi_monthly, stock_info_global_cls,
                           #   futures_foreign_hist, stock_market_deal_em
      tushare_macro.py     # TushareMacroSource：fx_daily, index_daily (宏观上下文)
      fred.py              # FREDSource：FRED API + realtime_start 支持（见 BP-1）
      sec_edgar.py         # SECEdgarSource：companyfacts XBRL + CapEx 单季反算（见 BP-3）
      yahoo_global.py      # YahooGlobalSource：全球指数/期货/FX + crumb 会话管理（见 BP-8）
      alpha_vantage.py     # AlphaVantageSource：新闻情绪 + 25 req/day 预算台账（见 BP-9）
```

`engine/data_agent/sources/akshare.py` 和 `tushare.py` **不移动**——它们与
`FieldGroup` 枚举、`GROUP_DISPATCH` 键强绑定，拆分会破坏全部测试。

所有宏观 sources 继承 `engine/data_agent/sources/base.py` 中的
`AbstractSource`，无需修改基类。

**所有权规则**（写入 `harness/CONNECTORS.md`）：

> 若某 source 函数服务**股票数据** → 属于 `data_agent/sources/`
> 若某 source 函数服务**宏观指标** → 属于 `shared/sources/`

---

## 决策三：MCP 封装，与 ADR-006 保持一致

### 决策：`engine/mcp/macro_tools.py` 暴露 6 个 MCP 工具

沿用 ADR-006 四层并存路线，宏观 agent 的 Phase 7 MCP 层：

```python
# engine/mcp/macro_tools.py

@mcp.tool()
def get_macro_state() -> dict:
    """返回当前宏观门控状态：capex_state / yield_curve_state / risk_state / composite。"""

@mcp.tool()
def get_capex_trend(company: str, quarters: int = 4) -> dict:
    """返回 MSFT/AMZN/GOOGL/META 的单季 CapEx 和 QoQ 增速（含 capex_as_of 时效标注）。"""

@mcp.tool()
def get_fomc_calendar(lookahead_days: int = 90) -> list[dict]:
    """返回未来 N 天内的 FOMC 会议日期和决议状态。"""

@mcp.tool()
def get_yield_curve() -> dict:
    """返回最新 10Y/2Y 国债收益率及 10Y-2Y 利差（FRED 来源，含 vintage）。"""

@mcp.tool()
def get_global_indices(groups: list[str]) -> dict:
    """返回指定 group（J/K/M/N）最新 OHLCV 和时效时间戳。"""

@mcp.tool()
def get_news_sentiment(hours_back: int = 24) -> dict:
    """返回 CLS 电报和 Alpha Vantage 新闻情绪摘要。"""
```

工具仅读取 DuckDB；业务逻辑留在 `engine/macro_agent/regime.py`，与 ADR-006
"同一业务逻辑，不同访问层"原则一致。工具返回值使用 Pydantic 模型强校验
（ADR-006 防幻觉机制二）。

---

## 决策四：UpdateClass 七级分类体系

### 决策：引入 `UpdateClass` 枚举，分类所有 30+ 指标

```python
# engine/macro_agent/update_class.py
class UpdateClass(str, Enum):
    INTRADAY_FAST = "intraday_fast"   # 1–5 min：NVDA/MSFT/AVGO/ANET/VRT、SGX A50、创业板50
    INTRADAY_SLOW = "intraday_slow"   # 15–60 min：全球指数、大宗商品、FX、新闻
    DAILY         = "daily"           # 收盘后：国债收益率、三星、台湾加权、成交额、绿电指数
    WEEKLY        = "weekly"          # 保留
    MONTHLY_FIXED = "monthly_fixed"   # BLS/NBS 发布日触发：CPI/PPI
    QUARTERLY     = "quarterly"       # SEC 10-Q/10-K 受理后：CapEx
    EVENT_DRIVEN  = "event_driven"    # FOMC 决议日：联邦基金利率目标区间
    STATIC_YAML   = "static_yaml"     # 人工维护：FOMC 日历 YAML
```

### 完整指标分类

| Group | 指标 | UpdateClass | 主要数据源 | 备注 |
|-------|------|-------------|-----------|------|
| I | US CPI/PPI | `MONTHLY_FIXED` | FRED CPIAUCSL/PPIACO | BLS 发布日 T+0/T+1 |
| I | China CPI/PPI | `MONTHLY_FIXED` | AKShare macro_china_cpi_monthly | NBS 发布日 |
| I | 联邦基金利率目标区间 | `EVENT_DRIVEN` | FRED DFEDTARL/DFEDTARU | 仅 FOMC 决议日变化 |
| I | FOMC 日历 | `STATIC_YAML` | fomc_calendar.yaml | 年度刷新 |
| J | Brent (BZ=F) / WTI (CL=F) | `INTRADAY_SLOW` | Yahoo Finance | ICE/NYMEX 开市期间 |
| J | XLU | `INTRADAY_SLOW` | Yahoo Finance | NYSE 开市期间 |
| K | SOX/COMP/NDX/SPX/DXY | `INTRADAY_SLOW` | Yahoo Finance | NYSE 开市期间 |
| K | 10Y/2Y 国债收益率 | `DAILY` | FRED DGS10/DGS2 | T+1；盘中备用 investing.com |
| K | 10Y-2Y 利差 | `DAILY` | 本地计算（DGS10 - DGS2） | 两项到齐后自动计算 |
| K | NVDA/MSFT/AVGO/ANET/VRT | `INTRADAY_FAST` | Yahoo Finance | A 股链条领先指标 |
| L | MSFT/AMZN/GOOGL/META CapEx | `QUARTERLY` | SEC EDGAR companyfacts | 10-Q/10-K 受理后触发 |
| L | CapEx YoY 增速 | `QUARTERLY` | 本地计算 | 新季度数据落地后重算 |
| M | SOXX/TWII/TSM (^SOX/TWII/TSM) | `INTRADAY_SLOW` | Yahoo Finance | TWSE 09:00–13:30 CST |
| M | 三星 (005930.KS) | `DAILY` | Yahoo Finance | KRX 收盘后 |
| M | KRX 半导体指数 | `DAILY` | investing.com 备用 | 稳定免费源缺失，仅日频 |
| N | SGX A50 期货 | `INTRADAY_FAST` | AKShare SGX | A 股开盘前关键信号 |
| N | 创业板 50 (000688.SH) | `INTRADAY_FAST` | AKShare stock_zh_index_spot | A 股交易时段 |
| N | USD/CNH (离岸人民币) | `INTRADAY_SLOW` | Sina FX | 24h 市场 |
| N | USD/CNY (在岸人民币) | `INTRADAY_SLOW` | Sina FX | 人行中间价 09:15 CST |
| N | 绿电板块指数 | `DAILY` | AKShare 概念板块 | 收盘后；需概念名称映射 |
| N | A 股两市日成交额 | `INTRADAY_SLOW` | AKShare stock_market_deal_em | 15 min 间隔；15:05 终值 |
| O | 财联社电报 (CLS) | `INTRADAY_SLOW` | AKShare stock_info_global_cls | 30 min 间隔 |
| O | 全球财经新闻 | `INTRADAY_SLOW` | Alpha Vantage NEWS_SENTIMENT | 预算门控（见 BP-9） |
| O | 地缘政治监控 | `EVENT_DRIVEN` | 关键词告警（GDELT/NewsAPI） | 关键词匹配触发 |

**调度关键洞察**：macro-agent 调度器必须**按指标独立判断时区窗口**，而非全局
判断。例如，`INTRADAY_FAST` 的 NVDA 在 NYSE 开市期间每 1–5 min 采集，而
`INTRADAY_FAST` 的 SGX A50 在 A 股开盘前的 08:00–09:30 CST 窗口尤为关键。

---

## 决策五：社区最佳实践补充（10 条）

以下设计点在现有架构文档中未涉及：

### BP-1：FRED `realtime_start` 时效审计列

FRED 支持通过 `realtime_start`/`realtime_end` 查询历史版本（vintage）数据。
`macro_indicators` 表存储 `realtime_start DATE` 和 `vintage_as_of DATE`，用于
回测时还原"模型在某时点知道什么"，消除前视偏差。

### BP-2：SEC EDGAR User-Agent 合规与 CIK 静态映射

SEC EDGAR 明确要求 User-Agent 包含联系邮件：
`my-invest-global ruoxu.wang@gmail.com`。`SECEdgarSource` 在类级别强制
注入此 header；速率限制器配置为 8 req/s（官方上限 10 req/s 的 80%）。
静态 `sec_cik_map.py` 缓存 MSFT/AMZN/GOOGL/META 的 CIK，避免重复发现请求。

### BP-3：CapEx 单季反算（10-Q 累积 → 单季）

SEC EDGAR 10-Q 披露财年累计 CapEx，而非单季。`SECEdgarSource` 必须实现
反算：`Q2_single = Q2_cumulative - Q1_cumulative`。入库前统一为单季值，并以
`filing_form TEXT`（"10-Q" | "10-K"）标注来源。Yahoo Finance `quoteSummary`
已返回单季值，可作为交叉验证。

### BP-4：宏观门控状态机引入 STALE 状态

若任一支柱（CapEx / 收益率曲线 / 风险指数）的最新数据时效超过其
`UpdateClass` 标准周期的 2 倍，门控状态自动切换为 `STALE`，拒绝基于陈旧
数据做出门控决策。`STALE` 状态通过 ADR-006 `[stale]` 标志链传播至
`FrozenMarketSnapshot`，避免 LangGraph agent 依赖过期宏观数据。

### BP-5：双列时区归一化

所有宏观表时间戳采用双列模式：
- `utc_ts TIMESTAMPTZ`：入库时刻（UTC）
- `local_date DATE`：原始市场的本地交易日期（非 UTC 日期）
- `market_tz TEXT`：原始市场时区（`America/New_York`、`Asia/Shanghai` 等）

此设计避免跨日查询时的 UTC 偏移错误（如"2026-05-15 SOX 收盘价"对应 ET
日期，而非 UTC 次日）。

### BP-6：FOMC ICS 解析，优于 HTML 抓取

美联储发布官方 ICS 日历。`FOMCCalendarSource` 使用 `icalendar` Python 库
解析，避免 HTML 结构变更导致的爬虫脆弱性；ICS 不可用时回退到本地
`fomc_calendar.yaml`。

### BP-7：BLS/NBS 发布日历预填充

BLS 提前一年公布 CPI/PPI 发布日期（结构化 HTML/PDF）；NBS 类似。
`release_calendar.py` 在启动时将这些日期预填充至 DuckDB，使
`MONTHLY_FIXED` 触发精确落在发布日，而非每天轮询月度序列（可减少 95% 的
无效 API 调用）。

### BP-8：Yahoo Finance Crumb 会话管理

Yahoo Finance `quoteSummary` 端点（CapEx 备用来源
`cashflowStatementHistoryQuarterly`）需要 `crumb` token。
`YahooGlobalSource` 实现 `_refresh_crumb()`，TTL 24h，在首次
`quoteSummary` 请求前懒加载。缺失此机制将导致生产环境 401/404。

### BP-9：Alpha Vantage 每日 25 请求预算台账

Alpha Vantage 免费层硬限制 25 req/day。`AlphaVantageSource` 在 DuckDB 维护
`alpha_vantage_budget` 台账（`date DATE, requests_used INT`），当
`requests_used >= 22` 时拒绝新请求（保留 3 次紧急备用）。

### BP-10：CapEx 内容哈希幂等导入

SEC EDGAR companyfacts 响应无可靠 `ETag`。`SECEdgarSource` 对原始 JSON
计算 SHA-256，存入 `capex_quarterly.source_hash`；重新拉取时若哈希不变则
跳过 upsert，提供数据实际变更的审计轨迹。

---

## 结果

### 正面影响

- 宏观门控从人工维护迁移至数据驱动；`macro_state.json` 手动覆盖保留为紧急逃生口
- LangGraph ReAct agent 获得 6 个 MCP 工具，输出经 Pydantic 强校验
- UpdateClass 分类使调度器在 5 个全球市场时区下行为正确，非活跃时段不产生冗余轮询
- FRED vintage 列支持未来无前视偏差的宏观门控回测
- 独立 agent 保持 stock-data-agent 的 A 股交易日历逻辑不受干扰

### 负面影响（已接受）

- Source 文件存在三个位置（`data_agent/sources/`、`shared/sources/`、
  `macro_agent/sources/`）；通过 `harness/CONNECTORS.md` 所有权规则缓解
- Alpha Vantage 免费层 25 req/day 是 Group O 新闻情绪的真实约束；调度器须
  精细预算（每 30–60 min 1 次，全天约 16–24 次）
- SEC EDGAR CapEx 数据在季末后 30–40 天到达；宏观状态输出中以
  `capex_as_of: "2026-Q1"` 明确披露时效滞后，而非隐藏

---

## 目录结构

```
engine/
  shared/                              # 两个 agent 共享
    __init__.py
    sources/
      __init__.py
      base_macro.py
      akshare_macro.py
      tushare_macro.py
      fred.py
      sec_edgar.py
      yahoo_global.py
      alpha_vantage.py

  macro_agent/                         # 新 agent
    __init__.py
    update_class.py                    # UpdateClass 枚举
    indicator_groups.py                # IndicatorGroup 枚举（I–O）+ SourcePolicy
    scheduler.py                       # MacroScheduler（时区感知 + 发布日历驱动）
    orchestrator.py                    # MacroOrchestrator（主循环 + 调度分发）
    storage.py                         # MacroStorage（4 张新 DuckDB 表）
    regime.py                          # MacroRegime（门控状态计算 + STALE 守卫）
    release_calendar.py                # BLS/NBS 发布日历预填充
    sec_cik_map.py                     # MSFT/AMZN/GOOGL/META 静态 CIK 映射
    fomc_calendar.yaml                 # 预填充 FOMC 日期（STATIC_YAML 类）
    sources/
      __init__.py
      fomc_ical.py                     # FOMCCalendarSource（Fed ICS 解析器）

  mcp/
    macro_tools.py                     # 6 个 MCP 工具

scripts/
  refresh_macro_agent.py               # CLI: uv run refresh-macro-agent

tests/
  test_macro_agent/
    __init__.py
    test_indicator_groups.py
    test_macro_scheduler.py
    test_macro_storage.py
    test_sec_edgar.py
    test_fred.py
    test_regime.py
```

### DuckDB 新增 4 张表

```sql
-- 所有宏观指标时间序列（含 FRED vintage 审计）
CREATE TABLE IF NOT EXISTS macro_indicators (
    indicator_id    TEXT        NOT NULL,   -- e.g. "CPIAUCSL", "DGS10", "BZ=F"
    group_code      TEXT        NOT NULL,   -- "I"/"J"/"K"/"L"/"M"/"N"/"O"
    period_date     DATE        NOT NULL,   -- 本地市场交易日期
    market_tz       TEXT        NOT NULL,   -- "America/New_York" / "Asia/Shanghai" 等
    value           DOUBLE,
    value_unit      TEXT,                   -- "percent" / "USD_per_barrel" / "index_points"
    value_raw       TEXT,                   -- 原始字符串（审计用）
    source          TEXT,
    realtime_start  DATE,                   -- FRED vintage；非 FRED 来源为 NULL
    vintage_as_of   DATE,                   -- 数据"被知晓"的日期
    utc_ts          TIMESTAMPTZ NOT NULL,   -- 入库时刻（UTC）
    fetched_at      TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (indicator_id, period_date, source)
);

-- 云巨头季度 CapEx（单季反算，哈希去重）
CREATE TABLE IF NOT EXISTS capex_quarterly (
    company         TEXT        NOT NULL,   -- "MSFT"/"AMZN"/"GOOGL"/"META"
    cik             TEXT        NOT NULL,
    fiscal_quarter  TEXT        NOT NULL,   -- "2026Q1"
    period_end      DATE        NOT NULL,
    capex_usd       DOUBLE,                 -- 单季值（正数），已反算
    capex_yoy_pct   DOUBLE,                 -- 同比增速 vs 去年同季
    filing_form     TEXT,                   -- "10-Q" / "10-K"
    source          TEXT,
    source_hash     TEXT,                   -- SHA-256（原始 JSON）用于幂等导入
    fetched_at      TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (company, fiscal_quarter, source)
);

-- FOMC 日历（静态预填充 + 决议后更新）
CREATE TABLE IF NOT EXISTS fomc_calendar (
    meeting_date    DATE        PRIMARY KEY,
    meeting_type    TEXT,                   -- "scheduled" / "emergency"
    decision_date   DATE,
    rate_decision   TEXT,                   -- "hold"/"hike_25"/"cut_25" 等；决议前 NULL
    target_lower    DOUBLE,
    target_upper    DOUBLE,
    source          TEXT,
    updated_at      TIMESTAMPTZ
);

-- 宏观门控状态（自动计算，手动覆盖保留为逃生口）
CREATE TABLE IF NOT EXISTS macro_regime (
    as_of_date          DATE        PRIMARY KEY,
    capex_state         TEXT,               -- "green"/"yellow"/"red"/"stale"
    yield_curve_state   TEXT,               -- "normal"/"flat"/"inverted"/"stale"
    risk_state          TEXT,               -- "risk_on"/"risk_off"/"neutral"/"stale"
    composite_state     TEXT,               -- "green"/"yellow"/"red"/"stale"
    capex_as_of         TEXT,               -- "2026-Q1"（明确披露时效滞后）
    yield_as_of         DATE,
    computed_at         TIMESTAMPTZ NOT NULL
);
```

---

## 参考

- `docs/macro-market-indicator-matrix.md` — 数据源权威文档（Groups I–O）
- `docs/data-source-matrix.md` — A 股数据源矩阵（stock-data-agent 参考）
- ADR-003：宏观 CapEx 门控逻辑定义
- ADR-006：四层工具封装路线 + 防幻觉机制
- `engine/data_agent/fields.py` — FieldGroup / SourcePolicy 模式（本 ADR 的 `indicator_groups.py` 镜像此设计）
- `engine/data_agent/sources/base.py` — `AbstractSource` 基类（宏观 sources 继承此类）
