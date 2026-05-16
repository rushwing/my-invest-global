# 宏观与全球市场指标 × 数据源工具矩阵

更新时间：2026-05-16  
适用范围：AIDC 产业链跟踪中的宏观、商品、全球指数、关键美股、云巨头 CapEx、中国市场指标与事件新闻。  
定位：补充 `docs/data-source-matrix.md`，用于宏观/市场指标采集方案设计；不实现代码。

## 概述

### 数据源对比总结

| 数据源 | 最适合字段 | 优点 | 主要限制 | 建议角色 |
|--------|------------|------|----------|----------|
| FRED API | 美国 CPI/PPI、联邦基金利率、美国国债收益率、部分美元指数替代 | 官方、免费、历史长、字段稳定 | 需申请 API Key；多数为日线/月度，不适合实时行情；FOMC 日历不是标准结构化字段 | 美国宏观与利率主源 |
| Yahoo Finance | 全球指数、ETF、期货、外汇、ADR、美股日线与准实时 | 覆盖广，`chart` 接口适合 OHLCV；`yfinance` 生态成熟 | 非官方 API；部分 ticker 会变动；`quoteSummary` 可能需 Cookie/crumb | 全球市场行情主源 |
| AKShare | 中国宏观、A 股指数、外汇、全球指数、期货与新闻封装 | 免费、函数名清晰，适合快速验证 | 底层多为网页接口，版本和网页变动风险高 | 中国/全球网页数据封装层 |
| Alpha Vantage | 美股实时/历史、外汇、商品、美国宏观、新闻情绪 | 有正式 API Key 和文档；覆盖股票/FX/宏观/新闻 | 免费档 25 req/day，生产需付费；中国本土指标覆盖弱 | 美股/FX/新闻情绪备源 |
| Tushare | 中国指数、A 股成交额、部分宏观与外汇数据 | 结构化、适合落库和回测 | 需 Token/积分；全球市场覆盖有限 | 中国市场盘后主备源 |
| SEC EDGAR | 美股公司 CapEx、10-K/10-Q、XBRL companyfacts | 官方、免费、结构化 | 需 CIK/tag 映射；季度口径需处理 10-K 累计值和 frame | 云巨头 CapEx 主源 |
| investing.com 网页接口 | 全球指数、期货、外汇、宏观日历 | 覆盖广，很多冷门标的网页可查 | 非官方，需 UA/Cookie，反爬强，字段和接口易变 | 最后备源/人工校验 |
| 新浪财经 | 汇率、美股报价、A 股/指数实时 | `hq.sinajs.cn/list=` 轻量；外汇代码可批量 | 需 UA/Referer；历史数据弱；全球指数覆盖不完整 | 汇率与实时行情备源 |

### 标记说明

| 标记 | 含义 |
|------|------|
| ✅ 可用 · 接口 | 可直接获取，接口名或 URL 关键词写在后面 |
| ⚠️ 有限 · 说明 | 可获取但有延迟、字段不全、需页面解析、口径不完全一致或稳定性不足 |
| ❌ 不支持 | 该源不提供或不适合作为该字段来源 |
| 🔑 需Token · 接口 | 需注册 Token/API Key，括号内注明限制或权限 |

### 全局采集原则

| 场景 | 建议 |
|------|------|
| 日线市场行情 | 盘后以 Yahoo `v8/chart` 或 Tushare/AKShare 日线固化；保留 `source`、`as_of_date`、`timezone`、`raw_payload_hash` |
| 准实时行情 | 仅核心指标轮询；Yahoo/新浪 1-5 分钟，Alpha Vantage 受免费配额限制不适合高频 |
| 月度宏观数据 | 按官方发布时间触发拉取；发布后 T+0/T+1 二次校验；FRED 使用 `realtime_start/end` 留痕 |
| SEC 财报数据 | 财报发布日/10-Q/10-K 入库后触发；季度 CapEx 需统一累计/单季口径 |
| Web scraping 接口 | 必须设置 UA/Referer，单域名并发不超过 2，遇到 403/429 冷却 30-60 分钟 |
| 数据一致性 | 同一指标保留主源与备源差异；收益率、汇率、指数点位必须注明单位和缩放因子 |

## I. 宏观经济数据

| 字段名 | 字段类型 | FRED | Yahoo Finance | AKShare | Alpha Vantage | Tushare | SEC EDGAR | investing.com | 新浪财经 | 备注 |
|--------|----------|------|---------------|---------|---------------|---------|-----------|---------------|----------|------|
| 美国 CPI（月度同比/环比） | monthly_series | 🔑 需Token · `CPIAUCSL` + `units=pc1/pch` | ❌ 不支持 | ✅ 可用 · `macro_usa_cpi_monthly()` | 🔑 需Token · `CPI`/`INFLATION` | ⚠️ 有限 · 宏观权限需校验 | ❌ 不支持 | ⚠️ 有限 · 经济日历/网页 | ❌ 不支持 | 月度，BLS 通常统计期后约 10-15 天发布 |
| 美国 PPI（月度同比/环比） | monthly_series | 🔑 需Token · `PPIACO` 或 PPI 细分 series + `units=pc1/pch` | ❌ 不支持 | ✅ 可用 · `macro_usa_ppi_monthly()` | ⚠️ 有限 · 宏观指标覆盖不如 CPI 稳定 | ⚠️ 有限 · 宏观权限需校验 | ❌ 不支持 | ⚠️ 有限 · 经济日历/网页 | ❌ 不支持 | 月度，BLS 通常统计期后约 10-15 天发布 |
| 中国 CPI（月度同比/环比） | monthly_series | ⚠️ 有限 · OECD/世界银行派生 series，非首选 | ❌ 不支持 | ✅ 可用 · `macro_china_cpi_monthly()` | ❌ 不支持 | ⚠️ 有限 · 中国宏观接口需权限校验 | ❌ 不支持 | ⚠️ 有限 · 经济日历/网页 | ❌ 不支持 | 月度，国家统计局通常统计期后约 9-15 天发布 |
| 中国 PPI（月度同比/环比） | monthly_series | ⚠️ 有限 · 国际组织派生，非首选 | ❌ 不支持 | ✅ 可用 · `macro_china_ppi_monthly()` | ❌ 不支持 | ⚠️ 有限 · 中国宏观接口需权限校验 | ❌ 不支持 | ⚠️ 有限 · 经济日历/网页 | ❌ 不支持 | 月度，国家统计局通常统计期后约 9-15 天发布 |
| 联邦基金利率目标区间 | daily/monthly_series | 🔑 需Token · `DFEDTARL/DFEDTARU`；`FEDFUNDS/DFF` 为有效利率 | ❌ 不支持 | ⚠️ 有限 · 美联储利率封装需版本校验 | 🔑 需Token · `FEDERAL_FUNDS_RATE` | ❌ 不支持 | ❌ 不支持 | ⚠️ 有限 · Fed rate 页面/日历 | ❌ 不支持 | FOMC 决议日实时变动；有效利率每日/月度 |
| FOMC 议息决议日历 | event_calendar | ⚠️ 有限 · FRED release calendar 非完整 FOMC API | ❌ 不支持 | ⚠️ 有限 · 日历类网页封装不稳定 | ⚠️ 有限 · 经济日历/新闻 | ❌ 不支持 | ❌ 不支持 | ⚠️ 有限 · 经济日历网页 | ❌ 不支持 | 建议抓 FederalReserve.gov 日历/ICS 或人工维护；结构化程度有限 |

### I 接口详情

| 接口 | 基础URL | 认证方式 | 限速估算 | 建议防拉黑延迟 | IP封锁风险 |
|------|---------|----------|----------|----------------|------------|
| FRED observations | `https://api.stlouisfed.org/fred/series/observations` | 🔑 API Key；`file_type=json` | 官方服务，建议 <120 req/min | 0.5-1s；宏观无需高频 | 低 |
| AKShare 宏观封装 | `macro_usa_cpi_monthly`、`macro_usa_ppi_monthly`、`macro_china_cpi_monthly`、`macro_china_ppi_monthly` | 无 Token；依赖 AKShare 版本 | 取决于底层站点 | 单函数 2-5s；发布日重试 | 中 |
| Alpha Vantage 宏观 | `https://www.alphavantage.co/query?function=CPI` 等 | 🔑 API Key；免费 25 req/day | 免费档 25 req/day | 12-60s；仅发布日/日批 | 低 |
| investing.com 经济日历 | 网页/非官方日历接口 | 无 Token；需 UA/Cookie | 不稳定 | 5-10s；失败冷却 30min | 高 |
| Federal Reserve 日历 | `https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm` | 无 Token；网页/ICS | 低频 | 每日一次，FOMC 周加扫 | 中 |

### I 采集策略

| 字段名 | 主源 | 备源1 | 备源2 | 建议采集频率 | 特殊时间触发点 |
|--------|------|-------|-------|--------------|----------------|
| 美国 CPI | FRED `CPIAUCSL` | AKShare `macro_usa_cpi_monthly()` | Alpha Vantage `CPI` | 每月发布日 T+0/T+1；平时月度 | BLS CPI 发布时间 |
| 美国 PPI | FRED `PPIACO`/PPI 细分 | AKShare `macro_usa_ppi_monthly()` | investing.com 日历 | 每月发布日 T+0/T+1 | BLS PPI 发布时间 |
| 中国 CPI | AKShare `macro_china_cpi_monthly()` | Tushare 宏观权限源 | investing.com 日历 | 每月发布日 T+0/T+1 | 国家统计局 CPI/PPI 发布时间 |
| 中国 PPI | AKShare `macro_china_ppi_monthly()` | Tushare 宏观权限源 | investing.com 日历 | 每月发布日 T+0/T+1 | 国家统计局 CPI/PPI 发布时间 |
| 联邦基金目标区间 | FRED `DFEDTARL/DFEDTARU` | Alpha Vantage `FEDERAL_FUNDS_RATE` | Fed 官网决议页 | 每日；FOMC 日每 15 分钟 | FOMC 声明发布、Powell 发布会 |
| FOMC 日历 | FederalReserve.gov 日历 | investing.com 经济日历 | 手工 YAML/CSV | 每周；FOMC 周每日 | 年初日历发布、临时会议 |

## J. 大宗商品与能源

| 字段名 | 字段类型 | FRED | Yahoo Finance | AKShare | Alpha Vantage | Tushare | SEC EDGAR | investing.com | 新浪财经 | 备注 |
|--------|----------|------|---------------|---------|---------------|---------|-----------|---------------|----------|------|
| 布伦特原油期货价格（日线 OHLCV） | daily_ohlcv | ⚠️ 有限 · 现货/价格 series 可作参考，非期货 OHLCV | ✅ 可用 · `BZ=F` `v8/chart` | ✅ 可用 · 外盘期货历史/实时封装 | 🔑 需Token · `BRENT` 仅价格序列，非完整期货 OHLCV | ❌ 不支持 | ❌ 不支持 | ⚠️ 有限 · Brent Futures 网页 | ⚠️ 有限 · 外盘期货代码需校验 | 日线，交易日 T+0/T+1；主源 Yahoo |
| WTI 原油期货价格（日线 OHLCV） | daily_ohlcv | ⚠️ 有限 · `DCOILWTICO` 为现货价格，非期货 OHLCV | ✅ 可用 · `CL=F` `v8/chart` | ✅ 可用 · 外盘期货历史/实时封装 | 🔑 需Token · `WTI` 仅价格序列，非完整期货 OHLCV | ❌ 不支持 | ❌ 不支持 | ⚠️ 有限 · WTI Futures 网页 | ⚠️ 有限 · 外盘期货代码需校验 | 日线，交易日 T+0/T+1；期货连续合约需注明换月 |
| XLU（日线 OHLCV、涨跌幅） | daily_ohlcv | ❌ 不支持 | ✅ 可用 · `XLU` `v8/chart` | ✅ 可用 · 美股/ETF 日线封装 | 🔑 需Token · `TIME_SERIES_DAILY`/`GLOBAL_QUOTE` | ❌ 不支持 | ❌ 不支持 | ⚠️ 有限 · ETF 网页 | ⚠️ 有限 · `gb_xlu` 报价，历史弱 | 美股交易日；涨跌幅自行计算 |

### J 接口详情

| 接口 | 基础URL | 认证方式 | 限速估算 | 建议防拉黑延迟 | IP封锁风险 |
|------|---------|----------|----------|----------------|------------|
| Yahoo chart | `https://query1.finance.yahoo.com/v8/finance/chart/{symbol}` | 无 Token；建议 UA | 30-100 req/min/IP | 1-2s；失败退避 | 中 |
| AKShare 外盘期货 | `futures_foreign_hist`、`futures_foreign_commodity_realtime` 等 | 无 Token；依赖版本 | 取决于底层东财/新浪 | 2-5s；避免高频扫全品种 | 中高 |
| Alpha Vantage 商品/股票 | `https://www.alphavantage.co/query` | 🔑 API Key；免费 25 req/day | 免费档 25 req/day | 12-60s | 低 |
| FRED 原油现货 | `fred/series/observations?series_id=DCOILWTICO` 等 | 🔑 API Key | 官方服务，低频即可 | 0.5-1s | 低 |
| investing.com 商品期货 | 商品期货历史数据网页/非官方接口 | 无 Token；需 UA/Cookie | 不稳定 | 5-10s；失败冷却 | 高 |
| 新浪外盘期货 | `https://hq.sinajs.cn/list=...` | 无 Token；需 UA/Referer | 30-80 req/min/IP | 2-5s | 中高 |

### J 采集策略

| 字段名 | 主源 | 备源1 | 备源2 | 建议采集频率 | 特殊时间触发点 |
|--------|------|-------|-------|--------------|----------------|
| 布伦特原油期货 | Yahoo `BZ=F` | AKShare 外盘期货 | investing.com | 日线盘后；核心看盘 15-60 分钟 | OPEC 会议、EIA 库存、地缘事件 |
| WTI 原油期货 | Yahoo `CL=F` | AKShare 外盘期货 | FRED `DCOILWTICO` 现货校验 | 日线盘后；核心看盘 15-60 分钟 | EIA 原油库存、OPEC、战争/制裁 |
| XLU | Yahoo `XLU` | Alpha Vantage `TIME_SERIES_DAILY` | 新浪 `gb_xlu` 实时 | 美股交易日 5-15 分钟；盘后固化 | 美债收益率急变、公用事业防御切换 |

## K. 美股关键指数与个股

| 字段名 | 字段类型 | FRED | Yahoo Finance | AKShare | Alpha Vantage | Tushare | SEC EDGAR | investing.com | 新浪财经 | 备注 |
|--------|----------|------|---------------|---------|---------------|---------|-----------|---------------|----------|------|
| SOX（日线 OHLCV、涨跌幅） | daily_ohlcv | ❌ 不支持 | ✅ 可用 · `^SOX` | ✅ 可用 · 全球指数/美股指数封装 | ⚠️ 有限 · 指数 symbol 支持不稳定 | ❌ 不支持 | ❌ 不支持 | ⚠️ 有限 · 指数网页 | ⚠️ 有限 · 美股指数报价需校验 | SOXX 可作可交易替代 |
| COMP/NDX（日线 OHLCV） | daily_ohlcv | ❌ 不支持 | ✅ 可用 · `^IXIC`、`^NDX` | ✅ 可用 · 全球指数封装 | ⚠️ 有限 · 指数 symbol 支持不稳定 | ❌ 不支持 | ❌ 不支持 | ⚠️ 有限 · 指数网页 | ⚠️ 有限 · 美股指数报价 | COMP 在 Yahoo 常用 `^IXIC`，非 `COMP` |
| SPX（日线 OHLCV） | daily_ohlcv | ⚠️ 有限 · `SP500` 仅日收盘 | ✅ 可用 · `^GSPC` | ✅ 可用 · 全球指数封装 | ⚠️ 有限 · 指数 symbol 支持不稳定 | ❌ 不支持 | ❌ 不支持 | ⚠️ 有限 · 指数网页 | ⚠️ 有限 · 美股指数报价 | `SP500` 可作收盘校验 |
| 10年期美债收益率 TNX（日线） | daily_series | ✅ 可用 · `DGS10` | ⚠️ 有限 · `^TNX` 口径/缩放需校验 | ✅ 可用 · 债券/全球利率封装视版本 | 🔑 需Token · `TREASURY_YIELD maturity=10year` | ❌ 不支持 | ❌ 不支持 | ⚠️ 有限 · 债券收益率网页 | ❌ 不支持 | 推荐 FRED；Yahoo `^TNX` 不是原始 DGS10 |
| 2年期美债收益率（日线） | daily_series | ✅ 可用 · `DGS2` | ⚠️ 有限 · Yahoo `^IRX` 是 13 周 T-bill，不是 2Y；不建议 | ⚠️ 有限 · 全球利率封装视版本 | 🔑 需Token · `TREASURY_YIELD maturity=2year` | ❌ 不支持 | ❌ 不支持 | ⚠️ 有限 · 债券收益率网页 | ❌ 不支持 | 用户写的 IRX 应修正为 FRED `DGS2` |
| 美债期限利差（10Y-2Y） | derived_series | ✅ 可用 · `DGS10-DGS2` 计算；或 FRED 利差 series | ❌ 不支持 | ⚠️ 有限 · 由收益率计算 | ⚠️ 有限 · 由收益率计算 | ❌ 不支持 | ❌ 不支持 | ⚠️ 有限 · 由网页收益率计算 | ❌ 不支持 | 计算字段，单位 pct points |
| DXY（日线 OHLCV） | daily_ohlcv | ⚠️ 有限 · `DTWEXBGS` 为贸易加权美元指数替代，不是 ICE DXY | ✅ 可用 · `DX-Y.NYB`/`DX=F` 需校验 | ✅ 可用 · 全球指数/外汇封装视版本 | ⚠️ 有限 · 可用 FX basket 自算或部分 symbol | ❌ 不支持 | ❌ 不支持 | ⚠️ 有限 · DXY 网页 | ❌ 不支持 | 免费源下 DXY 原始 ICE 数据稳定性有限 |
| NVDA/MSFT/AVGO/ANET/VRT（实时 + 日线） | quote_ohlcv | ❌ 不支持 | ✅ 可用 · ticker `v8/chart`/`quote` | ✅ 可用 · `stock_us_daily()`/美股实时封装 | 🔑 需Token · `GLOBAL_QUOTE`/`TIME_SERIES_DAILY` | ❌ 不支持 | ⚠️ 有限 · 公司事实非行情 | ⚠️ 有限 · 个股网页 | ✅ 可用 · `gb_nvda` 等实时，历史弱 | 实时 1-5 分钟，日线盘后 |

### K 接口详情

| 接口 | 基础URL | 认证方式 | 限速估算 | 建议防拉黑延迟 | IP封锁风险 |
|------|---------|----------|----------|----------------|------------|
| Yahoo chart/quote | `https://query1.finance.yahoo.com/v8/finance/chart/{symbol}` | 无 Token；建议 UA | 30-100 req/min/IP | 1-2s；403 后切 Session | 中 |
| FRED 利率/指数收盘 | `fred/series/observations` | 🔑 API Key | 官方低频 | 0.5-1s | 低 |
| Alpha Vantage 股票/债券收益率 | `https://www.alphavantage.co/query` | 🔑 API Key；免费 25 req/day | 免费档 25 req/day | 12-60s | 低 |
| AKShare 全球指数/美股 | `index_global`、`stock_us_daily`、美股实时相关函数 | 无 Token；依赖版本 | 取决于底层站点 | 2-5s | 中 |
| investing.com 指数/个股 | 指数/股票历史网页 | 无 Token；需 UA/Cookie | 不稳定 | 5-10s | 高 |
| 新浪美股报价 | `https://hq.sinajs.cn/list=gb_nvda` | 无 Token；需 UA/Referer | 30-80 req/min/IP | 2-5s | 中高 |

### K 采集策略

| 字段名 | 主源 | 备源1 | 备源2 | 建议采集频率 | 特殊时间触发点 |
|--------|------|-------|-------|--------------|----------------|
| SOX/COMP/NDX/SPX | Yahoo `^SOX/^IXIC/^NDX/^GSPC` | AKShare `index_global` | investing.com | 美股交易日 5-15 分钟；盘后固化 | 美股开盘、CPI/FOMC、NVDA 财报 |
| 10Y/2Y 美债收益率 | FRED `DGS10/DGS2` | Alpha Vantage `TREASURY_YIELD` | investing.com | 每日；美股盘中 15-60 分钟可用网页备源 | CPI/PPI/FOMC/非农 |
| 10Y-2Y 利差 | 本地计算 `DGS10-DGS2` | Alpha 数据计算 | investing.com 数据计算 | 同收益率 | 曲线倒挂/转正阈值 |
| DXY | Yahoo `DX-Y.NYB`/`DX=F` | investing.com DXY | FRED `DTWEXBGS` 替代 | 日线盘后；盘中 15-60 分钟 | FOMC、美元指数突破关键位 |
| NVDA/MSFT/AVGO/ANET/VRT | Yahoo chart/quote | Alpha Vantage | 新浪 `gb_*` 实时 | 交易时段 1-5 分钟；盘后固化 | 财报日、盘前/盘后异动、行业新闻 |

## L. 北美云巨头 CapEx

| 字段名 | 字段类型 | FRED | Yahoo Finance | AKShare | Alpha Vantage | Tushare | SEC EDGAR | investing.com | 新浪财经 | 备注 |
|--------|----------|------|---------------|---------|---------------|---------|-----------|---------------|----------|------|
| MSFT 最近4季度 CapEx | quarterly_series | ❌ 不支持 | ⚠️ 有限 · `quoteSummary cashflowStatementHistoryQuarterly` 非官方 | ❌ 不支持 | ⚠️ 有限 · 财务报表接口可能含 `capitalExpenditures` | ❌ 不支持 | ✅ 可用 · CIK `0000789019` + XBRL tag | ❌ 不支持 | ❌ 不支持 | SEC 主源；Yahoo 备源需处理负数口径 |
| AMZN 最近4季度 CapEx | quarterly_series | ❌ 不支持 | ⚠️ 有限 · `quoteSummary cashflowStatementHistoryQuarterly` | ❌ 不支持 | ⚠️ 有限 · 财务报表接口 | ❌ 不支持 | ✅ 可用 · CIK `0001018724` + XBRL tag | ❌ 不支持 | ❌ 不支持 | Amazon 可能需关注 finance lease 与 PP&E 口径差异 |
| GOOGL 最近4季度 CapEx | quarterly_series | ❌ 不支持 | ⚠️ 有限 · `quoteSummary cashflowStatementHistoryQuarterly` | ❌ 不支持 | ⚠️ 有限 · 财务报表接口 | ❌ 不支持 | ✅ 可用 · CIK `0001652044` + XBRL tag | ❌ 不支持 | ❌ 不支持 | Alphabet tag 通常可从 companyfacts 提取 |
| META 最近4季度 CapEx | quarterly_series | ❌ 不支持 | ⚠️ 有限 · `quoteSummary cashflowStatementHistoryQuarterly` | ❌ 不支持 | ⚠️ 有限 · 财务报表接口 | ❌ 不支持 | ✅ 可用 · CIK `0001326801` + XBRL tag | ❌ 不支持 | ❌ 不支持 | SEC 主源，财报日触发 |
| CapEx 同比增速 | derived_series | ❌ 不支持 | ⚠️ 有限 · 由 Yahoo cashflow 计算 | ❌ 不支持 | ⚠️ 有限 · 由 Alpha 财务计算 | ❌ 不支持 | ✅ 可用 · 由 SEC 单季 CapEx 计算 | ❌ 不支持 | ❌ 不支持 | 需统一 TTM/单季/最近4季度口径 |

### L 接口详情

| 接口 | 基础URL | 认证方式 | 限速估算 | 建议防拉黑延迟 | IP封锁风险 |
|------|---------|----------|----------|----------------|------------|
| SEC companyfacts | `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json` | 无 Token；必须设置合规 User-Agent（含联系邮箱） | SEC 建议不超过 10 req/s | 0.2-1s；公司级低频 | 低 |
| SEC submissions | `https://data.sec.gov/submissions/CIK##########.json` | 无 Token；合规 User-Agent | 同 SEC 规则 | 0.2-1s | 低 |
| Yahoo quoteSummary cashflow | `https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}?modules=cashflowStatementHistoryQuarterly` | 无 Token；可能需 Cookie/crumb | 20-60 req/min/IP | 2-5s | 中 |
| Alpha Vantage financial statements | `https://www.alphavantage.co/query?function=CASH_FLOW&symbol=MSFT` | 🔑 API Key；免费 25 req/day | 免费档 25 req/day | 12-60s | 低 |

### L 采集策略

| 字段名 | 主源 | 备源1 | 备源2 | 建议采集频率 | 特殊时间触发点 |
|--------|------|-------|-------|--------------|----------------|
| MSFT 最近4季度 CapEx | SEC companyfacts | Yahoo quoteSummary cashflow | Alpha Vantage `CASH_FLOW` | 财报季；平时每周 | 10-Q/10-K accepted 后；MSFT 财报日 |
| AMZN 最近4季度 CapEx | SEC companyfacts | Yahoo quoteSummary cashflow | Alpha Vantage `CASH_FLOW` | 财报季；平时每周 | 10-Q/10-K accepted 后；AMZN 财报日 |
| GOOGL 最近4季度 CapEx | SEC companyfacts | Yahoo quoteSummary cashflow | Alpha Vantage `CASH_FLOW` | 财报季；平时每周 | 10-Q/10-K accepted 后；GOOGL 财报日 |
| META 最近4季度 CapEx | SEC companyfacts | Yahoo quoteSummary cashflow | Alpha Vantage `CASH_FLOW` | 财报季；平时每周 | 10-Q/10-K accepted 后；META 财报日 |
| CapEx 同比增速 | 本地计算 | SEC companyfacts 复核 | Yahoo 计算复核 | 同 CapEx | 新季度数据入库后立即重算 |

### L 重点说明：SEC EDGAR 与 Yahoo CapEx

| 公司 | Ticker | CIK | SEC XBRL tag | Yahoo 备源字段 |
|------|--------|-----|--------------|----------------|
| Microsoft | MSFT | `0000789019` | `us-gaap/PaymentsToAcquirePropertyPlantAndEquipment` | `cashflowStatementHistoryQuarterly.cashflowStatements[].capitalExpenditures` |
| Amazon | AMZN | `0001018724` | `us-gaap/PaymentsToAcquirePropertyPlantAndEquipment` | 同上；需留意 lease/PP&E 口径 |
| Alphabet | GOOGL | `0001652044` | `us-gaap/PaymentsToAcquirePropertyPlantAndEquipment` | 同上 |
| Meta Platforms | META | `0001326801` | `us-gaap/PaymentsToAcquirePropertyPlantAndEquipment` | 同上 |

```python
import requests

CIK = "0000789019"
tag = "PaymentsToAcquirePropertyPlantAndEquipment"
url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json"
headers = {"User-Agent": "my-invest-global contact@example.com"}
facts = requests.get(url, headers=headers, timeout=20).json()["facts"]
items = facts["us-gaap"][tag]["units"]["USD"]
quarters = [x for x in items if x.get("form") in {"10-Q", "10-K"} and x.get("frame")]
quarters = sorted(quarters, key=lambda x: x["end"])[-8:]
capex = [(x["end"], abs(x["val"])) for x in quarters]
```

## M. 亚太半导体与新兴市场指数

| 字段名 | 字段类型 | FRED | Yahoo Finance | AKShare | Alpha Vantage | Tushare | SEC EDGAR | investing.com | 新浪财经 | 备注 |
|--------|----------|------|---------------|---------|---------------|---------|-----------|---------------|----------|------|
| KRX/KOSPI 半导体指数 | daily_ohlcv | ❌ 不支持 | ⚠️ 有限 · KOSPI `^KS11` 可用，半导体子行业 ticker 不稳定 | ⚠️ 有限 · 全球指数/韩国市场封装视版本 | ⚠️ 有限 · symbol 支持不稳定 | ❌ 不支持 | ❌ 不支持 | ⚠️ 有限 · 韩国行业指数网页 | ❌ 不支持 | KRX 半导体子行业免费结构化源不稳定，❌ 需付费终端（Wind/Bloomberg）更稳 |
| 三星电子 005930.KS 股价 | quote_ohlcv | ❌ 不支持 | ✅ 可用 · `005930.KS` | ✅ 可用 · 海外股票/韩股封装视版本 | ⚠️ 有限 · international symbol 支持不稳定 | ❌ 不支持 | ❌ 不支持 | ⚠️ 有限 · 股票网页 | ❌ 不支持 | 日线 OHLCV；实时延迟视源 |
| 台湾加权指数 TWII | daily_ohlcv | ❌ 不支持 | ✅ 可用 · `^TWII` | ✅ 可用 · 全球指数封装 | ⚠️ 有限 · 指数 symbol 支持不稳定 | ❌ 不支持 | ❌ 不支持 | ⚠️ 有限 · 指数网页 | ❌ 不支持 | 台股交易日 |
| 台积电 TSM/2330.TW | quote_ohlcv | ❌ 不支持 | ✅ 可用 · `TSM`、`2330.TW` | ✅ 可用 · 美股/台股封装视版本 | 🔑 需Token · `TSM` ADR；台股支持不稳定 | ❌ 不支持 | ⚠️ 有限 · TSM ADR 公司 filings | ⚠️ 有限 · 股票网页 | ✅ 可用 · `gb_tsm` ADR 实时 | ADR 与台股需汇率/时区口径 |
| SOXX ETF | quote_ohlcv | ❌ 不支持 | ✅ 可用 · `SOXX` | ✅ 可用 · 美股 ETF 封装 | 🔑 需Token · `SOXX` | ❌ 不支持 | ❌ 不支持 | ⚠️ 有限 · ETF 网页 | ⚠️ 有限 · `gb_soxx` 实时 | SOX 可交易替代 |

### M 接口详情

| 接口 | 基础URL | 认证方式 | 限速估算 | 建议防拉黑延迟 | IP封锁风险 |
|------|---------|----------|----------|----------------|------------|
| Yahoo chart | `https://query1.finance.yahoo.com/v8/finance/chart/{symbol}` | 无 Token；建议 UA | 30-100 req/min/IP | 1-2s | 中 |
| AKShare 全球/海外股票 | `index_global`、海外股票相关函数 | 无 Token；依赖版本 | 取决于底层站点 | 2-5s | 中 |
| Alpha Vantage 股票 | `TIME_SERIES_DAILY`、`GLOBAL_QUOTE` | 🔑 API Key；免费 25 req/day | 免费档 25 req/day | 12-60s | 低 |
| investing.com 亚太指数/股票 | 网页/非官方历史接口 | 无 Token；需 UA/Cookie | 不稳定 | 5-10s | 高 |
| 新浪美股 ADR 报价 | `https://hq.sinajs.cn/list=gb_tsm,gb_soxx` | 无 Token；需 UA/Referer | 30-80 req/min/IP | 2-5s | 中高 |

### M 采集策略

| 字段名 | 主源 | 备源1 | 备源2 | 建议采集频率 | 特殊时间触发点 |
|--------|------|-------|-------|--------------|----------------|
| KRX/KOSPI 半导体指数 | investing.com/人工校验 | KOSPI `^KS11` + 三星/SK 海力士 proxy | 付费终端 | 日线盘后 | 韩国半导体政策/三星业绩 |
| 三星电子 | Yahoo `005930.KS` | investing.com | AKShare 海外股票 | 韩国交易日盘后；盘中 15-30 分钟 | 三星业绩/存储价格异动 |
| 台湾加权指数 | Yahoo `^TWII` | AKShare `index_global` | investing.com | 台股交易日盘后；盘中 15-30 分钟 | 台股开盘、台积电法说 |
| 台积电 | Yahoo `TSM/2330.TW` | Alpha `TSM` ADR | 新浪 `gb_tsm` | ADR 美股时段；台股日线盘后 | TSM 法说、月营收 |
| SOXX | Yahoo `SOXX` | Alpha Vantage | 新浪 `gb_soxx` | 美股交易日 5-15 分钟；盘后 | SOX/半导体板块异动 |

## N. 中国市场关键指标

| 字段名 | 字段类型 | FRED | Yahoo Finance | AKShare | Alpha Vantage | Tushare | SEC EDGAR | investing.com | 新浪财经 | 备注 |
|--------|----------|------|---------------|---------|---------------|---------|-----------|---------------|----------|------|
| 富时中国A50/SGX A50 期货 | quote_ohlcv | ❌ 不支持 | ⚠️ 有限 · `CN=F`/A50 futures ticker 可用性需实测 | ✅ 可用 · 新加坡交易所期货/外盘期货封装 | ❌ 不支持 | ❌ 不支持 | ❌ 不支持 | ⚠️ 有限 · A50 Futures 网页 | ⚠️ 有限 · `hf_CHA50CFD` 等代码需校验 | 免费源稳定性一般，❌ 需付费终端（Wind/Bloomberg）更稳 |
| 科创50 000688.SH（日线 OHLCV） | daily_ohlcv | ❌ 不支持 | ⚠️ 有限 · `000688.SS` 需实测 | ✅ 可用 · `stock_zh_index_*` | ❌ 不支持 | 🔑 需Token · `index_daily` | ❌ 不支持 | ⚠️ 有限 · 指数网页 | ✅ 可用 · `sh000688` 实时，历史弱 | 日线盘后，A 股交易日 |
| USD/CNH（实时 + 日线） | fx_quote_ohlcv | ❌ 不支持 | ✅ 可用 · `CNH=X` | ✅ 可用 · `currency_boc_sina`/外汇日线封装 | 🔑 需Token · `FX_DAILY`/`CURRENCY_EXCHANGE_RATE` | ⚠️ 有限 · `fx_daily` 需权限 | ❌ 不支持 | ⚠️ 有限 · 外汇网页 | ✅ 可用 · `fx_susdcnh` | 离岸人民币，全天交易 |
| USD/CNY（实时 + 日线） | fx_quote_ohlcv | ⚠️ 有限 · 部分汇率 series，非实时 | ✅ 可用 · `CNY=X` | ✅ 可用 · `currency_boc_sina`/外汇日线封装 | 🔑 需Token · `FX_DAILY`/`CURRENCY_EXCHANGE_RATE` | ⚠️ 有限 · `fx_daily` 需权限 | ❌ 不支持 | ⚠️ 有限 · 外汇网页 | ✅ 可用 · `fx_susdcny` | 在岸人民币，中间价/即期需区分 |
| 国内绿电板块指数 | index_series | ❌ 不支持 | ❌ 不支持 | ⚠️ 有限 · 东财/同花顺概念板块封装；中证绿色电力指数需代码校验 | ❌ 不支持 | ⚠️ 有限 · 指数库需确认指数代码/权限 | ❌ 不支持 | ❌ 不支持 | ⚠️ 有限 · 概念板块实时需代码校验 | 若需正式中证指数，可能 ❌ 需付费终端（Wind/Bloomberg） |
| A股两市合计日成交额 | daily_decimal | ❌ 不支持 | ❌ 不支持 | ✅ 可用 · 沪深指数/市场总貌封装后求和 | ❌ 不支持 | 🔑 需Token · `daily_info`/指数成交额或交易所日统计权限 | ❌ 不支持 | ❌ 不支持 | ✅ 可用 · 上证/深证指数实时成交额求和 | 单位亿元；沪市+深市，注意是否含北交所 |

### N 接口详情

| 接口 | 基础URL | 认证方式 | 限速估算 | 建议防拉黑延迟 | IP封锁风险 |
|------|---------|----------|----------|----------------|------------|
| AKShare 中国指数/外汇 | `stock_zh_index_spot`、`stock_zh_index_daily`、`currency_boc_sina` 等 | 无 Token；依赖版本 | 取决于底层新浪/东财 | 2-5s | 中 |
| Tushare 指数/外汇 | `index_daily`、`fx_daily` 等 | 🔑 Token/积分 | 按积分等级 | 盘后批量 | 低 |
| Yahoo chart FX/指数 | `v8/chart/{symbol}` | 无 Token；建议 UA | 30-100 req/min/IP | 1-2s | 中 |
| Alpha Vantage FX | `FX_DAILY`、`CURRENCY_EXCHANGE_RATE` | 🔑 API Key；免费 25 req/day | 免费档 25 req/day | 12-60s | 低 |
| 新浪外汇/指数 | `https://hq.sinajs.cn/list=fx_susdcnh,fx_susdcny,sh000688` | 无 Token；需 UA/Referer | 30-80 req/min/IP | 2-5s | 中高 |
| investing.com 中国市场 | A50/FX/指数网页 | 无 Token；需 UA/Cookie | 不稳定 | 5-10s；失败冷却 | 高 |

### N 采集策略

| 字段名 | 主源 | 备源1 | 备源2 | 建议采集频率 | 特殊时间触发点 |
|--------|------|-------|-------|--------------|----------------|
| 富时中国A50/SGX A50 期货 | AKShare SGX/外盘期货 | Yahoo `CN=F` 实测 | investing.com | 交易时段 5-15 分钟；盘后固化 | A 股开盘前、夜盘、政策新闻 |
| 科创50 | AKShare 指数日线/实时 | Tushare `index_daily` | 新浪 `sh000688` | 交易时段 1-5 分钟；盘后 | A 股开盘/收盘、半导体行情 |
| USD/CNH | 新浪 `fx_susdcnh` | Yahoo `CNH=X` | Alpha `FX_DAILY` | 5-15 分钟；日线盘后 | 央行中间价、FOMC、风险事件 |
| USD/CNY | 新浪 `fx_susdcny` | Yahoo `CNY=X` | Tushare `fx_daily` | 5-15 分钟；日线盘后 | 央行中间价、外汇政策 |
| 绿电板块指数 | AKShare 概念/中证指数映射 | Tushare 指数权限 | 人工/付费终端 | 日线盘后；盘中 15 分钟 | 电价政策、绿电交易政策 |
| A股两市成交额 | AKShare 市场/指数成交额求和 | 新浪指数成交额求和 | Tushare 盘后 | 交易时段 5-15 分钟；盘后固化 | 10:00、11:30、14:30、15:00 |

## O. 地缘政治与事件驱动新闻

| 字段名 | 字段类型 | FRED | Yahoo Finance | AKShare | Alpha Vantage | Tushare | SEC EDGAR | investing.com | 新浪财经 | 备注 |
|--------|----------|------|---------------|---------|---------------|---------|-----------|---------------|----------|------|
| 全球主要财经新闻快讯 | news_json/text | ❌ 不支持 | ⚠️ 有限 · Yahoo news 非完整快讯源 | ✅ 可用 · `stock_info_global_cls()` 财联社等封装 | 🔑 需Token · `NEWS_SENTIMENT` | ❌ 不支持 | ❌ 不支持 | ⚠️ 有限 · 新闻/经济日历网页 | ✅ 可用 · 财经新闻网页/RSS 需解析 | Reuters/Bloomberg 免费 RSS 覆盖有限；完整快讯 ❌ 需付费终端（Bloomberg/Reuters） |
| 地缘政治事件监控 | news_json/text | ❌ 不支持 | ⚠️ 有限 · 新闻搜索 | ⚠️ 有限 · 财联社/新闻关键词 | 🔑 需Token · `NEWS_SENTIMENT` 按 topic/ticker | ❌ 不支持 | ❌ 不支持 | ⚠️ 有限 · 新闻网页 | ⚠️ 有限 · 新浪新闻关键词 | 结构化程度低，建议 LLM 后处理 |
| 新闻情绪/主题标签 | json | ❌ 不支持 | ⚠️ 有限 · Yahoo news 无稳定情绪 | ❌ 不支持 | 🔑 需Token · `NEWS_SENTIMENT` | ❌ 不支持 | ❌ 不支持 | ❌ 不支持 | ❌ 不支持 | 免费/低成本可用 Alpha Vantage；更强需 GDELT/NewsAPI/GNews |
| 财联社电报 | news_json/text | ❌ 不支持 | ❌ 不支持 | ✅ 可用 · `stock_info_global_cls()` | ❌ 不支持 | ❌ 不支持 | ❌ 不支持 | ❌ 不支持 | ⚠️ 有限 · 网页/非官方 | 高频抓取风险高；建议低频摘要 |

### O 接口详情

| 接口 | 基础URL | 认证方式 | 限速估算 | 建议防拉黑延迟 | IP封锁风险 |
|------|---------|----------|----------|----------------|------------|
| Alpha Vantage News Sentiment | `https://www.alphavantage.co/query?function=NEWS_SENTIMENT` | 🔑 API Key；免费 25 req/day | 免费档 25 req/day | 12-60s | 低 |
| AKShare 财联社封装 | `ak.stock_info_global_cls()` | 无 Token；依赖版本 | 取决于底层财联社 | 10-30s；避免高频 | 中高 |
| Yahoo news | `finance.yahoo.com/news` / quote news 派生 | 无 Token；可能需 Cookie | 20-60 req/min/IP | 2-5s | 中 |
| 新浪财经新闻/RSS | `finance.sina.com.cn` 新闻页/RSS | 无 Token；需 UA/Referer | 20-60 req/min/IP | 3-10s | 中高 |
| NewsAPI | `https://newsapi.org/v2/everything` | 🔑 API Key；免费档有限且生产受限 | 按套餐 | 1-5s；按配额 | 低 |
| GNews API | `https://gnews.io/api/v4/search` | 🔑 API Key；免费档有限 | 按套餐 | 1-5s；按配额 | 低 |
| GDELT 2.1 | `https://api.gdeltproject.org/api/v2/doc/doc` | 无 Token | 公共服务，需节制 | 1-5s | 低 |
| Reuters/Bloomberg RSS | 官网 RSS/网页 | 多数免费源有限；完整终端付费 | 不稳定 | 5-10s | 中高 |

### O 采集策略

| 字段名 | 主源 | 备源1 | 备源2 | 建议采集频率 | 特殊时间触发点 |
|--------|------|-------|-------|--------------|----------------|
| 全球财经新闻快讯 | Alpha Vantage `NEWS_SENTIMENT` | GDELT/NewsAPI/GNews | Yahoo/Sina 新闻 | 15-60 分钟；盘后摘要 | CPI/FOMC/非农、战争制裁、科技禁令 |
| 地缘政治事件监控 | GDELT/NewsAPI/GNews | Alpha Vantage news | 新浪/Yahoo 新闻搜索 | 30-60 分钟 | 出现“export control/sanction/Taiwan/Red Sea/OPEC”等关键词 |
| 新闻情绪/主题标签 | Alpha Vantage `NEWS_SENTIMENT` | LLM 本地打标 | GDELT themes | 30-60 分钟 | 核心股票/行业关键词命中 |
| 财联社电报 | AKShare `stock_info_global_cls()` | 财联社网页 | 手工关注列表 | 15-30 分钟；A 股盘中更密 | A 股开盘、午盘、收盘后 |

## 附录 A：全球指数与 ticker 代码对照表

| 指标 | Yahoo Finance ticker | 备选/说明 |
|------|----------------------|-----------|
| 费城半导体指数 SOX | `^SOX` | 可交易替代：`SOXX` |
| 纳斯达克综合指数 COMP | `^IXIC` | 用户写 COMP，Yahoo 常用 `^IXIC` |
| 纳斯达克100 NDX | `^NDX` | ETF 替代：`QQQ` |
| 标普500 SPX | `^GSPC` | FRED 收盘：`SP500` |
| 10Y 美债收益率 | `^TNX` | 主源建议 FRED `DGS10`；Yahoo 口径/缩放需校验 |
| 2Y 美债收益率 | 不建议用 Yahoo | 主源 FRED `DGS2`；`^IRX` 是 13 周 T-bill，不是 2Y |
| 美元指数 DXY | `DX-Y.NYB` / `DX=F` | FRED 替代：`DTWEXBGS` |
| 布伦特原油期货 | `BZ=F` | ICE Brent 连续合约 |
| WTI 原油期货 | `CL=F` | NYMEX WTI 连续合约 |
| XLU | `XLU` | 公用事业 ETF |
| NVDA/MSFT/AVGO/ANET/VRT | `NVDA` / `MSFT` / `AVGO` / `ANET` / `VRT` | 美股个股 |
| KOSPI | `^KS11` | 韩国综合指数，不是半导体子行业 |
| 三星电子 | `005930.KS` | 韩国交易所 |
| 台湾加权指数 | `^TWII` | 台股指数 |
| 台积电 ADR | `TSM` | 美股 ADR |
| 台积电台股 | `2330.TW` | 台股代码 |
| SOXX ETF | `SOXX` | SOX 可交易替代 |
| A50 期货 | `CN=F` | 可用性需实测；SGX/新浪/Investing 备查 |
| 科创50 | `000688.SS` | Yahoo 可用性需实测；新浪 `sh000688` |
| 离岸人民币 | `CNH=X` | 新浪 `fx_susdcnh` |
| 在岸人民币 | `CNY=X` | 新浪 `fx_susdcny` |

## 附录 C：FRED 常用 series_id 速查表

| series_id | 中文名称 | 更新频率 | 单位 | 典型延迟 |
|-----------|----------|----------|------|----------|
| `CPIAUCSL` | 美国 CPI：所有城市消费者，季调 | 月度 | 指数 1982-84=100 | 月度，发布滞后约 10-15 天 |
| `CPIAUCNS` | 美国 CPI：所有城市消费者，未季调 | 月度 | 指数 1982-84=100 | 月度，发布滞后约 10-15 天 |
| `PPIACO` | 美国 PPI：所有商品 | 月度 | 指数 1982=100 | 月度，发布滞后约 10-15 天 |
| `WPUFD4` | 美国 PPI：最终需求，商品/服务口径之一 | 月度 | 指数 | 月度，发布滞后约 10-15 天 |
| `DFEDTARL` | 联邦基金目标区间下限 | 日度 | Percent | FOMC 决议日更新 |
| `DFEDTARU` | 联邦基金目标区间上限 | 日度 | Percent | FOMC 决议日更新 |
| `DFF` | 有效联邦基金利率（日度） | 日度 | Percent | T+1 左右 |
| `FEDFUNDS` | 有效联邦基金利率（月度） | 月度 | Percent | 月度，滞后数日 |
| `DGS10` | 美国 10 年期国债收益率 | 日度 | Percent | T+1，节假日缺失 |
| `DGS2` | 美国 2 年期国债收益率 | 日度 | Percent | T+1，节假日缺失 |
| `T10Y2Y` | 10Y-2Y 美债利差 | 日度 | Percent | T+1，或本地用 `DGS10-DGS2` |
| `DTWEXBGS` | 贸易加权美元指数（广义，商品和服务） | 日度 | Index | T+1；非 ICE DXY |
| `SP500` | 标普500指数收盘 | 日度 | Index | T+1；仅收盘价 |
| `DCOILWTICO` | WTI 原油现货价格 | 日度 | Dollars per Barrel | T+1；非期货 OHLCV |
| `DCOILBRENTEU` | Brent 原油现货价格 | 日度 | Dollars per Barrel | T+1；非期货 OHLCV |

> FRED 同比/环比建议使用 observations 的 `units` 参数：`pc1` 为同比百分比变化，`pch` 为环比百分比变化；也可拉原始指数后本地计算以保留审计链路。

## 附录 D：AKShare 宏观/全球数据函数速查表

| 函数 | 覆盖字段 | 底层/目标地址 | 版本依赖与注意 |
|------|----------|---------------|----------------|
| `ak.macro_usa_cpi_monthly()` | 美国 CPI 月度数据 | 宏观数据网页封装 | 发布日需回归测试字段名 |
| `ak.macro_usa_ppi_monthly()` | 美国 PPI 月度数据 | 宏观数据网页封装 | 建议与 FRED 校验 |
| `ak.macro_china_cpi_monthly()` | 中国 CPI 月度数据 | 中国宏观数据网页封装 | 需确认同比/环比字段口径 |
| `ak.macro_china_ppi_monthly()` | 中国 PPI 月度数据 | 中国宏观数据网页封装 | 需确认字段更新滞后 |
| `ak.index_global()` | 全球主要指数日线/行情 | 全球指数网页封装 | 指数名称需映射到本项目 ticker |
| `ak.stock_us_daily()` | 美股日线 | 美股行情网页封装 | 建议与 Yahoo chart 校验 |
| `ak.stock_us_spot()` / 美股实时相关函数 | 美股实时/准实时 | 美股行情网页封装 | 函数名随 AKShare 版本可能调整 |
| `ak.currency_boc_sina()` | 银行/新浪外汇牌价 | 新浪/中行外汇数据 | 适合 USD/CNH、USD/CNY 备源，需字段映射 |
| `ak.fx_spot_quote()` / 外汇相关函数 | 外汇实时行情 | 新浪/外汇网页 | AKShare 版本差异较大，需锁版本 |
| `ak.futures_foreign_hist()` | 外盘期货历史 | 东财/新浪外盘期货 | 可用于 WTI/Brent/A50 备源，合约代码需校验 |
| `ak.futures_foreign_commodity_realtime()` | 外盘期货实时 | 东财/新浪外盘期货 | 实时字段稳定性需监控 |
| `ak.stock_zh_index_spot()` | 中国指数实时 | 新浪/东财指数行情 | 科创50、沪深指数实时 |
| `ak.stock_zh_index_daily()` | 中国指数日线 | 新浪/东财指数历史 | 适合 000688.SH 日线备源 |
| `ak.stock_info_global_cls()` | 财联社电报 | 财联社 | 新闻条数有限，适合事件触发摘要 |
| `ak.stock_board_concept_name_em()` | 东方财富概念板块列表 | 东方财富概念板块 | 可用于绿电概念映射，但非正式中证指数 |
| `ak.stock_board_concept_hist_em()` | 东方财富概念板块历史 | 东方财富概念板块 | 绿电板块需先确定板块名称/代码 |

## 参考资料

- FRED API `series/observations`：<https://fred.stlouisfed.org/docs/api/fred/series_observations.html>
- Alpha Vantage API Documentation：<https://www.alphavantage.co/documentation/>
- SEC EDGAR APIs：<https://www.sec.gov/search-filings/edgar-application-programming-interfaces>
- AKShare 宏观数据文档：<https://akshare.akfamily.xyz/data/macro/macro.html>
- AKShare 指数数据文档：<https://akshare.akfamily.xyz/data/index/index.html>
- AKShare 期货数据文档：<https://akshare.akfamily.xyz/data/futures/futures.html>
- Tushare 数据接口总览：<https://tushare.pro/document/2?doc_id=5>
- Yahoo Finance chart 端点参考：<https://hexdocs.pm/quant/0.1.0-alpha.1/Quant.Explorer.Providers.YahooFinance.html>
