---
name: aidc-report
description: Maintain and refresh this repository's AIDC stock research report. Use when Codex needs to add, remove, deduplicate, or reclassify A-share/US AIDC stocks; update data/agent_input/cn/stocks.yaml; refresh CN category Markdown files and data_china_aidc.md; synchronize aidc_report.html; or validate the generated AIDC report workflow.
---

# AIDC Report

Use this skill for the `my-invest-global` AIDC report workflow.

## Source Layout

- CN stock pool: `data/agent_input/cn/stocks.yaml`
- CN generated main table: `data/agent_input/cn/data_china_aidc.md`
- CN generated category files: `data/agent_input/cn/01_*.md` through `09_*.md`
- CN out-of-scope holding area: `data/agent_input/cn/_out_of_scope.md`
- US source table: `data/agent_input/us/data_us_aidc.md`
- HTML report: `aidc_report.html`
- Refresh script: `scripts/refresh_aidc_data.py`

## Data Boundaries

- Store only deterministic metadata in `stocks.yaml`: stock name, code, exchange, board, category, sub-sector, and source file.
- Keep judgmental or changing fields in Markdown/HTML output: price, daily return, market cap, PE, returns, volume, amount, product-line mix, scarcity, ranking, valuation signal, Davis double-click signal, and rating.
- Do not invent broker targets. Leave target prices blank unless a verified post-`2026-01-01` report source is recorded in `VERIFIED_TARGETS`.
- For newly added stocks, use `待补` / `待核验` placeholders for fundamentals unless reliable source data is already in the repo or explicitly supplied by the user.
- Treat Tencent quote/K-line data as the mechanical market data source used by this repo.
- Treat Eastmoney F10 `BusinessAnalysis/PageAjax` as the product-line mix source. Its profit field is main-business profit/gross-profit style segment profit, not audited attributable net profit; preserve that caveat in report notes.

## CN Classification Rules

Use the screenshot order as the formal CN taxonomy:

1. 光通信
2. 内存/半导体
3. 算力/芯片
4. PCB
5. 上游材料
6. AI服务器
7. 设备/封测
8. 散热/液冷
9. 电源系统

If the user's suggested class conflicts with the business exposure, correct it and mention the correction. Typical corrections:

- `东山精密`, `鹏鼎科技`, `信维通信` -> `PCB`
- `罗博特科`, `盛合晶微`, `联讯仪器` -> `设备/封测`
- enterprise SSD names such as `大普微` -> `内存/半导体`
- electronic copper foil, CCL, resin, CMP, wet chemicals -> `上游材料`

Put stocks that do not belong to these nine areas in `_out_of_scope.md` via the `out_of_scope` category.

## Workflow

1. Inspect current state:

```bash
git status --short
sed -n '1,220p' data/agent_input/cn/stocks.yaml
```

2. Resolve each new stock's code and board before editing. Prefer official exchange/company pages when a code is uncertain or recently listed.

3. Edit `data/agent_input/cn/stocks.yaml`.

- Deduplicate by `code`; if the same name appears twice, keep one record.
- Set `category_id`, `category`, `source_category`, `sub_sector`, and `source_file` consistently.
- Update `data_cutoff` only after a successful refresh.

4. Refresh generated artifacts:

```bash
uv run python scripts/refresh_aidc_data.py
```

This should fetch market data and product-line mix, update CN Markdown files first, then update `aidc_report.html`.

5. Validate:

```bash
uv run python scripts/refresh_aidc_data.py --check
uv run ruff check scripts/refresh_aidc_data.py tests/test_refresh_aidc_data.py
uv run pytest tests/test_refresh_aidc_data.py
```

6. Spot-check output:

```bash
rg -n "新增股票名|当日涨跌幅|成交量|产品线营收/净利份额比例|戴维斯双击观察" data/agent_input/cn aidc_report.html
```

## Output Expectations

In the final response, report:

- Which stocks were added or deduplicated.
- Any category corrections made.
- Whether CN Markdown was refreshed before HTML.
- Validation commands run and their result.
- Any remaining `待补` / `待核验` / `待获取` fields or data limitations, especially for newly listed stocks with incomplete lookback windows or unavailable product-line mix.
