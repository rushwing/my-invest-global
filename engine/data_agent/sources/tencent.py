"""
Tencent Securities data source.

Endpoints used:
  - qt.gtimg.cn/q=                 real-time batch quotes (up to 40 codes/request)
  - web.ifzq.gtimg.cn fqkline/get  daily K-line + embedded quote (refactored from
                                   scripts/refresh_aidc_data.py:fetch_tencent_stock)

Quote field index reference (Tencent qt API, verified 2026-05):
  [3]  current price
  [30] quote timestamp (YYYYMMDDHHmmss)
  [32] daily pct change
  [36] volume (lots = 100 shares)
  [37] amount (wan = 10,000 yuan)   fallback
  [39] dynamic PE
  [45] total market cap (yi = 100M yuan)
  [57] amount (wan) preferred field
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

from engine.data_agent.rate_limiter import RateLimiter
from engine.data_agent.sources.base import AbstractSource, SourceError

_BATCH_SIZE = 40  # safe batch size for qt.gtimg.cn


def _market_prefix(code: str) -> str:
    """Return 'sh' for SSE codes (6xx, 9xx) else 'sz'."""
    return "sh" if code.startswith(("6", "9")) else "sz"


def _tencent_symbol(code: str) -> str:
    return _market_prefix(code) + code


def _parse_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _chunk(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


class TencentSource(AbstractSource):
    """Real-time batch quotes and daily K-line from Tencent Securities."""

    name = "tencent"
    domain = "qt.gtimg.cn"

    def __init__(self, rate_limiter: RateLimiter) -> None:
        super().__init__(rate_limiter)
        # Override Referer for the ifzq sub-domain
        self._session.headers["Referer"] = "https://finance.qq.com/"

    # ── AbstractSource interface ──────────────────────────────────────────────

    def fetch_quotes(self, codes: list[str]) -> list[dict[str, Any]]:
        """
        Fetch real-time quotes for up to len(codes) stocks via qt.gtimg.cn.
        Returns normalised dicts suitable for storage.upsert_quotes().
        """
        results: list[dict[str, Any]] = []
        for batch in _chunk(codes, _BATCH_SIZE):
            results.extend(self._fetch_quote_batch(batch))
        return results

    # ── Additional fetchers ───────────────────────────────────────────────────

    def fetch_kline_day(
        self,
        code: str,
        end: date | None = None,
        lookback_days: int = 420,
        adjust: str = "qfq",
    ) -> dict[str, Any]:
        """
        Fetch daily K-line + embedded real-time quote for one stock.
        Refactored from scripts/refresh_aidc_data.py:fetch_tencent_stock().

        Returns a dict with keys: code, quote_time, price, pct_change, volume,
        amount, market_cap, dynamic_pe, kline (list of {date, open, high, low, close, volume}).
        """
        end_date = end or date.today()
        start_date = end_date - timedelta(days=lookback_days)
        symbol = _tencent_symbol(code)

        url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        params = {
            "param": f"{symbol},day,{start_date:%Y-%m-%d},{end_date:%Y-%m-%d},200,{adjust}"
        }

        # Use _get with the ifzq domain
        saved_domain = self.domain
        self.domain = "web.ifzq.gtimg.cn"
        try:
            payload = self._get(url, params=params)
        finally:
            self.domain = saved_domain

        data = payload["data"][symbol]
        quote = data["qt"][symbol]
        kline_raw = data.get("qfqday") or data.get("day") or []

        quote_time_str = quote[30]
        try:
            quote_time = datetime.strptime(quote_time_str, "%Y%m%d%H%M%S")
        except ValueError:
            quote_time = datetime.now()

        kline = [
            {
                "date": row[0],
                "open": _parse_float(str(row[1])),
                "close": _parse_float(str(row[2])),
                "high": _parse_float(str(row[3])),
                "low": _parse_float(str(row[4])),
                "volume": _parse_float(str(row[5])),
            }
            for row in kline_raw
            if len(row) >= 6
        ]

        return {
            "code": code,
            "quote_time": quote_time,
            "price": _parse_float(quote[3]),
            "pct_change": _parse_float(quote[32]),
            "volume": _parse_float(quote[36]),
            "amount": _parse_float(quote[57]) or _parse_float(quote[37]),
            "market_cap": _parse_float(quote[45]),  # 亿元
            "dynamic_pe": _parse_float(quote[39]),
            "kline": kline,
            "source": "tencent",
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _fetch_quote_batch(self, codes: list[str]) -> list[dict[str, Any]]:
        """
        Fetch one batch of up to BATCH_SIZE codes from qt.gtimg.cn.
        Response format: v_sh600000="1~name~code~price~...";
        """
        symbols = ",".join(_tencent_symbol(c) for c in codes)
        url = f"https://qt.gtimg.cn/q={symbols}"
        self._rl.acquire(self.domain)
        try:
            resp = self._session.get(url, timeout=15)
            resp.raise_for_status()
            self._rl.record_success(self.domain)
        except Exception as exc:
            self._rl.record_failure(self.domain, 0)
            raise SourceError(f"tencent batch quote failed: {exc}") from exc

        return self._parse_qt_response(resp.text, codes)

    def _parse_qt_response(self, text: str, codes: list[str]) -> list[dict[str, Any]]:
        """Parse the pipe-delimited qt.gtimg.cn response into normalised dicts."""
        results = []
        code_set = set(codes)
        for line in text.strip().split(";"):
            line = line.strip()
            if not line:
                continue
            match = re.match(r'v_(\w+)="(.+)"', line)
            if not match:
                continue
            symbol = match.group(1)
            fields = match.group(2).split("~")
            # Extract the 6-digit code from symbol (sh600000 → 600000)
            raw_code = symbol[2:]
            if raw_code not in code_set:
                continue
            if len(fields) < 58:
                continue
            try:
                quote_time = datetime.strptime(fields[30], "%Y%m%d%H%M%S")
            except (ValueError, IndexError):
                continue
            results.append({
                "code": raw_code,
                "quote_time": quote_time,
                "price": _parse_float(fields[3]),
                "pct_change": _parse_float(fields[32]),
                "volume": _parse_float(fields[36]),
                "amount": _parse_float(fields[57]) or _parse_float(fields[37]),
                "market_cap": _parse_float(fields[45]),
                "dynamic_pe": _parse_float(fields[39]),
                "pb": _parse_float(fields[46]) if len(fields) > 46 else None,
                "turnover_rate": _parse_float(fields[38]) if len(fields) > 38 else None,
                "source": "tencent",
            })
        return results
