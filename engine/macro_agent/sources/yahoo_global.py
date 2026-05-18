"""YahooGlobalSource — Yahoo Finance OHLCV fetcher for macro indicators."""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any
from zoneinfo import ZoneInfo

from engine.data_agent.sources.base import SourceError

log = logging.getLogger(__name__)
_UTC = ZoneInfo("UTC")


class YahooGlobalSource:
    """Fetches OHLCV data from Yahoo Finance for global macro indicators."""

    name = "yahoo_global"

    def __init__(self, rate_limiter: Any = None) -> None:
        self._rl = rate_limiter

    def fetch_ohlcv(self, ticker: str | list[str]) -> list[dict[str, Any]]:
        """Fetch latest OHLCV for a ticker symbol (or list of symbols).

        Returns a list of macro_indicators-compatible dicts.
        Raises SourceError on failure.
        """
        try:
            import yfinance as yf
        except ImportError as exc:
            raise SourceError("yfinance not installed") from exc

        try:
            tkr = yf.Ticker(ticker)
            hist = tkr.history(period="2d")
            if hist.empty:
                raise SourceError(f"No data returned for {ticker}")
            now_utc = dt.datetime.now(tz=_UTC)
            latest = hist.iloc[-1]
            idx = hist.index[-1]
            period_date = idx.date() if hasattr(idx, "date") else dt.date.today()
            return [{
                "indicator_id": ticker,
                "group_code": "",
                "period_date": period_date,
                "market_tz": "America/New_York",
                "value": float(latest["Close"]),
                "value_unit": "USD",
                "value_raw": str(latest["Close"]),
                "source": self.name,
                "realtime_start": None,
                "vintage_as_of": None,
                "utc_ts": now_utc,
                "fetched_at": now_utc,
            }]
        except SourceError:
            raise
        except Exception as exc:
            raise SourceError(f"Yahoo fetch error for {ticker}: {exc}") from exc
