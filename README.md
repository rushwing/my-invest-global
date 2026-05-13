# my-invest-global

> 中美 AI 数据中心（AIDC）产业链研究 + 大 A AI 基建股持仓顾问工具

数据截止：2026-05-13 | 仅供研究参考，不构成投资建议

---

## 项目定位

本项目分两个层次：

1. **研究层**：基于时寒冰《全球视野下的投资机会》方法论，对中美 AIDC 产业链 47 家核心标的进行全景分析
2. **顾问工具层**（建设中）：消费 Codex Agent 产出的结构化数据，结合持仓情况，给出 AI 基建股交易策略建议（不做自动执行）

---

## 架构总览

```
╔══════════════════════════════════════════════════════════════════╗
║  外部数据源（Codex Agent 负责采集，本工具只消费）                   ║
║  Daily News Agent      Weekly Report Agent     Holdings OCR Agent ║
║  Yahoo/东财/腾讯        行业研报 + 大V简报       截图 → 结构化CSV  ║
╚══════════════════╦═══════════════╦═════════════════╦═════════════╝
                   ▼               ▼                 ▼
╔══════════════════════════════════════════════════════════════════╗
║  data/agent_input/  （文件系统接口契约，详见 ADR-002）             ║
║  daily_news_{date}.json  |  weekly_report_{week}.json           ║
║  kol_digest_{date}.json  |  holdings_{date}.csv                 ║
╚══════════════════════════════╦═══════════════════════════════════╝
                               │ watchdog 监听触发
╔══════════════════════════════▼═══════════════════════════════════╗
║  AI 基建股持仓顾问核心引擎                                          ║
║  Signal A 技术分析（pandas-ta）30%                                ║
║  Signal B 基本面（紧缺度 × 目标价空间 × 财报超预期）40%             ║
║  Signal C 情绪/新闻（Codex agent 输出）30%                        ║
║  仓位框架：2/3 白马股 + 1/3 弹性股（动态 ±10%）                   ║
║  Claude API → 自然语言每日策略简报                                 ║
║  存储：DuckDB + Parquet（本地，免服务器）                           ║
╚══════════════════════════════╦═══════════════════════════════════╝
                               ▼
╔══════════════════════════════════════════════════════════════════╗
║  Streamlit 仪表盘（4 Tab）                                        ║
║  持仓总览 | 每日策略简报 | 个股深度 | 信号仪表盘                   ║
╚══════════════════════════════════════════════════════════════════╝
```

详细架构说明：[docs/architecture.md](docs/architecture.md)
技术选型决策：[docs/adr/](docs/adr/)

---

## 研报文件

| 文件 | 说明 |
|---|---|
| [aidc_report.html](aidc_report.html) | 自包含 HTML 全景研报（直接浏览器打开） |
| [methodology.md](methodology.md) | 时寒冰投资方法论框架 |
| [data_china_aidc.md](data_china_aidc.md) | 中国 A 股数据表（29 家标的，13 列） |
| [data_us_aidc.md](data_us_aidc.md) | 美股数据表（18 家标的，13 列） |

覆盖板块：光通信 / 半导体 / AI 服务器 / 网络 / PCB 基材 / 散热液冷 / 电源 / 机柜基建

---

## Codex Agent 接口规约

本工具从以下路径读取 Codex Agent 产出文件（路径约定，不提交实际数据）：

```
data/agent_input/
  daily_news_{YYYYMMDD}.json       # 财经新闻（隔夜美股优先）
  weekly_report_{YYYYWW}.json      # 行业研报 + 大V简报
  kol_digest_{YYYYMMDD}.json       # 韭圈儿 / Trader韭等
  holdings_{YYYYMMDD}.csv          # OCR Agent 解析持仓截图
```

JSON Schema 和 CSV Schema 详见 [ADR-002](docs/adr/ADR-002-data-pipeline-interface.md)

---

## 投资组合框架

| 类别 | 目标权重 | 代表标的 |
|---|---|---|
| 白马股（高确定性龙头） | ~67% | 中际旭创、澜起科技、北方华创、深南电路、英维克、浪潮信息 |
| 弹性股（高 beta 成长） | ~33% | 星融元、天孚通信（CPO）、剑桥科技（OCS）、高澜股份、寒武纪 |

宏观 CapEx 周期加速时弹性股可上调至 40%，板块回调 >15% 时降至 20%。
详见 [ADR-003](docs/adr/ADR-003-portfolio-framework.md)

---

## ADR 索引

| ADR | 决策 |
|---|---|
| [ADR-001](docs/adr/ADR-001-tech-stack.md) | 技术栈选型：Python + pandas-ta + DuckDB + Streamlit |
| [ADR-002](docs/adr/ADR-002-data-pipeline-interface.md) | 数据管道接口：文件系统契约 + watchdog |
| [ADR-003](docs/adr/ADR-003-portfolio-framework.md) | 投资组合框架：2/3 白马 + 1/3 弹性，动态 ±10% |
| [ADR-004](docs/adr/ADR-004-analysis-engine.md) | 分析引擎：三信号融合 + Claude API 生成简报 |
| [ADR-005](docs/adr/ADR-005-frontend-dashboard.md) | 前端仪表盘：Streamlit，参考 FinceptTerminal UX |

---

## 免责声明

本项目所有内容仅供投资研究参考，不构成任何投资建议。股市有风险，入市须谨慎。
数据来源：各公司公开财报、Wind/iFinD、高盛/摩根士丹利/中信/中金等机构研报摘要。
