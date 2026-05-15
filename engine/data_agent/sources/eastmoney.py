"""
Eastmoney data source.

Endpoints:
  - push2.eastmoney.com/api/qt/stock/get     real-time quote (single stock)
  - push2his.eastmoney.com/api/qt/stock/kline/get  historical K-line
  - emweb.securities.eastmoney.com F10        business segments (主营构成)
  - datacenter.eastmoney.com                  fund flow, earnings tables

Note: push2*.eastmoney.com uses numbered CDN subdomains (e.g. 17.push2.eastmoney.com)
that are geo-routed to mainland CN IPs.  In non-CN environments these may be
unreliable; the orchestrator should fall back to Tencent/Sina for quotes.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from engine.data_agent.rate_limiter import RateLimiter
from engine.data_agent.sources.base import AbstractSource, SourceError


def _em_code(code: str) -> str:
    """Return Eastmoney SH/SZ prefixed code."""
    return ("SH" if code.startswith(("6", "9")) else "SZ") + code


def _parse_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


class EastmoneySource(AbstractSource):
    """Eastmoney real-time quotes, K-line, business segments, and fund flow."""

    name = "eastmoney"
    domain = "push2.eastmoney.com"

    def __init__(self, rate_limiter: RateLimiter) -> None:
        super().__init__(rate_limiter)
        self._session.headers.update({
            "Referer": "https://quote.eastmoney.com/",
            "Origin": "https://quote.eastmoney.com",
        })

    # ── AbstractSource interface ──────────────────────────────────────────────

    def fetch_quotes(self, codes: list[str]) -> list[dict[str, Any]]:
        """Fetch real-time quotes one-by-one via push2.eastmoney.com."""
        results = []
        for code in codes:
            try:
                row = self._fetch_single_quote(code)
                if row:
                    results.append(row)
            except SourceError:
                raise
        return results

    # ── K-line ────────────────────────────────────────────────────────────────

    def fetch_kline_day(
        self,
        code: str,
        start: dt.date | None = None,
        end: dt.date | None = None,
        adjust: str = "qfq",   # qfq | hfq | none
    ) -> list[dict[str, Any]]:
        """Fetch adjusted daily K-line via push2his.eastmoney.com."""
        end_date   = end or dt.date.today()
        start_date = start or (end_date - dt.timedelta(days=420))
        fqt = {"qfq": "1", "hfq": "2", "none": "0"}.get(adjust, "1")
        secid = ("1." if code.startswith(("6", "9")) else "0.") + code
        url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "secid": secid,
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57",
            "klt": "101",           # 101 = daily
            "fqt": fqt,
            "beg": start_date.strftime("%Y%m%d"),
            "end": end_date.strftime("%Y%m%d"),
            "lmt": "500",
        }
        saved = self.domain
        self.domain = "push2his.eastmoney.com"
        try:
            payload = self._get(url, params=params)
        finally:
            self.domain = saved

        klines = payload.get("data", {}).get("klines") or []
        rows = []
        for item in klines:
            parts = item.split(",")
            if len(parts) < 6:
                continue
            rows.append({
                "code": code,
                "trade_date": parts[0],
                "open": _parse_float(parts[1]),
                "close": _parse_float(parts[2]),
                "high": _parse_float(parts[3]),
                "low": _parse_float(parts[4]),
                "volume": _parse_float(parts[5]),
                "amount": _parse_float(parts[6]) if len(parts) > 6 else None,
                "adj_type": adjust,
                "source": "eastmoney",
            })
        return rows

    def fetch_kline_min(
        self,
        code: str,
        period: int = 1,   # 1 | 5 | 15 | 30 | 60
    ) -> list[dict[str, Any]]:
        """Fetch 1-min (or other intraday) K-line via push2his.eastmoney.com."""
        secid = ("1." if code.startswith(("6", "9")) else "0.") + code
        url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "secid": secid,
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56",
            "klt": str(period),
            "fqt": "0",
            "beg": "0",
            "end": "20500101",
            "lmt": "1440",
        }
        saved = self.domain
        self.domain = "push2his.eastmoney.com"
        try:
            payload = self._get(url, params=params)
        finally:
            self.domain = saved

        klines = payload.get("data", {}).get("klines") or []
        rows = []
        for item in klines:
            parts = item.split(",")
            if len(parts) < 5:
                continue
            rows.append({
                "code": code,
                "trade_date": parts[0][:10],
                "open": _parse_float(parts[1]),
                "close": _parse_float(parts[2]),
                "high": _parse_float(parts[3]),
                "low": _parse_float(parts[4]),
                "volume": _parse_float(parts[5]) if len(parts) > 5 else None,
                "adj_type": "none",
                "source": "eastmoney",
            })
        return rows

    # ── Business segments (主营构成) ──────────────────────────────────────────

    def fetch_business_segments(self, code: str) -> list[dict[str, Any]]:
        """
        Fetch business segment breakdown via Eastmoney F10 PageAjax.
        Refactored from scripts/refresh_aidc_data.py:fetch_eastmoney_business_analysis().
        """
        em_code = _em_code(code)
        url = (
            "https://emweb.securities.eastmoney.com"
            f"/PC_HSF10/BusinessAnalysis/PageAjax?code={em_code}"
        )
        saved = self.domain
        self.domain = "emweb.securities.eastmoney.com"
        try:
            payload = self._get(url)
        finally:
            self.domain = saved

        return self._parse_segments(code, payload)

    def _parse_segments(self, code: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract structured rows from the zygcfx payload."""
        rows = payload.get("zygcfx") or []
        # Prefer product-type rows (MAINOP_TYPE=2), fall back to industry-type (1)
        product_rows = [r for r in rows if str(r.get("MAINOP_TYPE")) == "2" and r.get("ITEM_NAME")]
        if not product_rows:
            product_rows = [r for r in rows if str(r.get("MAINOP_TYPE")) == "1" and r.get("ITEM_NAME")]
        if not product_rows:
            return []

        # Use most recent report date
        latest_date = max(
            str(r.get("REPORT_DATE") or "")[:10] for r in product_rows
        )
        latest_rows = [
            r for r in product_rows
            if str(r.get("REPORT_DATE") or "")[:10] == latest_date
        ]

        result = []
        for r in latest_rows:
            result.append({
                "code": code,
                "report_date": latest_date,
                "segment_name": str(r.get("ITEM_NAME", "")).replace("|", "/"),
                "revenue": _parse_float(r.get("MAIN_BUSINESS_INCOME")),
                "profit": _parse_float(r.get("MAIN_BUSINESS_RPOFIT")),
                "revenue_ratio": _parse_float(r.get("MBI_RATIO")),
                "profit_ratio": _parse_float(r.get("MBR_RATIO")),
                "source": "eastmoney",
            })
        return result

    # ── Fund flow ─────────────────────────────────────────────────────────────

    def fetch_fund_flow(self, code: str) -> dict[str, Any] | None:
        """Fetch individual stock fund flow (主力净流入) via datacenter.eastmoney.com."""
        secid = ("1." if code.startswith(("6", "9")) else "0.") + code
        url = "https://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "secid": secid,
            "fields": "f62,f184,f66,f69,f72,f75,f78,f81,f164,f165",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        }
        try:
            payload = self._get(url, params=params)
        except SourceError:
            return None
        data = payload.get("data") or {}
        return {
            "code": code,
            "main_net_inflow": _parse_float(data.get("f62")),
            "super_large_net": _parse_float(data.get("f66")),
            "large_net": _parse_float(data.get("f72")),
            "medium_net": _parse_float(data.get("f78")),
            "small_net": _parse_float(data.get("f81")),
            "source": "eastmoney",
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _fetch_single_quote(self, code: str) -> dict[str, Any] | None:
        secid = ("1." if code.startswith(("6", "9")) else "0.") + code
        url = "https://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "secid": secid,
            "fields": "f43,f44,f45,f46,f47,f48,f57,f58,f60,f116,f117,f162,f163,f164,f167,f168,f169,f170,f171",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        }
        payload = self._get(url, params=params)
        data = payload.get("data")
        if not data:
            return None

        now = dt.datetime.now(tz=dt.timezone.utc)
        return {
            "code": code,
            "quote_time": now,
            "price": _parse_float(data.get("f43")),
            "pct_change": _parse_float(data.get("f170")),
            "volume": _parse_float(data.get("f47")),
            "amount": _parse_float(data.get("f48")),
            "market_cap": _parse_float(data.get("f116")),  # 亿元
            "dynamic_pe": _parse_float(data.get("f162")),
            "pb": _parse_float(data.get("f167")),
            "turnover_rate": _parse_float(data.get("f168")),
            "source": "eastmoney",
        }
