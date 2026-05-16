"""
Yahoo Finance source for global indices, futures, FX, and US equities.

Uses yfinance for OHLCV fetching. Uses crumb-based quoteSummary endpoint for
CapEx backup (BP-8). Returns records with period_date / market_tz / utc_ts
matching macro_indicators DDL (BP-5).
"""

from __future__ import annotations

import datetime as dt
from typing import Any
from zoneinfo import ZoneInfo

from engine.data_agent.rate_limiter import RateLimiter
from engine.data_agent.sources.base import SourceError
from engine.shared.sources.base_macro import MacroAbstractSource

_CRUMB_COOKIE_URL = "https://finance.yahoo.com/"
_CRUMB_URL = "https://query1.finance.yahoo.com/v1/test/getcrumb"
_QUOTE_SUMMARY_BASE = "https://query1.finance.yahoo.com/v10/finance/quoteSummary"
_CRUMB_TTL_SECONDS = 86_400  # 24 hours (BP-8)

# Ticker → market timezone mapping for period_date resolution.
_TZ_MAP: dict[str, str] = {
    "^SOX":     "America/New_York",
    "^IXIC":    "America/New_York",
    "^NDX":     "America/New_York",
    "^GSPC":    "America/New_York",
    "DX-Y.NYB": "America/New_York",
    "NVDA":     "America/New_York",
    "MSFT":     "America/New_York",
    "AVGO":     "America/New_York",
    "ANET":     "America/New_York",
    "VRT":      "America/New_York",
    "SOXX":     "America/New_York",
    "TSM":      "America/New_York",   # US ADR
    "BZ=F":     "America/New_York",
    "CL=F":     "America/New_York",
    "XLU":      "America/New_York",
    "^TWII":    "Asia/Taipei",
    "2330.TW":  "Asia/Taipei",
    "005930.KS":"Asia/Seoul",
}
_DEFAULT_TZ = "UTC"

# Indicator group code by ticker prefix.
_GROUP_MAP: dict[str, str] = {
    "^SOX": "K", "^IXIC": "K", "^NDX": "K", "^GSPC": "K",
    "DX-Y.NYB": "K", "NVDA": "K", "MSFT": "K", "AVGO": "K",
    "ANET": "K", "VRT": "K",
    "BZ=F": "J", "CL=F": "J", "XLU": "J",
    "SOXX": "M", "^TWII": "M", "2330.TW": "M", "TSM": "M",
    "005930.KS": "M",
}


class _CrumbExpiredError(Exception):
    """Internal signal: Yahoo returned 401 → expire cached crumb and retry."""


class YahooGlobalSource(MacroAbstractSource):
    name = "yahoo_global"
    domain = "query1.finance.yahoo.com"

    def __init__(self, rate_limiter: RateLimiter) -> None:
        super().__init__(rate_limiter)
        self._crumb: str | None = None
        self._crumb_refreshed_at: dt.datetime | None = None

    # ── Crumb management (BP-8) ───────────────────────────────────────────────

    def _refresh_crumb(self) -> str:
        """Return cached crumb or fetch a new one. TTL = 24 hours."""
        now = dt.datetime.now(tz=ZoneInfo("UTC"))
        if (
            self._crumb is not None
            and self._crumb_refreshed_at is not None
            and (now - self._crumb_refreshed_at).total_seconds() < _CRUMB_TTL_SECONDS
        ):
            return self._crumb

        # Prime session cookies with a finance.yahoo.com visit.
        self._rl.acquire(self.domain)
        self._session.get(_CRUMB_COOKIE_URL, timeout=10)
        self._rl.record_success(self.domain)

        # Fetch crumb string.
        self._rl.acquire(self.domain)
        try:
            resp = self._session.get(_CRUMB_URL, timeout=10)
            resp.raise_for_status()
            self._rl.record_success(self.domain)
        except Exception as exc:
            self._rl.record_failure(self.domain, 0)
            raise SourceError(f"Failed to fetch Yahoo crumb: {exc}") from exc

        crumb = resp.text.strip()
        if not crumb:
            raise SourceError("Yahoo Finance returned empty crumb")
        self._crumb = crumb
        self._crumb_refreshed_at = now
        return crumb

    # ── Public API ────────────────────────────────────────────────────────────

    def fetch_ohlcv(
        self,
        tickers: list[str],
        period: str = "1d",
        group_code_override: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch latest daily OHLCV for a list of global tickers via yfinance.

        Returns records matching macro_indicators DDL:
          indicator_id, group_code, period_date, market_tz, value (close),
          value_unit, utc_ts, fetched_at.
        """
        try:
            import yfinance as yf  # optional dependency
        except ImportError as exc:
            raise ImportError(
                "yfinance is required: uv pip install 'my-invest-global[data]'"
            ) from exc

        records: list[dict[str, Any]] = []
        # Chunk to avoid overloading Yahoo on large batches.
        for i in range(0, len(tickers), 10):
            chunk = tickers[i : i + 10]
            data = yf.download(
                chunk,
                period=period,
                interval="1d",
                group_by="ticker",
                auto_adjust=True,
                progress=False,
                threads=False,
            )
            for ticker in chunk:
                tz_str = _TZ_MAP.get(ticker, _DEFAULT_TZ)
                group = group_code_override or _GROUP_MAP.get(ticker, "")
                try:
                    df = data[ticker] if len(chunk) > 1 else data
                    if df.empty:
                        continue
                    row = df.iloc[-1]
                    close_val = float(row["Close"])
                    idx = df.index[-1]
                    # yfinance index is tz-aware (UTC); convert to local market date.
                    local_date = idx.astimezone(ZoneInfo(tz_str)).date()
                    records.append(
                        self._make_period_record(
                            indicator_id=ticker,
                            group_code=group,
                            period_date=local_date,
                            market_tz=tz_str,
                            value=close_val,
                            value_unit="price",
                            value_raw=str(close_val),
                        )
                    )
                except Exception:
                    continue
        return records

    def fetch_quote_summary(
        self,
        ticker: str,
        modules: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Fetch Yahoo Finance quoteSummary for a single ticker via the crumb API.

        Used as CapEx backup source (cashflowStatementHistoryQuarterly).
        Refreshes crumb and retries once on 401 (BP-8).
        """
        requested = modules or ["cashflowStatementHistoryQuarterly"]
        crumb = self._refresh_crumb()
        url = f"{_QUOTE_SUMMARY_BASE}/{ticker}"
        params: dict[str, str] = {"modules": ",".join(requested), "crumb": crumb}

        try:
            return self._quote_summary_request(url, params)
        except _CrumbExpiredError:
            self._crumb = None  # force cache expiry
            params["crumb"] = self._refresh_crumb()
            return self._quote_summary_request(url, params)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _quote_summary_request(self, url: str, params: dict[str, str]) -> dict[str, Any]:
        """Single attempt at the quoteSummary endpoint. Raises _CrumbExpiredError on 401."""
        self._rl.acquire(self.domain)
        try:
            resp = self._session.get(url, params=params, timeout=20)
        except Exception as exc:
            self._rl.record_failure(self.domain, 0)
            raise SourceError(f"Yahoo quoteSummary network error: {exc}") from exc

        if resp.status_code == 401:
            self._rl.record_failure(self.domain, resp.status_code)
            raise _CrumbExpiredError()
        if resp.status_code in (429, 403, 503):
            self._rl.record_failure(self.domain, resp.status_code)
            raise SourceError(f"Yahoo quoteSummary rate-limited ({resp.status_code})")

        try:
            resp.raise_for_status()
        except Exception as exc:
            self._rl.record_failure(self.domain, 0)
            raise SourceError(f"Yahoo quoteSummary HTTP error: {exc}") from exc

        self._rl.record_success(self.domain)
        data: dict[str, Any] = resp.json()
        result: list[dict[str, Any]] = data.get("quoteSummary", {}).get("result") or []
        return result[0] if result else {}
