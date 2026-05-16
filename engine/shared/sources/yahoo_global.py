"""
Yahoo Finance source for global indices, futures, FX, and US equities.

Uses yfinance for OHLCV fetching. Handles crumb-based quoteSummary for
CapEx backup (BP-8). Returns records with period_date / market_tz / utc_ts
matching macro_indicators DDL (BP-5).
"""

from __future__ import annotations

import datetime as dt
from typing import Any
from zoneinfo import ZoneInfo

from engine.data_agent.rate_limiter import RateLimiter
from engine.shared.sources.base_macro import MacroAbstractSource

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


class YahooGlobalSource(MacroAbstractSource):
    name = "yahoo_global"
    domain = "query1.finance.yahoo.com"

    def __init__(self, rate_limiter: RateLimiter) -> None:
        super().__init__(rate_limiter)
        self._crumb: str | None = None
        self._crumb_refreshed_at: dt.datetime | None = None

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
        Fetch Yahoo Finance quoteSummary for a single ticker.
        Used as CapEx backup (cashflowStatementHistoryQuarterly).
        """
        try:
            import yfinance as yf
        except ImportError as exc:
            raise ImportError(
                "yfinance is required: uv pip install 'my-invest-global[data]'"
            ) from exc

        t = yf.Ticker(ticker)
        result: dict[str, Any] = {}
        requested = modules or ["cashflowStatementHistoryQuarterly"]
        if "cashflowStatementHistoryQuarterly" in requested:
            try:
                cf = t.quarterly_cashflow
                result["cashflowStatementHistoryQuarterly"] = cf.to_dict() if cf is not None else {}
            except Exception:
                result["cashflowStatementHistoryQuarterly"] = {}
        return result
