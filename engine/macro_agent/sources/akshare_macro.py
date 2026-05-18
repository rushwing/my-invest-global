"""AKShareMacroSource — macroeconomic data via AKShare."""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any
from zoneinfo import ZoneInfo

from engine.data_agent.sources.base import SourceError

log = logging.getLogger(__name__)
_UTC = ZoneInfo("UTC")


class AKShareMacroSource:
    """Fetches macroeconomic data via AKShare (backup for FRED on US CPI/PPI)."""

    name = "akshare_macro"

    def __init__(self, rate_limiter: Any = None) -> None:
        self._rl = rate_limiter

    def fetch_us_cpi(self) -> list[dict[str, Any]]:
        """Fetch US CPI data via AKShare."""
        return self._fetch_macro_series("CPIAUCSL", "macro_usa_cpi")

    def fetch_us_ppi(self) -> list[dict[str, Any]]:
        """Fetch US PPI data via AKShare."""
        return self._fetch_macro_series("PPIACO", "macro_usa_ppi")

    def fetch_china_cpi(self) -> list[dict[str, Any]]:
        """Fetch China CPI data via AKShare."""
        return self._fetch_macro_series("CPI_CHINA", "macro_china_cpi")

    def fetch_china_ppi(self) -> list[dict[str, Any]]:
        """Fetch China PPI data via AKShare."""
        return self._fetch_macro_series("PPI_CHINA", "macro_china_ppi")

    def fetch_quote(self, indicator_id: str) -> list[dict[str, Any]]:
        """Generic quote fetch fallback."""
        return self._fetch_macro_series(indicator_id, indicator_id.lower())

    def _fetch_macro_series(self, indicator_id: str, ak_func: str) -> list[dict[str, Any]]:
        try:
            import akshare as ak
        except ImportError as exc:
            raise SourceError("akshare not installed") from exc

        try:
            func = getattr(ak, ak_func, None)
            if func is None:
                raise SourceError(f"AKShare function not found: {ak_func}")
            df = func()
            if df is None or df.empty:
                raise SourceError(f"No data returned for {indicator_id}")
            now_utc = dt.datetime.now(tz=_UTC)
            latest = df.iloc[-1]
            return [{
                "indicator_id": indicator_id,
                "group_code": "",
                "period_date": dt.date.today(),
                "market_tz": "America/New_York",
                "value": float(latest.iloc[-1]),
                "value_unit": None,
                "value_raw": str(latest.iloc[-1]),
                "source": self.name,
                "realtime_start": None,
                "vintage_as_of": None,
                "utc_ts": now_utc,
                "fetched_at": now_utc,
            }]
        except SourceError:
            raise
        except Exception as exc:
            raise SourceError(f"AKShare fetch error for {indicator_id}: {exc}") from exc
