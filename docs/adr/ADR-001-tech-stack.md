# ADR-001：技术栈总体选型

- **状态**：已采纳
- **日期**：2026-05-13
- **决策者**：Daniel Wong

---

## 背景

需要为"大 A AI 基建股持仓顾问工具"选定技术栈。工具定位是：
- 消费 Codex Agent 产出的结构化数据（不自己爬虫/采集）
- 对持仓进行技术分析 + 基本面分析 + 情绪分析，输出策略建议
- 不做自动交易执行，人工最终决策
- 个人使用为主，未来可能扩展到小团队

核心约束：
- 开发效率优先（尽快上线核心功能）
- 无服务器基础设施依赖（本地运行）
- 与量化分析生态良好集成
- 为未来扩展预留接口

---

## 可选方案

### 维度一：核心语言

| 选项 | Pros | Cons |
|---|---|---|
| **Python（选定）** | 量化生态最完整（pandas/numpy/scipy）；AI/ML 生态（LLM SDK）；Streamlit/Plotly 原生支持；pandas-ta/yfinance 等工具 | 运行时性能不如 Rust/C++；GIL 限制并发 |
| TypeScript/Node | 前端集成好；异步 I/O 好 | 量化分析生态薄弱；需要大量 bridge 代码 |
| Python + Rust（PyO3） | 性能热点可 Rust 化 | 开发复杂度显著上升；过早优化 |

### 维度二：量化分析框架

| 选项 | Pros | Cons |
|---|---|---|
| **pandas-ta + 自定义（选定）** | 轻量、可控；专注技术分析指标；不引入不需要的组件 | 需要自己实现因子框架 |
| Qlib（完整平台） | 功能最全（因子/模型/回测/组合优化）；Microsoft 维护 | 杀鸡用牛刀——本工具不需要自动回测和模型训练；50 只股票小池易过拟合；引入大量不必要依赖 |
| vectorbt | 回测速度极快（numpy 向量化） | 侧重回测而非实时推荐；文档较少 |
| TA-Lib | 成熟稳定；C 实现性能好 | 需要编译安装（macOS 有时麻烦）；接口不够 Pythonic |

> **关键判断**：Qlib 的设计目标是"全自动量化研究平台"，覆盖从数据→因子→模型→回测→执行的完整链路。本工具只需要技术指标计算 + 规则打分，pandas-ta 完全够用，引入 Qlib 反而增加维护负担。未来若需要 ML 因子模型，可以单独引入 lightgbm，不需要捆绑整个 Qlib。

### 维度三：数据存储

| 选项 | Pros | Cons |
|---|---|---|
| **DuckDB + Parquet（选定）** | 无需安装服务；对 Parquet 的 OLAP 查询极快（列式存储）；SQL 接口友好；内存内计算；单文件部署 | 不支持高并发写入；不适合 OLTP 场景 |
| PostgreSQL + TimescaleDB | 成熟稳定；时序数据优化；多用户并发 | 需要安装和维护 PostgreSQL 服务；个人使用过重 |
| SQLite | 无服务器；成熟 | 列式查询慢；大数据量下性能差；无原生 Parquet 支持 |
| InfluxDB | 专为时序设计；查询语言优雅 | 需要单独服务；生态相对封闭 |

### 维度四：Agent 接口

| 选项 | Pros | Cons |
|---|---|---|
| **文件系统 JSON/CSV（选定）** | 零基础设施依赖；Codex agent 直接写文件即可；调试简单（文件可直接查看）；schema 版本化容易 | 无实时推送（需 watchdog 轮询）；不支持高频数据 |
| SQLite 共享数据库 | 事务安全；可查询历史；接口标准化 | Codex agent 需要写入同一 DB，耦合度提高 |
| Redis Streams | 实时推送；解耦彻底；持久化 | 需要 Redis 服务；对个人工具过重 |
| HTTP API（FastAPI） | 标准接口；语言无关 | 需要运行服务；增加部署复杂度 |

### 维度五：前端框架

见 [ADR-005](ADR-005-frontend-dashboard.md)

---

## 决策

**选定方案：Python + pandas-ta + DuckDB + Streamlit + 文件系统接口**

完整依赖栈：

```
核心分析
  pandas >= 2.0
  pandas-ta >= 0.3
  numpy >= 1.26

数据存储
  duckdb >= 0.10
  pyarrow >= 14.0  （Parquet 读写）

数据采集（按需，非强依赖）
  tushare            （价格数据）
  akshare            （备用数据源）

Agent 接口
  watchdog >= 4.0    （文件监听）

LLM 合成
  anthropic >= 0.25  （Claude API）

前端
  streamlit >= 1.32
  plotly >= 5.18

工具
  pydantic >= 2.0    （schema 验证）
  loguru             （日志）
  python-dotenv      （环境变量）
```

---

## Trade-off 推导

1. **为什么不用 Qlib**：Qlib 假设用户需要完整的量化研究链路（回测→组合优化→执行），本工具是"推荐辅助"而非"策略交易"，引入 Qlib 的收益 < 维护成本。pandas-ta 覆盖所有所需技术指标，未来若需 ML 因子，单独引入 lightgbm 即可。

2. **为什么不用 PostgreSQL**：个人开发阶段，DuckDB 的分析性能远超 SQLite，且无需运行服务。扩展到团队时，切换为 PostgreSQL 只需改数据层接口（已预留）。

3. **为什么文件系统而非 Redis**：Codex agent 只需写 JSON/CSV 文件，学习成本为零。watchdog 的轮询延迟对"每日策略建议"场景完全可接受（数据是每日批量，不是毫秒级）。

4. **为什么 pandas-ta 而非 TA-Lib**：macOS 上 TA-Lib 需要编译 C 依赖，安装繁琐。pandas-ta 是纯 Python，pip 一键安装，接口更 Pythonic，覆盖指标完整。

---

## 后果

- ✅ 开发速度快：Python 生态完善，无需配置服务器
- ✅ 调试友好：所有中间结果以文件/SQL 形式可查
- ✅ 扩展路径清晰：文件→Redis，DuckDB→PostgreSQL，Streamlit→React 均有明确升级路径
- ⚠️ 不适合高频/实时场景：watchdog 轮询延迟秒级；如需实时信号需升级到 Redis
- ⚠️ 并发写入限制：DuckDB 单写入进程；多 agent 并发写入需要文件锁机制
