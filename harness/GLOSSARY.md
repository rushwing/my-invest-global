# my-invest-global 项目本体词汇表（Ontology Glossary）

> **用途**：后端开发、Agent设计、Phase规划、API字段命名共用同一份本体定义，消除语义漂移。
>
> **规范**：
> - 代码/API/文件字段名：使用**英文标识符**（snake_case）
> - 用户界面标签：使用**中文**，以表格「UI 标签」列为准
> - 如一个概念有多种中文说法，本表选定唯一正式用法，其他列为禁用词
>
> **机器可读枚举**：FSM状态、owner、priority等枚举见 `harness/req-constants.sh`

---

## §1 投资组合术语（Portfolio Terms）

| 英文标识符 | UI 标签 | 定义 | 禁用词（勿混用）|
|-----------|--------|------|--------------|
| `white_horse` | 白马股 | 高质量稳健型持仓，目标≤2/3总仓位（约67%）。特征：高ROE、行业龙头、紧缺度Tier-1/2、估值合理。 | 蓝筹股、稳健股、核心仓 |
| `elastic` | 弹性股 | 高成长弹性型持仓，目标≤1/3总仓位（约33%）。特征：受CapEx/AI算力周期驱动，Beta较高，波动较大。 | 成长股、弹性仓、弹性仓位 |
| `holding` | 持仓（单行） | `HoldingsFile` CSV中的单行记录，代表当前持有的一只股票，含代码、成本价、市值、类别。 | 仓位（泛指）、头寸、position |
| `holdings` | 持仓列表 | 当日全量持仓记录，来源于`HoldingsFile`，是runner的主要输入。 | 仓位列表、portfolio（泛指）|
| `holding_category` | 持仓类别 | `HoldingRow.category`字段，枚举：`white_horse` / `elastic`。 | 类型、股票类别 |
| `macro_state` | 宏观状态 | CapEx周期状态，三值枚举：`GREEN` / `YELLOW` / `RED`。驱动弹性股目标仓位比例。存储于`MacroStateFile`。 | state（FSM另有含义）、宏观周期、周期状态 |
| `rebalance` | 再平衡 | `check_portfolio_balance()`返回`rebalance_needed=True`时触发的调仓**建议**，非实际交易指令。 | 调仓、平衡、balance（名词）|
| `elastic_ratio` | 弹性占比 | 弹性股总市值 / 全部持仓总市值，实时计算值。 | 弹性比例（可）、弹性仓位比 |
| `white_horse_ratio` | 白马占比 | 白马股总市值 / 全部持仓总市值，实时计算值。 | 白马比例（可）|
| `scarcity_tier` | 紧缺度等级 | 行业供需紧缺程度，枚举：`Tier-1`（最紧缺）到 `Tier-4`（充裕）。影响`fundamental_score`。 | 稀缺度、紧缺级别 |

---

## §2 宏观状态枚举（Macro State Enum）

| `macro_state`值 | 弹性股目标仓位 | 触发条件 | 颜色指示 |
|----------------|------------|---------|--------|
| `GREEN` | 38% | CapEx指引强劲上调，大厂算力支出加速信号（NVDA/AVGO/MSFT CapEx超预期）| 绿 |
| `YELLOW` | 33% | 默认状态，CapEx信号中性或信号混乱 | 黄 |
| `RED` | 20% | CapEx指引下修，防御性收缩弹性暴露（大厂削减支出或暂停采购）| 红 |

手动覆盖：`python -m engine.portfolio.macro_gate --set green|yellow|red`

---

## §3 信号术语（Signal Terms）

信号是量化打分系统的三个分支，每支独立计算后融合为综合评分。

| 英文标识符 | UI 标签 | 融合权重 | 来源Phase | 接口方法 | 定义 |
|-----------|--------|---------|----------|---------|------|
| `technical_score` | 技术信号 | 30% | Phase 2 | `SignalProvider.compute_score(code, date)` | 基于MACD金叉/死叉、RSI超买超卖（14日）、布林带位置计算的0–100分值 |
| `fundamental_score` | 基本面信号 | 40% | Phase 3 | `SignalProvider.compute_score(code, date)` | 基于PE百分位、ROE趋势、紧缺度等级、目标价上行空间计算的0–100分值 |
| `sentiment_score` | 情绪信号 | 30% | Phase 4 | `SignalProvider.compute_score(code, date)` | 基于相关新闻情绪、KOL表态、美股隔夜涨跌计算的0–100分值 |
| `composite_score` | 综合评分 | — | Phase 5 | runner内部计算 | `technical_score×0.30 + fundamental_score×0.40 + sentiment_score×0.30`，取值0.0–100.0 |

**禁止同义词**：
- 不得单独用 `score` 代替任一具体分值（`score`单独使用语义不明确）
- 不得用 `signal` 代替 `action_code`（`signal`是0–100分数；`action_code`是操作指令字符串）
- 代码中禁用 `signal_a` / `signal_b` / `signal_c` 字母编号

---

## §4 操作码术语（Action Code Terms）

`action_code`是机器可读的操作建议字符串枚举，存储于`SignalsFile.stock_signals[].action_code`，驱动策略简报生成和Streamlit仪表盘色标。

### 基础映射（由`composite_score`决定）

| `action_code`值 | 触发条件 | 中文建议 | UI 颜色 |
|----------------|---------|---------|--------|
| `strong_add` | `composite_score ≥ 75` | 强烈加仓 | 红色 |
| `hold_add` | `60 ≤ composite_score < 75` | 持有/小幅加仓 | 琥珀色 |
| `hold` | `40 ≤ composite_score < 60` | 持有观望 | 灰色 |
| `reduce` | `composite_score < 40` | 减仓 | 蓝色 |

### 特殊覆盖（优先级高于基础映射）

| `action_code`值 | 触发条件 | 优先级 | UI 颜色 |
|----------------|---------|-------|--------|
| `stop_loss` | 当前价跌破买入成本价×(1-8%) | **最高**，覆盖所有基础码 | 深红色 |
| `take_profit_alert` | 当前价超买入成本价×(1+20%) | 附加（不替换基础码，并列输出）| 金色 |
| `macro_red` | `macro_state=RED` AND `holding_category=elastic` | 次高，降一级基础码（`strong_add`→`hold_add`，`hold_add`→`hold`，`hold`→`reduce`）| 橙色 |

**禁止**：不得用 `signal` 代替 `action_code`；不得用 `recommend` / `recommendation` 作字段名（`action_code`是字段名，`recommendation`是生成的Markdown文件）。

---

## §5 文件契约术语（File Contract Terms — ADR-002）

所有文件路径均为项目根目录相对路径。

| 英文标识符 | 文件路径模板 | Pydantic Schema | 写入方 | 读取方 |
|-----------|------------|----------------|------|------|
| `SignalsFile` | `data/processed/signals_{YYYYMMDD}.json` | `engine.schemas.SignalsFile` | `engine.runner.run_daily_pipeline()` | Streamlit dashboard, Phase 6 synthesis |
| `DailyNewsFile` | `data/processed/daily_news_{YYYYMMDD}.json` | `engine.schemas.DailyNewsFile` | news agent (Phase 4) | `sentiment_score` provider |
| `WeeklyReportFile` | `data/processed/weekly_report_{YYYYMMDD}.json` | `engine.schemas.WeeklyReportFile` | weekly report agent | KOL/情绪分析 |
| `HoldingsFile` | `data/agent_input/cn/holdings_{YYYYMMDD}.csv` | `engine.schemas.HoldingRow`（per row）| 人工维护 | `run_daily_pipeline()` |
| `MacroStateFile` | `data/cache/macro_state.json` | `{"state": "GREEN"\|"YELLOW"\|"RED"}` | `engine.portfolio.macro_gate` | `run_daily_pipeline()` |
| `recommendations` | `data/processed/recommendations_{YYYYMMDD}.md` | Markdown（自由格式）| Phase 6 Claude API synthesis | Streamlit Tab 2 |

**日期格式**：文件名中日期格式统一为`YYYYMMDD`（无分隔符），如`signals_20260513.json`。

---

## §6 数据层术语（Data Layer Terms）

| 英文标识符 | 模块路径 | 定义 |
|-----------|---------|------|
| `Storage` | `engine.data_agent.storage.Storage` | DuckDB持久化类，数据库文件路径`data/db/aidc.duckdb` |
| `FieldGroup` | `engine.data_agent.fields.FieldGroup` | 数据组枚举（quotes/prices/fundamentals/fund_flow/shareholders/announcements/…）|
| `DataProvenance` | `engine.schemas.DataProvenance` | 来源追踪元数据（source, as_of, fetched_at, confidence）|
| `StockDataOrchestrator` | `engine.data_agent.orchestrator.StockDataOrchestrator` | 数据采集调度器，协调多数据源并发拉取 |
| `SignalProvider` | `engine.signals.protocol.SignalProvider` | 信号计算接口（Protocol），`compute_score(code:str, date:str) -> float` |
| `StubSignalProvider` | `engine.signals.stub.StubSignalProvider` | 固定分值测试桩，用于Phase 5集成测试，不依赖真实市场数据 |

---

## §7 Phase 8a — 知识图谱术语（KG Terms，前瞻定义）

> 本节为Phase 8a开发预定义，当前版本不实现。

**Neo4j CE节点类型**（ADR-006决策，KuzuDB已否决）：

| 节点标签 | 关键属性 | 用途 |
|---------|---------|------|
| `(:Stock)` | code, name, exchange, board | 股票实体 |
| `(:Sector)` | id, name | 行业 |
| `(:SubSector)` | id, name | 子行业 |
| `(:Concept)` | id, name, theme | 主题概念（CPO/HBM/800G等）|
| `(:Institution)` | name, holder_type | 机构股东（公募/北向/险资）|
| `(:Document)` | doc_id, doc_type, pub_date | 文档节点（年报/研报）|

**关系类型**：`BELONGS_TO`、`PART_OF`、`EXPOSED_TO`、`SUPPLIES`、`COMPETES_WITH`、`HOLDS`、`ABOUT`、`MENTIONS`

**Cypher访问**：通过`langchain-neo4j.GraphCypherQAChain`只读模式，禁止Agent直接写入。

---

## §8 Phase 8b — RAG术语（前瞻定义）

> 本节为Phase 8b开发预定义，当前版本不实现。

| 英文标识符 | 定义 |
|-----------|------|
| `chunk` | PDF切分段落，800 tokens / 128 overlap（LanceDB存储单元）|
| `embedding` | BAAI/bge-m3本地模型向量（`~/.cache/huggingface/`共用缓存）|
| `rag_source` | RAG召回块的文档引用（doc_id + chunk偏移），用于claim_verifier回溯 |
| `reranker` | BAAI/bge-reranker-v2-m3，对候选chunk精排 |

**文档解析**：`pymupdf`（fitz），禁止使用`pdfplumber`（慢10-100倍）。

---

## §9 Phase 9 — LangGraph Agent Harness术语（前瞻定义）

> 本节为Phase 9开发预定义，当前版本不实现。与ADR-006 §3对应。

| 英文标识符 | 定义 |
|-----------|------|
| `FrozenMarketSnapshot` | `session_init`节点从DuckDB一次性读取并冻结的市场数据快照，后续LLM节点只读不写 |
| `AnalysisState` | LangGraph `StateGraph`的状态`TypedDict`，含`market_data`、`kg_subgraph`、`rag_chunks`、`react_steps`等字段 |
| `react_steps` | `Annotated[list[dict], operator.add]`，ReAct循环的append-only步骤日志，不可回溯修改 |
| `claim_verifier` | `fact_evaluator`节点调用的确定性验证器，回溯量化断言到`market_data` / `rag_sources` / `kg_subgraph` |
| `tool_output_schemas` | 所有工具函数的Pydantic返回模型，`None`字段显式声明，防止LLM对缺失字段作假设 |
| `prompt_contracts` | 每个节点的system prompt存储为带版本字符串常量，SHA-256哈希写入`analysis_sessions` DuckDB表 |
| `routing_decision` | 路由枚举：`data_only` / `kg_first` / `rag_first` / `kg+rag` |

---

## §10 消歧义速查（Disambiguation）

> **开发时如果拿不准用哪个词，查这一节。**

| ❌ 禁用/含糊 | ✅ 正式用法 | 说明 |
|------------|-----------|------|
| `signal`（单独）| `technical_score` / `fundamental_score` / `sentiment_score` / `action_code` | 视上下文明确；`signal`单独使用歧义极大 |
| `signal A/B/C` | `technical_score` / `fundamental_score` / `sentiment_score` | 代码中禁用字母编号 |
| `state`（单独）| `macro_state` | `state`在REQ FSM中另有含义，必须用全称 |
| `score`（单独）| `composite_score`或具体分值 | 必须指明是哪种score |
| `balance`（名词）| `check_portfolio_balance()`返回值 | 始终使用函数全名 |
| `position`（英文）| `holding`（个股）/ `holdings`（列表）/ `elastic_ratio`（比例）| position歧义大；按上下文选择正确词 |
| `弹性仓` | `elastic`（代码）/ 弹性股（UI）| 弹性是持仓类别，不是仓位大小 |
| `持仓比例`（泛指）| `elastic_ratio` 或 `white_horse_ratio` | 必须指明是哪类比例 |
| `recommend` / `recommendation`（字段名）| `action_code`（字段）/ `recommendations_{date}.md`（文件）| 区分字段名和文件名 |
| `signal_a` / `signal_b` / `signal_c` | `technical_score` / `fundamental_score` / `sentiment_score` | 代码中禁用字母编号 |
| `portfolio`（泛指）| `holdings`（持仓列表）/ `SignalsFile`（输出）/ 视上下文 | 英文portfolio在中文股票场景歧义大 |
| `macro` | `macro_state`（代码字段全称）| 必须用全称 |

---

## §11 需求流程词汇（Harness Process Terms）

> **机器可读来源：`harness/req-constants.sh`**（validator从该文件source枚举值）。
> 新增状态或角色时，**先改`req-constants.sh`，再改本表和`requirement-standard.md`**，防止三处漂移。

### REQ `status`枚举值

| 值 | Owner（frontmatter） | 含义 |
|----|----------------------|------|
| `draft` | `human-001` | 需求草稿，尚未进入agent工作流 |
| `req_review` | `optimizer-001` ↔ `evaluator-001` | Optimizer设计需求文本，Evaluator审核，迭代直到通过 |
| `tc_design` | `evaluator-001` | Evaluator编写测试用例文本（TC文件）|
| `tc_review` | `optimizer-001` ↔ `evaluator-001` | Optimizer审核TC文本，迭代直到通过 |
| `tc_impl` | `optimizer-001` | Optimizer实现测试代码 |
| `tc_impl_review` | `evaluator-001` | Evaluator审核测试代码，通过则进入`req_impl` |
| `req_impl` | `optimizer-001` | Optimizer实现需求，完成后开draft PR |
| `req_impl_review` | `evaluator-001` | Evaluator在draft PR上做审查，通过则`gh pr ready`进入`pr_draft` |
| `pr_draft` | `human-001` | PR已就绪（draft→ready），等待human-001合并 |
| `done` | — | PR已合并，所有关联bug已关闭 |
| `blocked` | `unassigned` | 外部阻塞或`review_round≥3`升级 |

### REQ `owner`枚举值

> **机器可读来源：`harness/agent-registry.yml`**。新增agent时只更新注册表，无需修改脚本或本表。

| 值 | 角色 | 含义 |
|----|------|------|
| `optimizer-001` | optimizer | Claude Code（当前会话）负责（需求设计、实现）|
| `evaluator-001` | evaluator | Claude（独立会话）或Codex负责（需求审核、TC设计、代码审查）|
| `human-001` | human | Daniel负责（范围审批、合并）|
| `unassigned` | — | 未分配（`draft`和`blocked`状态允许）|

### REQ `tc_policy`枚举值

| 值 | 含义 |
|----|------|
| `required` | 必须有测试用例（默认）|
| `optional` | 建议但非强制（纯接口/协议定义时使用）|
| `exempt` | 明确豁免，须填写`tc_exempt_reason` |

### BUG `status`枚举值

| 值 | 含义 |
|----|------|
| `open` | 已发现，待处理 |
| `in_progress` | 正在修复 |
| `blocked` | 有外部依赖阻塞 |
| `resolved` | 代码已修复，待验证 |
| `closed` | 修复验证通过 |
