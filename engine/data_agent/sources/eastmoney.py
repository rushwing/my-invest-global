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


# Eastmoney push2 returns several numeric fields as integers scaled by 100.
# Divide by this factor to get the real value (e.g. f43=1234 → price 12.34).
_EM_QUOTE_SCALE: dict[str, float] = {
    "f43":  0.01,   # current price × 100
    "f170": 0.01,   # daily pct_change × 100  (result is %)
    "f162": 0.01,   # dynamic PE × 100
    "f167": 0.01,   # PB × 100
    "f168": 0.01,   # turnover rate × 100  (result is %)
    # f47 (volume shares), f48 (amount yuan), f116/f117 (market cap yuan): no scale
}


def _em_float(data: dict, field: str) -> float | None:
    """Parse an Eastmoney push2 field, applying the scale factor if configured."""
    raw = _parse_float(data.get(field))
    if raw is None:
        return None
    scale = _EM_QUOTE_SCALE.get(field, 1.0)
    return raw * scale


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
            # parts[0] is "YYYY-MM-DD HH:MM" for minute bars — keep full datetime
            rows.append({
                "code": code,
                "bar_time": parts[0],   # full datetime string, e.g. "2026-05-16 09:30"
                "period": period,
                "open": _parse_float(parts[1]),
                "close": _parse_float(parts[2]),
                "high": _parse_float(parts[3]),
                "low": _parse_float(parts[4]),
                "volume": _parse_float(parts[5]) if len(parts) > 5 else None,
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
        if not rows:
            return []

        # Determine the latest report date across ALL rows (both type 1 and 2).
        # Only then apply the type preference within that period, so we never
        # silently return an older period's product rows when the latest period
        # only has industry-type rows.
        dates = [str(r.get("REPORT_DATE") or "")[:10] for r in rows if r.get("REPORT_DATE")]
        if not dates:
            return []
        latest_date = max(dates)
        latest_rows = [r for r in rows if str(r.get("REPORT_DATE") or "")[:10] == latest_date]

        # Within the latest period: prefer product type (2), fallback to industry type (1)
        product_rows = [r for r in latest_rows if str(r.get("MAINOP_TYPE")) == "2" and r.get("ITEM_NAME")]
        if not product_rows:
            product_rows = [r for r in latest_rows if str(r.get("MAINOP_TYPE")) == "1" and r.get("ITEM_NAME")]
        if not product_rows:
            return []

        result = []
        for r in product_rows:
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

    def fetch_fund_flow(self, code: str) -> list[dict[str, Any]]:
        """Fetch individual stock fund flow (主力净流入) via push2.eastmoney.com."""
        secid = ("1." if code.startswith(("6", "9")) else "0.") + code
        url = "https://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "secid": secid,
            "fields": "f62,f184,f66,f69,f72,f75,f78,f81,f164,f165",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        }
        payload = self._get(url, params=params)
        data = payload.get("data") or {}
        if not data:
            return []
        return [{
            "code": code,
            "trade_date": dt.date.today().isoformat(),
            "main_net_inflow": _parse_float(data.get("f62")),
            "super_large_net": _parse_float(data.get("f66")),
            "large_net": _parse_float(data.get("f72")),
            "medium_net": _parse_float(data.get("f78")),
            "small_net": _parse_float(data.get("f81")),
            "source": "eastmoney",
        }]

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
            "price":        _em_float(data, "f43"),    # ÷100
            "pct_change":   _em_float(data, "f170"),   # ÷100 → %
            "volume":       _parse_float(data.get("f47")),   # shares, no scale
            "amount":       _parse_float(data.get("f48")),   # yuan, no scale
            "market_cap":   _parse_float(data.get("f116")),  # yuan, no scale
            "dynamic_pe":   _em_float(data, "f162"),   # ÷100
            "pb":           _em_float(data, "f167"),   # ÷100
            "turnover_rate": _em_float(data, "f168"),  # ÷100 → %
            "source": "eastmoney",
        }
