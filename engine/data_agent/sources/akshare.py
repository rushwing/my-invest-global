"""
AKShare data source (akshare==1.18.60).

Wraps the 27 functions validated in docs/akshare-validation-report.md.
Used primarily as a backup/fallback for K-line, fundamentals, and fund-flow data
when primary sources (Tencent, Eastmoney, Tushare) are unavailable.

Parameter notes (verified 2026-05-16 against akshare 1.18.60):
  stock_individual_fund_flow: market='sh' (SSE) or 'sz' (SZSE) — NOT board name
  stock_zygc_em: symbol='SH688041' or 'SZ000001' (exchange-prefixed)
  stock_zh_a_hist: adjust='' | 'qfq' | 'hfq'
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from engine.data_agent.rate_limiter import RateLimiter
from engine.data_agent.sources.base import AbstractSource, SourceError


def _market(code: str) -> str:
    return "sh" if code.startswith(("6", "9")) else "sz"


def _em_prefix(code: str) -> str:
    return ("SH" if code.startswith(("6", "9")) else "SZ") + code


class AKShareSource(AbstractSource):
    """AKShare 1.18.60 wrapper — fallback for K-line, fundamentals, and more."""

    name = "akshare"
    domain = "akshare"  # virtual domain — RateLimiter uses its own config entry

    def __init__(self, rate_limiter: RateLimiter) -> None:
        super().__init__(rate_limiter)
        try:
            import akshare as ak
            assert ak.__version__ == "1.18.60", (
                f"Expected akshare==1.18.60, got {ak.__version__}. "
                "Run: uv sync --extra data"
            )
            self._ak = ak
        except ImportError as exc:
            raise ImportError(
                "akshare is not installed. Run: uv sync --extra data"
            ) from exc

    # ── AbstractSource interface ──────────────────────────────────────────────

    def fetch_quotes(self, codes: list[str]) -> list[dict[str, Any]]:
        """
        AKShare does not provide efficient batch real-time quotes.
        Use stock_zh_a_spot_em() to get all A-shares at once and filter.
        Note: this function uses Eastmoney push2 CDN and may SKIP in non-CN networks.
        """
        self._rl.acquire(self.domain)
        try:
            df = self._ak.stock_zh_a_spot_em()
            self._rl.record_success(self.domain)
        except Exception as exc:
            self._rl.record_failure(self.domain, 0)
            raise SourceError(f"akshare stock_zh_a_spot_em failed: {exc}") from exc

        code_set = set(codes)
        results = []
        for _, row in df.iterrows():
            code = str(row.get("代码", ""))
            if code not in code_set:
                continue
            results.append({
                "code": code,
                "quote_time": dt.datetime.now(tz=dt.UTC),
                "price": row.get("最新价"),
                "pct_change": row.get("涨跌幅"),
                "volume": row.get("成交量"),
                "amount": row.get("成交额"),
                "market_cap": row.get("总市值"),
                "dynamic_pe": row.get("市盈率-动态"),
                "pb": row.get("市净率"),
                "turnover_rate": row.get("换手率"),
                "source": "akshare",
            })
        return results

    # ── K-line ────────────────────────────────────────────────────────────────

    def fetch_kline_day(
        self,
        code: str,
        start: dt.date | None = None,
        end: dt.date | None = None,
        adjust: str = "qfq",
    ) -> list[dict[str, Any]]:
        """Daily K-line via stock_zh_a_hist()."""
        end_date   = end or dt.date.today()
        start_date = start or (end_date - dt.timedelta(days=420))
        self._rl.acquire(self.domain)
        try:
            df = self._ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                adjust=adjust,
            )
            self._rl.record_success(self.domain)
        except Exception as exc:
            self._rl.record_failure(self.domain, 0)
            raise SourceError(f"akshare stock_zh_a_hist({code}) failed: {exc}") from exc

        results = []
        for _, row in df.iterrows():
            results.append({
                "code": code,
                "trade_date": str(row.get("日期", ""))[:10],
                "open": row.get("开盘"),
                "close": row.get("收盘"),
                "high": row.get("最高"),
                "low": row.get("最低"),
                "volume": row.get("成交量"),
                "amount": row.get("成交额"),
                "adj_type": adjust or "none",
                "source": "akshare",
            })
        return results

    # ── Business segments ─────────────────────────────────────────────────────

    def fetch_business_segments(self, code: str) -> list[dict[str, Any]]:
        """Business segment breakdown via stock_zygc_em()."""
        symbol = _em_prefix(code)
        self._rl.acquire(self.domain)
        try:
            df = self._ak.stock_zygc_em(symbol=symbol)
            self._rl.record_success(self.domain)
        except Exception as exc:
            self._rl.record_failure(self.domain, 0)
            raise SourceError(f"akshare stock_zygc_em({symbol}) failed: {exc}") from exc

        results = []
        for _, row in df.iterrows():
            results.append({
                "code": code,
                "report_date": str(row.get("报告期", ""))[:10],
                "segment_name": str(row.get("项目名称", "")),
                "revenue": row.get("营业收入-营业收入"),
                "profit": row.get("营业利润-营业利润"),
                "revenue_ratio": row.get("营业收入-收入比例"),
                "profit_ratio": row.get("营业利润-利润比例"),
                "source": "akshare",
            })
        return results

    # ── Fund flow ─────────────────────────────────────────────────────────────

    def fetch_fund_flow(self, code: str) -> list[dict[str, Any]]:
        """Individual stock fund flow via stock_individual_fund_flow()."""
        market = _market(code)
        self._rl.acquire(self.domain)
        try:
            df = self._ak.stock_individual_fund_flow(stock=code, market=market)
            self._rl.record_success(self.domain)
        except Exception as exc:
            self._rl.record_failure(self.domain, 0)
            raise SourceError(f"akshare fund_flow({code}) failed: {exc}") from exc

        results = []
        for _, row in df.iterrows():
            results.append({
                "code": code,
                "trade_date": str(row.get("日期", ""))[:10],
                "main_net_inflow": row.get("主力净流入-净额"),
                "super_large_net": row.get("超大单净流入-净额"),
                "large_net": row.get("大单净流入-净额"),
                "medium_net": row.get("中单净流入-净额"),
                "small_net": row.get("小单净流入-净额"),
                "source": "akshare",
            })
        return results
