# ADR-006：AI 集成层架构——工具封装、知识图谱与推理 Agent

- **状态**：已采纳
- **日期**：2026-05-16
- **决策者**：Daniel Wong

## 背景

`data_agent`（Phase 0–5）完成后，面临四个新问题：

1. 如何把数据层暴露给三类调用方：Cron Job / Web 页面 / AI 推理 Agent
2. 哪些数据需要向量化，哪些不需要
3. 推理 Agent 是否引入图数据库来替代或补充向量数据库
4. 如何防止推理 Agent 的语义漂移（幻觉式财务数据引用）

本 ADR 同时决定 Qlib 和 Bloomberg 参考库的融合策略，以及参考 `~/Dev/math-to-go`
harness 模式的防漂移机制设计。

---

## 决策一：工具封装分层

### 可选方案

| 方案 | 适合场景 | 问题 |
|------|----------|------|
| CLI only | Cron | 已完成，但 Web/AI 无法调 |
| MCP Server | 人机交互（Claude Desktop） | 不适合 Cron/程序化 pipeline |
| FastAPI | Web + Cron-via-HTTP | 需要常驻服务 |
| SDK tool_use | 程序化 AI Pipeline | 无 UI，纯代码 |

### 决策：四层并存，互不替代

```
Cron Job    → CLI（已有，uv run refresh-data-agent）
Web UI      → FastAPI（engine/api/）                    Phase 6
Claude 交互 → MCP Server（engine/mcp/）                 Phase 7
AI Pipeline → LangGraph + ReAct Agent（engine/agents/） Phase 9
```

三套新封装均调用同一 `Storage` + `StockDataOrchestrator` Python 层，**不重复实现业务逻辑**。

---

## 决策二：图数据库 + 向量数据库混合存储

### 问题背景

推理场景有两类本质不同的查询，无法互相替代：

1. **关系遍历**："CPO 主题有哪些股，其机构持仓如何变化？谁是中际旭创的上游？"
   → 图遍历问题，SQL 无法表达多跳关系，向量近似无法给出精确路径
2. **语义召回**："年报中关于 800G 量产时间表的段落？"
   → 向量近似问题，图结构无法实现开放语义检索

### 存储边界决策

| 数据类型 | 存储 | 理由 |
|----------|------|------|
| OHLCV / K 线 | DuckDB | SQL 精确查询 |
| 财务指标 | DuckDB | 数值过滤/排序 |
| 主营构成、股东持仓 | DuckDB（原始）+ Neo4j（关系） | 双写：SQL 查原始，图查关系 |
| 股票-行业-概念 关系 | Neo4j KG | 关系遍历，supply chain |
| 年报 / 季报全文 | LanceDB | 语义段落召回 |
| 研报 / 分析师报告 | LanceDB | "找看多光模块研报" |
| 公告 / 新闻文本 | LanceDB | 事件检索、情绪分析 |
| markdown 调研文档 | LanceDB | RAG 喂给推理 Agent |

### 图数据库选型：Neo4j Community Edition 5.x（Docker）

**否决 KuzuDB**：KuzuDB 于 2025 年 10 月被 Apple 收购并 archive，无上游维护，
不适合生产投资工具。此结论与 `math-to-go` ADR-004 一致。

**选 Neo4j CE 的理由：**
- Cypher 为行业标准，LLM 可直接生成合法 Cypher 语句
- `langchain-neo4j` 提供 `GraphCypherQAChain`（read-only 安全模式），无需直接暴露 Cypher API
- Neo4j v5.11+ 内置 vector index，未来可在单个查询内合并 KG + 向量
- 与 `math-to-go` 共用 Docker 运行环境，无新基础设施负担

**Investment KG Schema：**

```cypher
// 节点类型
(:Stock {code, name, exchange, board, scarcity, rating, active})
(:Sector {id, name})
(:SubSector {id, name})
(:Concept {id, name, description, theme})  // "cpo", "hbm", "800g", "国产替代"
(:Institution {name, holder_type})           // 公募基金 | 北向资金 | 险资 | 产业资本
(:Document {doc_id, title, doc_type, pub_date, source, chunk_count})

// 关系类型
(:Stock)-[:BELONGS_TO]->(:SubSector)-[:PART_OF]->(:Sector)
(:Stock)-[:EXPOSED_TO {weight: FLOAT, as_of: DATE}]->(:Concept)
(:Stock)-[:SUPPLIES {segment: STRING, as_of: DATE}]->(:Stock)   // 供应链方向
(:Stock)-[:COMPETES_WITH]->(:Stock)
(:Institution)-[:HOLDS {hold_ratio: FLOAT, report_date: DATE}]->(:Stock)
(:Document)-[:ABOUT]->(:Stock)
(:Document)-[:MENTIONS]->(:Concept)
```

**KG 节点数据来源：**
- `Stock`：`data/agent_input/cn/stocks.yaml`
- `Institution`：DuckDB `stock_shareholders.holder_name`（去重）
- `Concept`：手动维护 `data/kg_seed/concepts.yaml`
- `Document`：Phase 8b ingest 时创建

### 向量存储：LanceDB + BGE-M3 本地模型

**Embedding model**：`BAAI/bge-m3`（本地，无 API 费用）
- 与 `math-to-go` 共用 `~/.cache/huggingface/` 模型 cache，无需重复下载
- Reranker：`BAAI/bge-reranker-v2-m3`（同系列，与 LanceDB ANN 配合使用）

**否决 voyage-finance-2**：需要 API 调用费用，本地模型在中文金融文本上性能相当。

**PDF 解析**：`pymupdf`（fitz），而非 `pdfplumber`
- 解析速度快 10-100 倍
- 更好支持复杂表格结构（年报中财务报表的主要来源）

**文档来源**：CNINFO 爬虫自动下载
- 扩展现有 `engine/data_agent/sources/cninfo.py`，新增 `fetch_annual_report_pdf(code, year)` 方法
- 滑动窗口切分：800 tokens，128 overlap（保留表格上下文）

---

## 决策三：推理 Agent 框架——LangGraph + ReAct + Harness

### LangGraph StateGraph（参考 math-to-go ADR-007）

Phase 9 使用 LangGraph v0.3+ `StateGraph`，节点为纯函数 `(state) → partial_state`，
与 `math-to-go` 中 `review_graph`、`exercise_graph` 的模式完全一致。

**StateGraph 拓扑：**

```
session_init
    │
    ├─[data_only]──────────────────────────────────────────────────┐
    ├─[kg_first]───► kg_retrieval ──► react_reasoner ─────────────┤
    ├─[rag_first]──► rag_retrieval ─► react_reasoner ─────────────┤
    └─[kg+rag]────► kg_retrieval ──► rag_retrieval ─► react_reasoner ►│
                                                                    │
                                                          draft_generator
                                                                │
                                                          fact_evaluator
                                              ┌───────────────┴──────────────────┐
                                      [score<75, retry<2]              [score≥75 or retry≥2]
                                              │                                   │
                                       draft_generator                  citation_formatter
                                       (with critique)                            │
                                                                           session_close → END
```

**ReAct 模式**：`react_reasoner` 节点在内部实现 thought/action/observation 循环，
每步追加到 `react_steps: Annotated[list[dict], operator.add]`（append-only，无法回溯修改）。
工具调用使用参数化函数（`tools.py` 注册表），不允许 freeform SQL 或 Cypher，防止 prompt injection。

### Harness 层：四个防语义漂移机制

投资域语义漂移的具体表现：捏造 PE 值、引用过期或不存在的目标价、混淆股票代码。

**机制一：`FrozenMarketSnapshot`（数据注入冻结）**

`session_init` 节点在 graph 执行开始时，一次性从 DuckDB 读取所有相关数值并冻结为
`FrozenMarketSnapshot` TypedDict。任何后续 LLM 节点不得修改此 dict，只能读取。
LLM 上下文中明确注明各字段的截止时间（`snapshot_as_of`），超过 24 小时的字段自动
打上 `[stale]` 标记，要求 LLM 在分析中注明数据截止日期。

等同于 `math-to-go` 的 SESSION_NOTES.md 冻结注入模式（ADR-007 §3.2）。

**机制二：`tool_output_schemas.py`（工具输出 Pydantic 验证）**

所有工具函数返回 Pydantic 模型而非原始 dict：
- `None` 字段显式声明（防止 LLM 对缺失字段作出假设）
- 类型约束在 Python 层强制执行，非 LLM prompt 层
- 工具调用失败时返回带 `error` 字段的模型，而非 raise exception（保持 ReAct 循环可继续）

**机制三：`claim_verifier.py`（事后确定性校验）**

`fact_evaluator` 节点调用此模块对 `draft_analysis` 进行非 LLM 的确定性检查：
- 用正则提取所有量化断言（数字、百分比、日期、股票代码）
- 逐一回溯到以下允许来源之一：`market_data` snapshot 字段、`rag_sources` 引用的 chunk、`kg_subgraph` 中的关系事实
- 无法回溯的断言加入 `factual_errors`，触发 generator 重试（最多 2 次）

等同于 `math-to-go` 用 `sympy` 进行数学输出的代数验证（ADR-007 §4.1）。

**机制四：`prompt_contracts.py`（Prompt 版本哈希）**

每个节点的 system prompt 存储为带版本的字符串常量，SHA-256 哈希在 `session_close`
节点写入 `analysis_sessions` DuckDB 表。可审计"哪次分析使用了哪版 prompt"，
支持 prompt 变更的 A/B 对比。

### `AnalysisState` 核心结构

```python
class FrozenMarketSnapshot(TypedDict):
    codes: list[str]
    quote_snapshot: dict         # {code: {price, pct_change, pe, pb, market_cap}}
    fundamentals_snapshot: dict  # {code: {roe, net_margin, revenue_growth}}
    fund_flow_snapshot: dict     # {code: {main_net_inflow_5d}}
    shareholder_snapshot: dict   # {code: [{holder_name, hold_ratio}]}
    snapshot_as_of: str          # ISO 8601 datetime
    snapshot_staleness_hours: float

class AnalysisState(TypedDict):
    query: str
    query_codes: list[str]
    market_data: FrozenMarketSnapshot        # 冻结，任何节点不得修改
    kg_subgraph: dict
    kg_cypher_used: str                      # 审计用
    rag_chunks: list[dict]
    rag_sources: list[str]
    react_steps: Annotated[list[dict], operator.add]    # append-only
    tool_calls_made: Annotated[list[str], operator.add] # append-only
    draft_analysis: str
    evaluation_result: dict   # {score: int, critiques: list, factual_errors: list}
    final_analysis: str
    citations: list[dict]     # [{claim, source_doc_id, source_field}]
    routing_decision: str     # "kg_first"|"rag_first"|"data_only"|"kg+rag"
    retry_count: int
    error: str | None
```

---

## 决策四：Qlib / Bloomberg 融合

**Qlib**：ADR-001 已决定不引入（"引入 Qlib 反而增加维护负担"）。该决定维持不变。
若未来需要 ML 因子信号，单独引入 `lightgbm`，不捆绑 Qlib 框架。

**Bloomberg 参考库**：作为字段命名规范参考，在 `engine/data_agent/bloomberg_compat.py`
维护 Bloomberg field → 本地 DuckDB 字段的映射表。未来若有 blpapi 访问权限，
通过此映射层对接，核心存储层**零改动**。

---

## 实施计划

| Phase | 内容 | 新依赖 |
|-------|------|--------|
| 6 | FastAPI 服务层（engine/api/） | fastapi>=0.111, uvicorn>=0.29 |
| 7 | MCP Server（engine/mcp/） | mcp>=1.0 |
| 8a | Neo4j KG（engine/kg/） | neo4j>=5.28, langchain-neo4j>=0.3, pydantic-settings>=2.0 |
| 8b | LanceDB RAG（engine/rag/） | lancedb>=0.9, FlagEmbedding>=1.2, torch>=2.2, pymupdf>=1.24, tantivy>=0.22 |
| 9 | LangGraph Agent + Harness（engine/agents/） | langgraph>=0.3, langchain-core>=0.3, langchain-anthropic>=0.3, langgraph-checkpoint-sqlite>=2.0 |

推荐开发顺序：Phase 7 → Phase 6 → Phase 8a → Phase 8b → Phase 9

---

## 后果

- ✅ 四类调用方都有清晰的接入路径，无强耦合
- ✅ Neo4j KG 补充 SQL 的关系遍历能力（供应链、机构持仓图谱）
- ✅ LanceDB 补充 Neo4j 的语义召回能力——两个存储各司其职
- ✅ Harness 四机制系统性消除投资域特有的幻觉风险
- ✅ BGE-M3 本地运行无 API 费用，与 math-to-go 共用 model cache，无新基础设施
- ✅ LangGraph 与 math-to-go 使用相同框架，Daniel 已有实操经验
- ⚠️ Neo4j 需要 Docker 容器（math-to-go 环境已有，新增 service 即可）
- ⚠️ torch + FlagEmbedding 依赖体积约 2GB（可拆分为独立 `embedder` optional group）
- ⚠️ MCP + FastAPI + LangGraph 三套封装需分别维护（共享底层 Storage，维护量小）
