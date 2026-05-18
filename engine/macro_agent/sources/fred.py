"""FREDSource — FRED (Federal Reserve Economic Data) series fetcher."""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any
from zoneinfo import ZoneInfo

from engine.data_agent.sources.base import SourceError

log = logging.getLogger(__name__)
_UTC = ZoneInfo("UTC")

_FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"


class FREDSource:
    """Fetches macroeconomic series from FRED."""

    name = "fred"

    def __init__(self, rate_limiter: Any = None) -> None:
        self._rl = rate_limiter

    def fetch_series(self, series_id: str) -> list[dict[str, Any]]:
        """Fetch latest observations for a FRED series.

        Returns a list of macro_indicators-compatible dicts.
        Raises SourceError on HTTP or parse failure.
        """
        import os

        import httpx

        api_key = os.getenv("FRED_API_KEY", "")
        if not api_key:
            raise SourceError("FRED_API_KEY not set")

        try:
            resp = httpx.get(
                _FRED_API_URL,
                params={
                    "series_id": series_id,
                    "api_key": api_key,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": 2,
                },
                timeout=20,
            )
            resp.raise_for_status()
        except Exception as exc:
            raise SourceError(f"FRED HTTP error for {series_id}: {exc}") from exc

        try:
            obs = resp.json().get("observations", [])
            now_utc = dt.datetime.now(tz=_UTC)
            records = []
            for o in obs:
                if o.get("value") == ".":
                    continue
                try:
                    period_date = dt.date.fromisoformat(o["date"])
                    value = float(o["value"])
                except (KeyError, ValueError):
                    continue
                records.append({
                    "indicator_id": series_id,
                    "group_code": "",
                    "period_date": period_date,
                    "market_tz": "America/New_York",
                    "value": value,
                    "value_unit": None,
                    "value_raw": o["value"],
                    "source": self.name,
                    "realtime_start": dt.date.fromisoformat(o["realtime_start"])
                    if o.get("realtime_start") else None,
                    "vintage_as_of": None,
                    "utc_ts": now_utc,
                    "fetched_at": now_utc,
                })
            if not records:
                raise SourceError(f"No observations returned for {series_id}")
            return records
        except SourceError:
            raise
        except Exception as exc:
            raise SourceError(f"FRED parse error for {series_id}: {exc}") from exc
