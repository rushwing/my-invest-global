# 中国 AIDC 投资跟踪系统字段 × 数据源工具矩阵

更新时间：2026-05-16  
适用范围：约 47 只 A 股 AIDC 股票池、18 只美股观察池；A 股优先，港股/美股作为观察与备源扩展。

## 概述

### 数据源对比总结

| 数据源 | 最适合字段 | 优点 | 主要限制 | 建议角色 |
|--------|------------|------|----------|----------|
| 腾讯证券 HTTP | A 股实时行情、五档盘口、K 线、复权 K 线 | 免费、轻量、延迟低，当前仓库已使用 `web.ifzq.gtimg.cn` | 非正式公开服务，字段位置需校验，易受频控影响 | A 股行情主源、K 线主源 |
| 新浪财经 HTTP | A 股实时行情、五档盘口、日线备份 | `hq.sinajs.cn/list=` 简单稳定，适合多代码批量 | 需 UA/Referer 伪装；历史接口易封 IP | 实时行情备源 |
| 东方财富 Web API | 实时行情、财务、主营构成、资金流、股东、公告、研报、板块 | 字段覆盖最广，网页端数据丰富 | `push2/datacenter/emweb` 均为网页接口，字段名和签名可能变化 | 基本面、资金流、F10 主源 |
| AKShare | A 股/港股/美股封装、东财/新浪/巨潮封装 | 开发效率高，函数名清晰，当前项目已声明 `akshare>=1.12` | 版本依赖强，底层网页变化会破坏函数 | 工程封装层、备源聚合 |
| Tushare Pro | 规范化财务、复权因子、资金流、股东、指数 | 数据结构稳定、适合落库和回测 | 需 Token 与积分；实时能力弱 | 高质量盘后主备源 |
| 巨潮资讯 CNINFO | 公告、定期报告、信息披露 | 法定披露平台，公告权威 | 抓取需遵守 robots.txt 与访问节奏，公告 PDF 解析成本高 | 公告主源、财报原文校验 |
| Yahoo Finance | 美股观察池行情、K 线、财务、评级/目标价辅助 | 覆盖美股好，`yfinance` 生态成熟 | 非官方 API；`quoteSummary` 可能需要 Cookie/crumb | 美股观察池主源 |

> 说明：`hq.sinajs.cn` 属于新浪财经行情域名；腾讯侧本文使用 `qt.gtimg.cn` 与 `web.ifzq.gtimg.cn`。仓库当前脚本使用腾讯 `web.ifzq.gtimg.cn/appstock/app/fqkline/get` 获取行情/K 线，并使用东方财富 F10 `BusinessAnalysis/PageAjax` 获取主营构成。

### 标记说明

| 标记 | 含义 |
|------|------|
| ✅ 可用 · 接口 | 可直接获取，接口名或 URL 关键词写在后面 |
| ⚠️ 有限 · 说明 | 可获取但有延迟、字段不全、需页面解析或历史范围限制 |
| ❌ 不支持 | 该源不提供或不适合作为该字段来源 |
| 🔑 需Token · 接口 | 需注册 Token/API Key，括号内注明积分或权限 |

### 全局采集原则

| 场景 | 建议 |
|------|------|
| 交易时段实时行情 | 股票池按 15-25 只一组批量请求；主源失败后切备源；单源连续 3 次失败进入 5/15/30/60 秒指数退避 |
| 开盘/午盘敏感窗口 | 9:30-9:40、13:00-13:10 降低批量并发，优先核心 20 只；同源请求间隔不低于 1.0 秒 |
| 盘后补全 | 15:05 后固定采集全池日终行情、资金流、K 线、复权因子；17:00 后补财务/指标类数据 |
| Web scraping 接口 | 必须设置 UA/Referer，保留 Session，遇到 403/429 立即冷却 10-30 分钟；严禁高并发扫全市场 |
| 数据一致性 | 同一字段保留 `source`、`source_time`、`as_of_date`、`raw_payload_hash`；价格类用腾讯/新浪/东财交叉校验 |

## A. 实时/准实时行情（≤15 分钟延迟）

| 字段名 | 字段类型 | 腾讯证券API | 新浪财经API | 东方财富API | AKShare封装 | Tushare | 巨潮资讯CNINFO | Yahoo Finance | 备注 |
|--------|----------|-------------|-------------|-------------|-------------|---------|----------------|---------------|------|
| 最新价 | decimal | ✅ 可用 · `qt.gtimg.cn/q=` 或 `web.ifzq...qt` | ✅ 可用 · `hq.sinajs.cn/list=` | ✅ 可用 · `push2.eastmoney.com/api/qt/stock/get f43` | ✅ 可用 · `ak.stock_zh_a_spot_em()` | ⚠️ 有限 · `daily` 盘后 | ❌ 不支持 | ✅ 可用 · `v8/chart`/`v7/quote` | A 股主源腾讯，东财校验 |
| 涨跌幅 | decimal | ✅ 可用 · `qt.gtimg.cn` | ✅ 可用 · `hq.sinajs.cn` 计算 | ✅ 可用 · `f170` | ✅ 可用 · `stock_zh_a_spot_em()` | ⚠️ 有限 · `daily.pct_chg` 盘后 | ❌ 不支持 | ✅ 可用 · `regularMarketChangePercent` | 新浪常需自行计算 |
| 涨跌额 | decimal | ✅ 可用 · `qt.gtimg.cn` | ✅ 可用 · `hq.sinajs.cn` 计算 | ✅ 可用 · `f169` | ✅ 可用 · `stock_zh_a_spot_em()` | ⚠️ 有限 · `daily.change` 盘后 | ❌ 不支持 | ✅ 可用 · `regularMarketChange` | 单位统一为元/美元 |
| 开盘价 | decimal | ✅ 可用 · `qt.gtimg.cn` | ✅ 可用 · `hq.sinajs.cn` | ✅ 可用 · `f46` | ✅ 可用 · `stock_zh_a_spot_em()` | ⚠️ 有限 · `daily.open` 盘后 | ❌ 不支持 | ✅ 可用 · `v8/chart meta` | 盘中随源刷新 |
| 最高价 | decimal | ✅ 可用 · `qt.gtimg.cn` | ✅ 可用 · `hq.sinajs.cn` | ✅ 可用 · `f44` | ✅ 可用 · `stock_zh_a_spot_em()` | ⚠️ 有限 · `daily.high` 盘后 | ❌ 不支持 | ✅ 可用 · `v8/chart` | 日内最高 |
| 最低价 | decimal | ✅ 可用 · `qt.gtimg.cn` | ✅ 可用 · `hq.sinajs.cn` | ✅ 可用 · `f45` | ✅ 可用 · `stock_zh_a_spot_em()` | ⚠️ 有限 · `daily.low` 盘后 | ❌ 不支持 | ✅ 可用 · `v8/chart` | 日内最低 |
| 昨收价 | decimal | ✅ 可用 · `qt.gtimg.cn` | ✅ 可用 · `hq.sinajs.cn` | ✅ 可用 · `f60` | ✅ 可用 · `stock_zh_a_spot_em()` | ✅ 可用 · `daily.pre_close` | ❌ 不支持 | ✅ 可用 · `chartPreviousClose` | 涨跌计算基准 |
| 成交量（手） | integer | ✅ 可用 · `qt.gtimg.cn` | ✅ 可用 · `hq.sinajs.cn` | ✅ 可用 · `f47` | ✅ 可用 · `stock_zh_a_spot_em()` | ✅ 可用 · `daily.vol` | ❌ 不支持 | ✅ 可用 · `v8/chart volume` | 美股为股，A 股统一换算手 |
| 成交额（万元） | decimal | ✅ 可用 · `qt.gtimg.cn` | ✅ 可用 · `hq.sinajs.cn` | ✅ 可用 · `f48` | ✅ 可用 · `stock_zh_a_spot_em()` | ✅ 可用 · `daily.amount` 需换算 | ❌ 不支持 | ✅ 可用 · 价格×成交量估算 | 东财单位通常为元 |
| 买一/卖一至买五/卖五报价及量 | json | ✅ 可用 · `qt.gtimg.cn` 五档字段 | ✅ 可用 · `hq.sinajs.cn` 10 档字段子集 | ⚠️ 有限 · `push2 qt/stock/get` 需扩展 fields | ⚠️ 有限 · `stock_bid_ask_em()`/底层变动 | ❌ 不支持 | ❌ 不支持 | ⚠️ 有限 · 美股盘口需付费源 | 五档字段需保留原始数组 |
| 换手率 | decimal | ✅ 可用 · `qt.gtimg.cn` | ⚠️ 有限 · 部分需自行计算 | ✅ 可用 · `f168` | ✅ 可用 · `stock_zh_a_spot_em()` | 🔑 需Token · `daily_basic`（2000积分） | ❌ 不支持 | ⚠️ 有限 · 美股需股本计算 | A 股直接取东财/腾讯 |
| 量比 | decimal | ✅ 可用 · `qt.gtimg.cn` | ⚠️ 有限 · 不稳定 | ✅ 可用 · `f50` | ✅ 可用 · `stock_zh_a_spot_em()` | ❌ 不支持 | ❌ 不支持 | ❌ 不支持 | 盘中监控字段 |
| 振幅 | decimal | ✅ 可用 · `qt.gtimg.cn` | ✅ 可用 · 最高最低昨收计算 | ✅ 可用 · `f171` | ✅ 可用 · `stock_zh_a_spot_em()` | 🔑 需Token · `stk_factor` 或自行计算（5000积分） | ❌ 不支持 | ✅ 可用 · 计算 | 统一按百分比 |
| 总市值 | decimal | ✅ 可用 · `qt.gtimg.cn` | ⚠️ 有限 · 不稳定 | ✅ 可用 · `f116` | ✅ 可用 · `stock_zh_a_spot_em()` | 🔑 需Token · `daily_basic.total_mv`（2000积分） | ❌ 不支持 | ✅ 可用 · `marketCap` | 单位统一为亿元 |
| 流通市值 | decimal | ✅ 可用 · `qt.gtimg.cn` | ⚠️ 有限 · 不稳定 | ✅ 可用 · `f117` | ✅ 可用 · `stock_zh_a_spot_em()` | 🔑 需Token · `daily_basic.circ_mv`（2000积分） | ❌ 不支持 | ⚠️ 有限 · 美股需 float shares | 单位统一为亿元 |
| 动态PE | decimal | ✅ 可用 · `qt.gtimg.cn` | ⚠️ 有限 · 不稳定 | ✅ 可用 · `f162` | ✅ 可用 · `stock_zh_a_spot_em()` | 🔑 需Token · `daily_basic.pe_ttm`（2000积分） | ❌ 不支持 | ✅ 可用 · `trailingPE` | 需区分 TTM/动态 |
| 静态PE | decimal | ⚠️ 有限 · 字段需校验 | ⚠️ 有限 · 不稳定 | ✅ 可用 · `f163/f164` 类估值字段 | ⚠️ 有限 · 东财实时字段不总是返回 | 🔑 需Token · `daily_basic.pe`（2000积分） | ❌ 不支持 | ✅ 可用 · `trailingPE` | A 股建议 Tushare 盘后校正 |
| 市净率PB | decimal | ✅ 可用 · `qt.gtimg.cn` | ⚠️ 有限 · 不稳定 | ✅ 可用 · `f167` | ✅ 可用 · `stock_zh_a_spot_em()` | 🔑 需Token · `daily_basic.pb`（2000积分） | ❌ 不支持 | ✅ 可用 · `priceToBook` | 盘中用东财，盘后用 Tushare |
| 52周最高/最低 | decimal | ✅ 可用 · `qt.gtimg.cn` 或 K 线计算 | ⚠️ 有限 · 需历史计算 | ⚠️ 有限 · `push2` 扩展字段或 K 线计算 | ✅ 可用 · `stock_zh_a_hist()` 计算 | 🔑 需Token · `daily/stk_factor` 计算 | ❌ 不支持 | ✅ 可用 · `fiftyTwoWeekHigh/Low` | A 股建议从 260 交易日 K 线滚动计算 |

### A 接口详情

| 接口 | 基础URL | 认证方式 | 限速（估算） | 建议防拉黑延迟 | IP封锁风险 |
|------|---------|---------|-------------|--------------|-----------|
| 腾讯实时行情 | `https://qt.gtimg.cn/q=sh600000` | 无 Token；建议 UA | 60-120 req/min/IP | 批量 20-40 码/次；请求间隔 0.8-1.5s | 中 |
| 腾讯 K 线内嵌 quote | `https://web.ifzq.gtimg.cn/appstock/app/fqkline/get` | 无 Token；建议 UA | 30-80 req/min/IP | 单股 1.0-2.0s；失败指数退避 | 中 |
| 新浪实时行情 | `https://hq.sinajs.cn/list=sz000001` | 无 Token；必须 UA/Referer；建议 Session | 60-100 req/min/IP | 批量 20-50 码/次；1.5-3.0s | 中高 |
| 东方财富实时行情 | `https://push2.eastmoney.com/api/qt/stock/get` | 无 Token；建议 UA/Referer；通常无需 Cookie | 60-120 req/min/IP | 1.0-2.0s；403 后冷却 | 中 |
| AKShare 实时封装 | `ak.stock_zh_a_spot_em()` | 无 Token；依赖 AKShare 版本 | 取决于底层东财 | 全市场调用间隔 5-15s | 中 |
| Tushare 日线/每日指标 | `pro.daily`、`pro.daily_basic` | 🔑 Token；2000积分起 | 按积分等级 | 批量按交易日拉取，非盘中轮询 | 低 |
| Yahoo Finance quote/chart | `https://query1.finance.yahoo.com/v8/finance/chart/{symbol}` | 无 Token；`quoteSummary` 可能需 Cookie/crumb | 30-100 req/min/IP | 1.0-2.0s；403 切 chart | 中 |

### A 采集策略

| 字段名 | 主源 | 备源1 | 备源2 | 建议采集频率 | 特殊时间触发点 |
|--------|------|-------|-------|-------------|--------------|
| 最新价/涨跌幅/涨跌额 | 腾讯 `qt.gtimg.cn` | 东方财富 `push2` | 新浪 `hq.sinajs.cn` | 交易时段 1-3 分钟；核心股 30-60 秒 | 9:30-9:40、13:00-13:10 加密 |
| 开盘/最高/最低/昨收 | 腾讯 `qt.gtimg.cn` | 东方财富 `push2` | Tushare `daily` 盘后 | 交易时段 3-5 分钟；盘后固化 | 15:05 固定采集 |
| 成交量/成交额 | 腾讯 `qt.gtimg.cn` | 东方财富 `push2` | 新浪 `hq.sinajs.cn` | 交易时段 1-3 分钟 | 11:00-11:30、14:30-15:00 加密 |
| 五档盘口 | 腾讯 `qt.gtimg.cn` | 新浪 `hq.sinajs.cn` | 东方财富扩展 fields | 核心股 30-60 秒；普通股 3-5 分钟 | 开盘后 10 分钟与收盘前 30 分钟 |
| 换手率/量比/振幅 | 东方财富 `push2` | 腾讯 `qt.gtimg.cn` | AKShare `stock_zh_a_spot_em()` | 交易时段 3-5 分钟 | 量比异常大于 3 时即时刷新 |
| 总市值/流通市值 | 东方财富 `push2` | 腾讯 `qt.gtimg.cn` | Tushare `daily_basic` | 交易时段 15 分钟；盘后校正 | 15:05 与 17:30 |
| 动态PE/静态PE/PB | 东方财富 `push2` | 腾讯 `qt.gtimg.cn` | Tushare `daily_basic` | 交易时段 30 分钟；盘后校正 | 财报季每季末后 30 天密集扫描 |
| 52周最高/最低 | 腾讯/东财 K 线滚动计算 | Tushare `daily` | Yahoo 美股 | 每日盘后 | 15:05 固定采集 |

## B. 分时与 K 线数据

| 字段名 | 字段类型 | 腾讯证券API | 新浪财经API | 东方财富API | AKShare封装 | Tushare | 巨潮资讯CNINFO | Yahoo Finance | 备注 |
|--------|----------|-------------|-------------|-------------|-------------|---------|----------------|---------------|------|
| 分时成交（1min OHLCV） | time_series | ✅ 可用 · `web.ifzq...mKLine`/分钟参数 | ⚠️ 有限 · 新浪分时接口易变 | ✅ 可用 · `push2his.eastmoney.com/api/qt/stock/kline/get klt=1` | ✅ 可用 · `ak.stock_zh_a_hist_min_em(period="1")` | 🔑 需Token · 分钟数据权限/积分 | ❌ 不支持 | ✅ 可用 · `v8/chart interval=1m` | AKShare 注明 1 分钟近 5 交易日且不复权 |
| 日K线（前复权/后复权/不复权 OHLCV） | time_series | ✅ 可用 · `web.ifzq...fqkline/get day,qfq/hfq` | ✅ 可用 · 新浪历史日线 | ✅ 可用 · 东财 K 线 `klt=101 fqt=0/1/2` | ✅ 可用 · `ak.stock_zh_a_hist(adjust=""/"qfq"/"hfq")` | 🔑 需Token · `daily`/`pro_bar`（2000积分起） | ❌ 不支持 | ✅ 可用 · `v8/chart interval=1d` | 仓库当前主源为腾讯前复权日 K |
| 周K线、月K线 | time_series | ✅ 可用 · `web.ifzq...week/month` | ⚠️ 有限 · 历史接口质量一般 | ✅ 可用 · 东财 K 线 `klt=102/103` | ✅ 可用 · `ak.stock_zh_a_hist(period="weekly/monthly")` | 🔑 需Token · `weekly`/`monthly`（2000积分起） | ❌ 不支持 | ✅ 可用 · `v8/chart interval=1wk/1mo` | 周月线盘后更新即可 |
| 复权因子 | decimal_series | ⚠️ 有限 · 可由 qfq/hfq 与不复权反推 | ⚠️ 有限 · `stock_zh_a_daily adjust=factor` | ⚠️ 有限 · fqt 结果可反推 | ⚠️ 有限 · `ak.stock_zh_a_daily(adjust="qfq-factor")` | 🔑 需Token · `adj_factor`（2000积分起） | ❌ 不支持 | ✅ 可用 · split/dividend 事件反推 | 生产建议以 Tushare `adj_factor` 为标准 |

### B 接口详情

| 接口 | 基础URL | 认证方式 | 限速（估算） | 建议防拉黑延迟 | IP封锁风险 |
|------|---------|---------|-------------|--------------|-----------|
| 腾讯复权 K 线 | `https://web.ifzq.gtimg.cn/appstock/app/fqkline/get` | 无 Token；建议 UA | 30-80 req/min/IP | 单股 1-2s；分批拉 420 日 | 中 |
| 东方财富历史 K 线 | `https://push2his.eastmoney.com/api/qt/stock/kline/get` | 无 Token；建议 Referer | 60-120 req/min/IP | 1-2s；失败退避 | 中 |
| 新浪历史日线 | `https://finance.sina.com.cn/realstock/company/{symbol}/nc.shtml` 派生接口 | 无 Token；需 UA/Referer/Session | 20-60 req/min/IP | 2-5s | 高 |
| AKShare K 线封装 | `stock_zh_a_hist`、`stock_zh_a_hist_min_em` | 无 Token；依赖版本 | 取决于底层东财 | 全池分钟数据分批，避免扫全市场 | 中 |
| Tushare K 线/复权 | `daily`、`weekly`、`monthly`、`pro_bar`、`adj_factor` | 🔑 Token；2000积分起，分钟权限另计 | 按积分等级 | 盘后批量 | 低 |
| Yahoo chart | `https://query1.finance.yahoo.com/v8/finance/chart/{symbol}` | 无 Token；建议 UA | 30-100 req/min/IP | 1-2s | 中 |

### B 采集策略

| 字段名 | 主源 | 备源1 | 备源2 | 建议采集频率 | 特殊时间触发点 |
|--------|------|-------|-------|-------------|--------------|
| 分时成交（1min OHLCV） | 东方财富 `push2his klt=1` | AKShare `stock_zh_a_hist_min_em()` | 腾讯分钟 K | 核心股 1 分钟；普通股 5 分钟 | 9:30-9:40、13:00-13:10 |
| 日K线 | 腾讯 `fqkline day` | AKShare `stock_zh_a_hist()` | Tushare `daily/pro_bar` | 每日 15:05 与 17:30 双采 | 15:05 固定采集 |
| 周K线、月K线 | 腾讯 `week/month` | 东方财富 K 线 | Tushare `weekly/monthly` | 每周五 15:30；每月末 16:00 | 周/月最后交易日 |
| 复权因子 | Tushare `adj_factor` | AKShare factor | 腾讯/东财反推 | 每日盘前 9:20 与盘后 17:30 | 除权除息日前后加密 |

## C. 财务基本面（季报/年报）

| 字段名 | 字段类型 | 腾讯证券API | 新浪财经API | 东方财富API | AKShare封装 | Tushare | 巨潮资讯CNINFO | Yahoo Finance | 备注 |
|--------|----------|-------------|-------------|-------------|-------------|---------|----------------|---------------|------|
| 营业收入（季度/年度/TTM） | decimal | ❌ 不支持 | ✅ 可用 · `vip.stock.finance.sina.com.cn` 财报页 | ✅ 可用 · `datacenter`/年报季报 | ✅ 可用 · `stock_yjbb_em()`/`stock_lrb_em()` | 🔑 需Token · `income`/`fina_indicator`（2000积分） | ⚠️ 有限 · 年报 PDF/公告解析 | ✅ 可用 · `quoteSummary financials` | TTM 需滚动计算 |
| 净利润（季度/年度/TTM） | decimal | ❌ 不支持 | ✅ 可用 · 新浪财报页 | ✅ 可用 · 东财年报季报 | ✅ 可用 · `stock_yjbb_em()`/`stock_lrb_em()` | 🔑 需Token · `income`（2000积分） | ⚠️ 有限 · PDF 解析 | ✅ 可用 · `quoteSummary` | 区分归母/扣非 |
| 毛利率 | decimal | ❌ 不支持 | ✅ 可用 · 新浪关键指标 | ✅ 可用 · 东财业绩报表 | ✅ 可用 · `stock_yjbb_em()`/`stock_financial_analysis_indicator()` | 🔑 需Token · `fina_indicator.grossprofit_margin` | ⚠️ 有限 · PDF 解析 | ✅ 可用 · 财务报表计算 | 用百分比 |
| 净利率 | decimal | ❌ 不支持 | ✅ 可用 · 新浪关键指标 | ✅ 可用 · 东财主要指标 | ✅ 可用 · `stock_financial_analysis_indicator()` | 🔑 需Token · `fina_indicator.netprofit_margin` | ⚠️ 有限 · PDF 解析 | ✅ 可用 · 财务报表计算 | 用百分比 |
| ROE | decimal | ❌ 不支持 | ✅ 可用 · 新浪关键指标 | ✅ 可用 · 东财主要指标 | ✅ 可用 · `stock_financial_analysis_indicator()` | 🔑 需Token · `fina_indicator.roe*`（2000积分） | ⚠️ 有限 · PDF 解析 | ✅ 可用 · `returnOnEquity` | 摊薄/加权需注明 |
| ROA | decimal | ❌ 不支持 | ✅ 可用 · 新浪关键指标 | ✅ 可用 · 东财主要指标 | ✅ 可用 · `stock_financial_analysis_indicator()` | 🔑 需Token · `fina_indicator.roa*` | ⚠️ 有限 · PDF 解析 | ✅ 可用 · `returnOnAssets` | 口径统一 |
| 资产负债率 | decimal | ❌ 不支持 | ✅ 可用 · 新浪财报页 | ✅ 可用 · 东财资产负债表 | ✅ 可用 · `stock_zcfz_em()`/财务指标 | 🔑 需Token · `fina_indicator.debt_to_assets` | ⚠️ 有限 · PDF 解析 | ✅ 可用 · 资产负债表计算 | 财报期字段 |
| 经营现金流 | decimal | ❌ 不支持 | ✅ 可用 · 新浪现金流量表 | ✅ 可用 · 东财现金流量表 | ✅ 可用 · `stock_xjll_em()` | 🔑 需Token · `cashflow`（2000积分） | ⚠️ 有限 · PDF 解析 | ✅ 可用 · `cashflowStatementHistory` | 单位统一为亿元 |
| 每股收益EPS | decimal | ❌ 不支持 | ✅ 可用 · 新浪关键指标 | ✅ 可用 · 东财业绩报表 | ✅ 可用 · `stock_yjbb_em()` | 🔑 需Token · `income.basic_eps`/`fina_indicator.eps` | ⚠️ 有限 · PDF 解析 | ✅ 可用 · `trailingEps` | 基本/稀释需区分 |
| 每股净资产BPS | decimal | ❌ 不支持 | ✅ 可用 · 新浪关键指标 | ✅ 可用 · 东财业绩报表 | ✅ 可用 · `stock_yjbb_em()` | 🔑 需Token · `fina_indicator.bps` | ⚠️ 有限 · PDF 解析 | ⚠️ 有限 · 需计算 | BPS 盘后更新 |
| 商誉 | decimal | ❌ 不支持 | ✅ 可用 · 新浪资产负债表 | ✅ 可用 · 东财资产负债表 | ✅ 可用 · `stock_zcfz_em()`/新浪财报封装 | 🔑 需Token · `balancesheet.goodwill` | ⚠️ 有限 · PDF 解析 | ✅ 可用 · 资产负债表 | AIDC 并购公司重点监控 |
| 研发投入占比 | decimal | ❌ 不支持 | ⚠️ 有限 · 需财报科目计算 | ⚠️ 有限 · 东财财报科目/研发费用 | ⚠️ 有限 · `stock_lrb_em()` 需字段校验 | 🔑 需Token · `fina_indicator.rd_exp`/利润表研发费用 | ⚠️ 有限 · 年报 PDF 更完整 | ⚠️ 有限 · 美股 R&D/revenue | 建议研发费用/营业收入 |
| 业绩预告/快报 | json | ❌ 不支持 | ⚠️ 有限 · 新闻/公告页 | ✅ 可用 · 东财 `yjyg`/`yjkb` | ✅ 可用 · `stock_yjyg_em()`/`stock_yjkb_em()` | 🔑 需Token · `forecast`/`express`（2000积分） | ✅ 可用 · 公告分类关键词 | ❌ 不支持 | 预告作为事件表保存 |

### C 接口详情

| 接口 | 基础URL | 认证方式 | 限速（估算） | 建议防拉黑延迟 | IP封锁风险 |
|------|---------|---------|-------------|--------------|-----------|
| 东方财富年报季报 | `https://datacenter.eastmoney.com/securities/api/data/v1/get`、`data.eastmoney.com/bbsj` | 无 Token；需 UA/Referer；建议 Session | 30-80 req/min/IP | 2-5s；按报告期批量 | 中高 |
| 东方财富 F10 财务 | `https://emweb.securities.eastmoney.com/PC_HSF10/.../PageAjax` | 无 Token；需 UA/Referer；Cookie 可复用 | 20-60 req/min/IP | 2-5s；失败冷却 | 中高 |
| 新浪财务页 | `https://vip.stock.finance.sina.com.cn/corp/go.php/...` | 无 Token；需 UA/Referer | 20-60 req/min/IP | 2-5s | 高 |
| AKShare 财务封装 | `stock_yjbb_em`、`stock_lrb_em`、`stock_xjll_em`、`stock_financial_analysis_indicator` | 无 Token；依赖 AKShare 版本 | 取决于底层站点 | 按报告期拉全市场 | 中 |
| Tushare 财务 | `income`、`balancesheet`、`cashflow`、`fina_indicator`、`forecast`、`express` | 🔑 Token；2000积分起 | 按积分等级 | 财报季日扫，平时周扫 | 低 |
| 巨潮公告/PDF | `https://www.cninfo.com.cn/new/hisAnnouncement/query`、`static.cninfo.com.cn` | 无 Token；需遵守 robots；建议 Referer/Cookie | 10-30 req/min/IP | 3-10s；PDF 单独队列 | 高 |
| Yahoo quoteSummary | `https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}` | 无 Token；可能需 Cookie/crumb | 20-60 req/min/IP | 2-5s | 中 |

### C 采集策略

| 字段名 | 主源 | 备源1 | 备源2 | 建议采集频率 | 特殊时间触发点 |
|--------|------|-------|-------|-------------|--------------|
| 营业收入 | Tushare `income` | 东方财富 `datacenter` | AKShare `stock_yjbb_em()` | 财报季每日；平时每周 | 每季末后 30 天密集扫描 |
| 净利润 | Tushare `income` | 东方财富 `stock_lrb_em` | 巨潮公告校验 | 财报季每日 | 预告/快报公告后即时刷新 |
| 毛利率/净利率 | Tushare `fina_indicator` | 东方财富主要指标 | AKShare 财务指标 | 财报季每日；盘后 | 财报披露当日 20:00 后 |
| ROE/ROA | Tushare `fina_indicator` | 东方财富主要指标 | 新浪关键指标 | 财报季每日 | 财报披露后 T+0/T+1 |
| 资产负债率 | Tushare `fina_indicator` | 东方财富资产负债表 | 巨潮 PDF 校验 | 财报季每日 | 财报披露后 |
| 经营现金流 | Tushare `cashflow` | 东方财富现金流量表 | 新浪现金流量表 | 财报季每日 | 财报披露后 |
| EPS/BPS | Tushare `income/fina_indicator` | 东方财富业绩报表 | AKShare `stock_yjbb_em()` | 财报季每日 | 财报披露后 |
| 商誉 | Tushare `balancesheet` | 东方财富资产负债表 | 巨潮 PDF 校验 | 季度 | 年报/半年报后重点 |
| 研发投入占比 | Tushare 财报科目 | 巨潮年报 PDF | 东方财富利润表 | 季度，年报重点 | 年报披露后 48 小时内 |
| 业绩预告/快报 | 东方财富 `yjyg/yjkb` | Tushare `forecast/express` | 巨潮公告 | 财报季每日 2 次 | 1/4/7/10 月密集扫描 |

## D. 主营业务构成

| 字段名 | 字段类型 | 腾讯证券API | 新浪财经API | 东方财富API | AKShare封装 | Tushare | 巨潮资讯CNINFO | Yahoo Finance | 备注 |
|--------|----------|-------------|-------------|-------------|-------------|---------|----------------|---------------|------|
| 各业务线营收/利润/占比 | json | ❌ 不支持 | ⚠️ 有限 · 财报页需解析 | ✅ 可用 · `emweb...BusinessAnalysis/PageAjax zygcfx` | ✅ 可用 · `ak.stock_zygc_em(symbol="SH688041")` | 🔑 需Token · `fina_mainbz`（2000积分） | ⚠️ 有限 · 年报 PDF/HTML 解析 | ⚠️ 有限 · 美股 segment 数据不稳定 | 仓库当前主源为东财 F10；利润为主营业务利润/毛利口径 |
| 报告期 | date | ❌ 不支持 | ⚠️ 有限 · 财报页 | ✅ 可用 · `REPORT_DATE` | ✅ 可用 · `stock_zygc_em()` | 🔑 需Token · `fina_mainbz.end_date` | ✅ 可用 · 公告报告期 | ⚠️ 有限 · 财报期 | 取最新披露期并保留历史 |

### D 接口详情

| 接口 | 基础URL | 认证方式 | 限速（估算） | 建议防拉黑延迟 | IP封锁风险 |
|------|---------|---------|-------------|--------------|-----------|
| 东方财富 F10 主营构成 | `https://emweb.securities.eastmoney.com/PC_HSF10/BusinessAnalysis/PageAjax?code=SH688041` | 无 Token；需 UA/Referer；建议 Session/Cookie | 20-60 req/min/IP | 单股 2-5s；失败冷却 | 中高 |
| AKShare 主营构成 | `ak.stock_zygc_em()` | 无 Token；依赖 AKShare 版本 | 取决于东财 F10 | 单股 2-5s | 中高 |
| Tushare 主营业务 | `pro.fina_mainbz` | 🔑 Token；2000积分起 | 按积分等级 | 财报季日扫 | 低 |
| 巨潮年报原文 | `static.cninfo.com.cn/finalpage/...PDF` | 无 Token；需 robots 合规 | 10-30 req/min/IP | PDF 下载 5-10s | 高 |

### D 采集策略

| 字段名 | 主源 | 备源1 | 备源2 | 建议采集频率 | 特殊时间触发点 |
|--------|------|-------|-------|-------------|--------------|
| 各业务线营收/利润/占比 | 东方财富 `BusinessAnalysis/PageAjax` | AKShare `stock_zygc_em()` | Tushare `fina_mainbz` | 财报季每日；平时每月 | 财报披露后与每季末后 30 天 |
| 报告期 | 东方财富 `REPORT_DATE` | Tushare `end_date` | 巨潮公告报告期 | 同主营构成 | 新财报公告后即时刷新 |

## E. 资金流向

| 字段名 | 字段类型 | 腾讯证券API | 新浪财经API | 东方财富API | AKShare封装 | Tushare | 巨潮资讯CNINFO | Yahoo Finance | 备注 |
|--------|----------|-------------|-------------|-------------|-------------|---------|----------------|---------------|------|
| 主力净流入/散户净流出（大单/超大单） | decimal/json | ❌ 不支持 | ⚠️ 有限 · 资金页面解析 | ✅ 可用 · `data.eastmoney.com/zjlx` | ✅ 可用 · `stock_individual_fund_flow()`/`stock_main_fund_flow()` | 🔑 需Token · `moneyflow_dc`（5000积分）/`moneyflow`（2000积分） | ❌ 不支持 | ❌ 不支持 | 盘中用东财，盘后用 Tushare 校正 |
| 北向资金持股量及变化（沪深港通） | decimal/json | ❌ 不支持 | ❌ 不支持 | ✅ 可用 · `data.eastmoney.com/hsgtcg` | ✅ 可用 · `stock_hsgt_hold_stock_em()` | 🔑 需Token · `hk_hold`/`moneyflow_hsgt`（2000积分） | ❌ 不支持 | ❌ 不支持 | 持股量 T+1 更可靠 |
| 融资融券余额 | decimal | ❌ 不支持 | ❌ 不支持 | ✅ 可用 · `data.eastmoney.com/rzrq` | ✅ 可用 · `stock_margin_*` 系列 | 🔑 需Token · `margin`/`margin_detail`（2000积分） | ❌ 不支持 | ❌ 不支持 | 盘后/次日更新 |

### E 接口详情

| 接口 | 基础URL | 认证方式 | 限速（估算） | 建议防拉黑延迟 | IP封锁风险 |
|------|---------|---------|-------------|--------------|-----------|
| 东方财富个股资金流 | `https://data.eastmoney.com/zjlx/detail.html` 派生 API | 无 Token；需 UA/Referer；建议 Session | 30-60 req/min/IP | 2-5s | 中高 |
| 东方财富沪深港通 | `https://data.eastmoney.com/hsgtcg/list.html` | 无 Token；需 UA/Referer | 20-60 req/min/IP | 2-5s | 中高 |
| 东方财富融资融券 | `https://data.eastmoney.com/rzrq/...` | 无 Token；需 UA/Referer | 20-60 req/min/IP | 2-5s | 中高 |
| AKShare 资金流封装 | `stock_individual_fund_flow`、`stock_hsgt_hold_stock_em`、`stock_margin_account_info` | 无 Token；依赖版本 | 取决于底层站点 | 2-5s；避免全量高频 | 中高 |
| Tushare 资金/两融 | `moneyflow_dc`、`moneyflow`、`hk_hold`、`moneyflow_hsgt`、`margin`、`margin_detail` | 🔑 Token；2000-5000积分 | 按积分等级 | 盘后批量 | 低 |

### E 采集策略

| 字段名 | 主源 | 备源1 | 备源2 | 建议采集频率 | 特殊时间触发点 |
|--------|------|-------|-------|-------------|--------------|
| 主力净流入/散户净流出 | 东方财富资金流 | AKShare `stock_individual_fund_flow()` | Tushare `moneyflow_dc` | 交易时段 5-15 分钟；盘后校正 | 11:00-11:30、14:30-15:00 加密 |
| 北向资金持股量及变化 | 东方财富沪深港通 | AKShare `stock_hsgt_hold_stock_em()` | Tushare `hk_hold` | 每日盘后/次日 8:30 | 北向大幅异动时刷新 |
| 融资融券余额 | Tushare `margin_detail` | 东方财富两融 | AKShare 两融封装 | 每日 9:30 后与 17:30 | 盘后固定采集 |

## F. 股东结构

| 字段名 | 字段类型 | 腾讯证券API | 新浪财经API | 东方财富API | AKShare封装 | Tushare | 巨潮资讯CNINFO | Yahoo Finance | 备注 |
|--------|----------|-------------|-------------|-------------|-------------|---------|----------------|---------------|------|
| 十大流通股东（最新季） | json | ❌ 不支持 | ⚠️ 有限 · F10 页面解析 | ✅ 可用 · `data.eastmoney.com/gdfx` | ✅ 可用 · `stock_gdfx_free_holding_detail_em()` | 🔑 需Token · `top10_floatholders`（2000积分） | ✅ 可用 · 定期报告原文 | ⚠️ 有限 · holders 数据偏美股口径 | 季度报告披露后更新 |
| 机构持仓比例 | decimal/json | ❌ 不支持 | ⚠️ 有限 · F10 页面解析 | ✅ 可用 · 股东分析/基金持仓 | ✅ 可用 · `stock_gdfx_*_em()`/机构持股函数 | 🔑 需Token · `top10_floatholders`/基金持仓 | ⚠️ 有限 · PDF 解析 | ✅ 可用 · `institutionOwnership` | 需定义机构口径：基金、QFII、社保、券商、保险等 |
| 限售股解禁计划 | json | ❌ 不支持 | ⚠️ 有限 · 公告/页面解析 | ✅ 可用 · 限售解禁页面 | ⚠️ 有限 · 东财/巨潮封装视版本 | 🔑 需Token · `share_float`（120-3000积分口径以权限页为准） | ✅ 可用 · 解禁公告 | ❌ 不支持 | 事件表，关注未来 180 天 |

### F 接口详情

| 接口 | 基础URL | 认证方式 | 限速（估算） | 建议防拉黑延迟 | IP封锁风险 |
|------|---------|---------|-------------|--------------|-----------|
| 东方财富股东分析 | `https://data.eastmoney.com/gdfx/HoldingAnalyse.html` | 无 Token；需 UA/Referer；建议 Session | 20-60 req/min/IP | 2-5s | 中高 |
| 东方财富限售解禁 | `https://data.eastmoney.com/dxf/default.html` 派生 API | 无 Token；需 UA/Referer | 20-60 req/min/IP | 2-5s | 中高 |
| AKShare 股东封装 | `stock_gdfx_free_holding_detail_em` 等 | 无 Token；依赖版本 | 取决于东财 | 按报告期拉取 | 中高 |
| Tushare 股东/解禁 | `top10_floatholders`、`top10_holders`、`share_float` | 🔑 Token；通常 2000积分起，`share_float` 低积分可试用 | 按积分等级 | 季报后批量 | 低 |
| 巨潮定期报告 | `hisAnnouncement/query` + PDF | 无 Token；需 robots 合规 | 10-30 req/min/IP | 3-10s | 高 |

### F 采集策略

| 字段名 | 主源 | 备源1 | 备源2 | 建议采集频率 | 特殊时间触发点 |
|--------|------|-------|-------|-------------|--------------|
| 十大流通股东 | Tushare `top10_floatholders` | 东方财富股东分析 | 巨潮定期报告 | 季报后每日，平时月度 | 每季末后 30 天 |
| 机构持仓比例 | 东方财富股东分析 | Tushare 股东/基金持仓 | 巨潮定期报告 | 季报后每日，平时月度 | 基金季报披露窗口 |
| 限售股解禁计划 | Tushare `share_float` | 东方财富限售解禁 | 巨潮公告 | 每周；未来 30 天每日 | 解禁前 T-30/T-10/T-3/T-1 |

## G. 公告/研报/新闻

| 字段名 | 字段类型 | 腾讯证券API | 新浪财经API | 东方财富API | AKShare封装 | Tushare | 巨潮资讯CNINFO | Yahoo Finance | 备注 |
|--------|----------|-------------|-------------|-------------|-------------|---------|----------------|---------------|------|
| 上市公司公告（标题、时间、URL、类型） | json | ❌ 不支持 | ⚠️ 有限 · 新闻/公告页 | ✅ 可用 · `data.eastmoney.com/notices` | ✅ 可用 · `stock_notice_report()`/`stock_individual_notice_report()`/`stock_zh_a_disclosure_report_cninfo()` | 🔑 需Token · 大模型语料/公告权限视套餐 | ✅ 可用 · `hisAnnouncement/query` | ⚠️ 有限 · 美股 SEC/新闻非 A 股 | CNINFO 为法定披露主源 |
| 分析师评级及目标价 | json | ❌ 不支持 | ⚠️ 有限 · 研报页解析 | ✅ 可用 · `data.eastmoney.com/report/stock.jshtml` | ✅ 可用 · `stock_research_report_em()` | 🔑 需Token · 券商盈利预测/研报权限 | ❌ 不支持 | ✅ 可用 · `quoteSummary recommendationTrend/financialData` | A 股目标价需记录报告日期与机构 |
| 行业新闻摘要 | text/json | ❌ 不支持 | ✅ 可用 · 新浪财经新闻 | ✅ 可用 · 东财新闻搜索 | ✅ 可用 · `stock_news_em()`/`stock_info_global_cls()` | 🔑 需Token · 新闻快讯/通讯权限视套餐 | ⚠️ 有限 · 公告非新闻 | ✅ 可用 · Yahoo news | 需做 AIDC 关键词过滤与去重 |

### G 接口详情

| 接口 | 基础URL | 认证方式 | 限速（估算） | 建议防拉黑延迟 | IP封锁风险 |
|------|---------|---------|-------------|--------------|-----------|
| 巨潮公告查询 | `https://www.cninfo.com.cn/new/hisAnnouncement/query` | 无 Token；需 UA/Referer/Cookie；遵守 robots.txt | 10-30 req/min/IP | 3-10s；分页慢拉 | 高 |
| 东方财富公告 | `https://data.eastmoney.com/notices/...` | 无 Token；需 UA/Referer | 20-60 req/min/IP | 2-5s | 中高 |
| 东方财富研报 | `https://data.eastmoney.com/report/stock.jshtml` | 无 Token；需 UA/Referer | 20-60 req/min/IP | 2-5s | 中高 |
| 东方财富新闻搜索 | `https://so.eastmoney.com/news/s?keyword=` | 无 Token；需 UA/Referer | 20-60 req/min/IP | 2-5s | 中高 |
| AKShare 资讯封装 | `stock_zh_a_disclosure_report_cninfo`、`stock_research_report_em`、`stock_news_em` | 无 Token；依赖版本 | 取决于底层站点 | 2-5s | 中高 |
| Yahoo news/quoteSummary | `query1.finance.yahoo.com`、`finance.yahoo.com/news` | 无 Token；可能需 Cookie | 20-60 req/min/IP | 2-5s | 中 |

### G 采集策略

| 字段名 | 主源 | 备源1 | 备源2 | 建议采集频率 | 特殊时间触发点 |
|--------|------|-------|-------|-------------|--------------|
| 上市公司公告 | 巨潮 `hisAnnouncement/query` | AKShare CNINFO 封装 | 东方财富公告 | 交易日 8:30、12:30、16:00、21:00 | 财报季每日加扫；重大事项关键词即时 |
| 分析师评级及目标价 | 东方财富研报 | AKShare `stock_research_report_em()` | Yahoo 美股评级 | 每日 18:00 | 新研报发布时间、财报后 5 个交易日 |
| 行业新闻摘要 | 东方财富新闻/财联社 | 新浪财经新闻 | Yahoo news | 交易时段 30 分钟；盘后汇总 | 美股盘前/盘后、A 股收盘后 |

## H. 宏观/行业指数

| 字段名 | 字段类型 | 腾讯证券API | 新浪财经API | 东方财富API | AKShare封装 | Tushare | 巨潮资讯CNINFO | Yahoo Finance | 备注 |
|--------|----------|-------------|-------------|-------------|-------------|---------|----------------|---------------|------|
| 上证综指、深证成指、创业板指实时行情 | decimal/json | ✅ 可用 · `qt.gtimg.cn/q=sh000001,sz399001,sz399006` | ✅ 可用 · `hq.sinajs.cn/list=sh000001,sz399001,sz399006` | ✅ 可用 · `push2` 指数 secid | ✅ 可用 · `stock_zh_index_spot()`/指数封装 | 🔑 需Token · `index_daily`/实时指数权限 | ❌ 不支持 | ✅ 可用 · `000001.SS`/`399001.SZ` 部分 | 指数实时主源可与个股同链路 |
| 行业指数（申万二级：光通信II、存储器II等） | decimal/json | ⚠️ 有限 · 无申万完整分类 | ⚠️ 有限 · 新浪行业板块非申万 | ✅ 可用 · 东财行业/板块，申万需映射 | ✅ 可用 · `stock_board_industry_name_em()`/`stock_board_industry_index_ths()` | 🔑 需Token · `sw_daily`/`sw_member`/申万实时（4000积分起部分） | ❌ 不支持 | ❌ 不支持 | 申万二级建议 Tushare/申万授权源；东财板块作近似 |

### H 接口详情

| 接口 | 基础URL | 认证方式 | 限速（估算） | 建议防拉黑延迟 | IP封锁风险 |
|------|---------|---------|-------------|--------------|-----------|
| 腾讯指数行情 | `https://qt.gtimg.cn/q=sh000001,sz399001,sz399006` | 无 Token；建议 UA | 60-120 req/min/IP | 1-2s | 中 |
| 新浪指数行情 | `https://hq.sinajs.cn/list=sh000001,sz399001,sz399006` | 无 Token；需 UA/Referer | 60-100 req/min/IP | 1.5-3s | 中高 |
| 东方财富指数/板块 | `push2.eastmoney.com`、`quote.eastmoney.com/center/boardlist.html` | 无 Token；需 UA/Referer | 30-80 req/min/IP | 2-5s | 中高 |
| AKShare 板块/行业 | `stock_board_industry_name_em`、`stock_board_industry_spot_em`、`stock_board_industry_index_ths` | 无 Token；依赖版本 | 取决于底层站点 | 2-5s | 中高 |
| Tushare 指数/申万 | `index_daily`、`index_dailybasic`、`sw_daily`、`sw_member` | 🔑 Token；指数/申万通常 2000-4000积分起 | 按积分等级 | 盘后批量 | 低 |
| Yahoo 指数 | `https://query1.finance.yahoo.com/v8/finance/chart/{symbol}` | 无 Token | 30-100 req/min/IP | 1-2s | 中 |

### H 采集策略

| 字段名 | 主源 | 备源1 | 备源2 | 建议采集频率 | 特殊时间触发点 |
|--------|------|-------|-------|-------------|--------------|
| 上证综指、深证成指、创业板指实时行情 | 腾讯 `qt.gtimg.cn` | 新浪 `hq.sinajs.cn` | 东方财富 `push2` | 交易时段 1-3 分钟 | 9:30-9:40、14:30-15:00 |
| 行业指数（申万二级等） | Tushare 申万指数 | 东方财富行业板块 | AKShare 同花顺行业指数 | 交易时段 5-15 分钟；盘后校正 | AIDC 板块涨跌幅偏离大盘 ±2% 时刷新 |

## 附录 A：推荐 HTTP 请求头模板

### 通用浏览器模板

```http
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36
Accept: application/json,text/plain,*/*
Accept-Language: zh-CN,zh;q=0.9,en;q=0.8
Connection: keep-alive
Cache-Control: no-cache
Pragma: no-cache
```

### 新浪 `hq.sinajs.cn`

```http
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36
Referer: https://finance.sina.com.cn/
Accept: */*
```

### 东方财富 `push2/datacenter/emweb`

```http
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36
Referer: https://quote.eastmoney.com/
Origin: https://quote.eastmoney.com
Accept: application/json,text/plain,*/*
```

### 巨潮资讯 CNINFO

```http
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36
Referer: https://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search
Origin: https://www.cninfo.com.cn
Accept: application/json,text/plain,*/*
```

### Yahoo Finance

```http
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36
Referer: https://finance.yahoo.com/
Accept: application/json,text/plain,*/*
```

### User-Agent 轮换建议

| 项目 | 建议 |
|------|------|
| UA 池大小 | 3-5 个主流桌面浏览器 UA 即可，避免过度随机 |
| Session | 同一域名复用一个 `requests.Session`，保留 Cookie 与连接池 |
| Referer | 按域名固定，不要跨站乱填 |
| 超时 | connect 5s、read 15-20s |
| 重试 | 仅对 408/429/5xx 重试；退避 1s、2s、5s、15s |
| 熔断 | 同域名连续 3 次 403/429 熔断 10-30 分钟 |
| 并发 | Web scraping 类接口单域名并发不超过 2-4；Tushare/Yahoo 可按配额调整 |

## 附录 B：AKShare 函数速查表

| 函数 | 覆盖字段 | 底层/目标地址 | 版本依赖与注意 |
|------|----------|---------------|----------------|
| `ak.stock_zh_a_spot_em()` | A 股实时行情、涨跌幅、成交量、成交额、换手率、量比、PE、PB、市值 | 东方财富沪深京 A 股实时行情 | AKShare 文档当前为 1.18.60；项目声明 `akshare>=1.12`，建议锁定并回归测试 |
| `ak.stock_zh_a_hist()` | 日/周/月 K 线，前复权/后复权/不复权 | 东方财富历史行情 | 支持 `period="daily/weekly/monthly"`、`adjust=""/"qfq"/"hfq"` |
| `ak.stock_zh_a_hist_min_em()` | 1/5/15/30/60 分钟 K 线 | 东方财富分时 | 1 分钟通常仅近 5 个交易日且不复权 |
| `ak.stock_zh_a_daily()` | 新浪历史日线与复权因子 | 新浪财经 | AKShare 文档建议优先用 `stock_zh_a_hist`；多次获取易封 IP |
| `ak.stock_yjbb_em()` | 业绩报表、EPS、营收、净利润、ROE、毛利率 | 东方财富年报季报 | 按报告期拉全市场 |
| `ak.stock_lrb_em()` | 利润表、营业收入、净利润 | 东方财富利润表 | 按报告期 |
| `ak.stock_xjll_em()` | 现金流量表、经营现金流 | 东方财富现金流量表 | 按报告期 |
| `ak.stock_financial_analysis_indicator()` | 财务指标、ROE、ROA、利润率等 | 新浪/财务指标页 | 单股历史指标 |
| `ak.stock_financial_abstract()` | 新浪关键指标 | 新浪财经 | 字段为宽表，需转长表 |
| `ak.stock_financial_report_sina()` | 三大报表 | 新浪财经 | 参数区分资产负债表、利润表、现金流量表 |
| `ak.stock_yjyg_em()` | 业绩预告 | 东方财富 | 按报告期 |
| `ak.stock_zygc_em()` | 主营业务构成、报告期、收入/利润/占比 | 东方财富 F10 | 当前仓库东财 F10 原始接口的封装替代 |
| `ak.stock_individual_fund_flow()` | 个股资金流、大单/超大单/小单 | 东方财富资金流 | 近 100 个交易日 |
| `ak.stock_main_fund_flow()` | 主力净流入排名 | 东方财富资金流 | 全市场排名 |
| `ak.stock_hsgt_hold_stock_em()` | 北向持股及变化 | 东方财富沪深港通 | 支持今日、3日、5日、10日、月/季/年排行 |
| `ak.stock_margin_account_info()` | 两融账户汇总 | 东方财富融资融券 | 市场级，不一定是个股余额 |
| `ak.stock_gdfx_free_holding_detail_em()` | 十大流通股东明细 | 东方财富股东分析 | 按报告期全市场 |
| `ak.stock_zh_a_disclosure_report_cninfo()` | 巨潮公告标题/时间/链接 | 巨潮资讯 | 单股、分类、日期范围 |
| `ak.stock_notice_report()` | 东财公告大全 | 东方财富公告 | 按公告类型与日期 |
| `ak.stock_individual_notice_report()` | 个股公告 | 东方财富公告 | 单股、类型、日期范围 |
| `ak.stock_research_report_em()` | 个股研报、评级、盈利预测、PDF | 东方财富研报 | 单股全量 |
| `ak.stock_news_em()` | 个股新闻 | 东方财富新闻搜索 | 最近约 100 条 |
| `ak.stock_info_global_cls()` | 财联社电报 | 财联社 | 最近约 20 条 |
| `ak.stock_board_industry_name_em()` | 东方财富行业板块实时行情 | 东方财富板块 | 近似行业指数，不等同申万 |
| `ak.stock_board_industry_spot_em()` | 指定行业板块实时行情 | 东方财富板块 | 可用板块名或代码 |
| `ak.stock_board_industry_index_ths()` | 同花顺行业指数日线 | 同花顺行业板块 | 行业命名需映射到 AIDC 子赛道 |
| `ak.stock_sector_spot()` | 新浪行业板块行情 | 新浪财经 | 非申万口径，仅作参考 |

## 参考资料

- AKShare 股票数据文档：<https://akshare.akfamily.xyz/data/stock/stock.html>
- AKShare GitHub README 与版本信息：<https://github.com/akfamily/akshare>
- Tushare 数据接口与权限索引：<https://tushare.pro/document/2?doc_id=5>
- Tushare 每日指标：<https://tushare.pro/document/2?doc_id=32>
- Tushare 复权因子：<https://tushare.pro/document/2?doc_id=28>
- Tushare 财务接口权限说明：<https://www.tushare.pro/document/2?doc_id=108>
- Tushare 个股资金流向（DC）：<https://tushare.pro/document/2?doc_id=349>
- Tushare 融资融券标的：<https://tushare.pro/document/2?doc_id=326>
- Tushare 限售股解禁：<https://tushare.pro/document/2?doc_id=160>
- 巨潮资讯官网：<https://www.cninfo.com.cn/new/index>
- Yahoo Finance chart/quote 端点说明参考：<https://hexdocs.pm/quant/0.1.0-alpha.1/Quant.Explorer.Providers.YahooFinance.html>
