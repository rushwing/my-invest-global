"""
FRED (Federal Reserve Economic Data) source.

Fetches economic time series via the FRED REST API.
Supports realtime_start for vintage-aware queries (BP-1).

Requires env var: FRED_API_KEY
"""

from __future__ import annotations

import datetime as dt
import os
from typing import Any

from engine.data_agent.rate_limiter import RateLimiter
from engine.shared.sources.base_macro import MacroAbstractSource

_FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"


class FREDSource(MacroAbstractSource):
    name = "fred"
    domain = "api.stlouisfed.org"

    def __init__(self, rate_limiter: RateLimiter, api_key: str | None = None) -> None:
        super().__init__(rate_limiter)
        _key = api_key or os.environ.get("FRED_API_KEY")
        if not _key:
            raise RuntimeError(
                "FRED_API_KEY environment variable is not set. "
                "Obtain a free key from https://fred.stlouisfed.org/docs/api/api_key.html"
            )
        self._api_key: str = _key

    def fetch_series(
        self,
        series_id: str,
        start_date: str | dt.date | None = None,
        realtime_start: str | dt.date | None = None,
        group_code: str = "",
    ) -> list[dict[str, Any]]:
        """
        Fetch observations for a FRED series.

        Args:
            series_id:      FRED series ID (e.g. "CPIAUCSL", "DGS10").
            start_date:     Earliest observation date (YYYY-MM-DD or date).
            realtime_start: Vintage start date for historical data (BP-1).
            group_code:     Indicator group tag (e.g. "I", "K") stored in records.

        Returns:
            list of dicts compatible with macro_indicators DDL.
        """
        params: dict[str, str] = {
            "series_id":  series_id,
            "api_key":    self._api_key,
            "file_type":  "json",
            "sort_order": "asc",
        }
        if start_date:
            params["observation_start"] = str(start_date)
        if realtime_start:
            params["realtime_start"] = str(realtime_start)

        data = self._get(_FRED_BASE, params=params)
        observations: list[dict] = data.get("observations", [])

        realtime_start_date: dt.date | None = None
        if realtime_start:
            if isinstance(realtime_start, str):
                realtime_start_date = dt.date.fromisoformat(realtime_start)
            else:
                realtime_start_date = realtime_start  # type: ignore[assignment]

        records: list[dict[str, Any]] = []
        for obs in observations:
            raw_val = obs.get("value", ".")
            if raw_val == ".":
                continue
            try:
                value = float(raw_val)
            except ValueError:
                continue

            period_date = dt.date.fromisoformat(obs["date"])
            records.append(
                self._make_period_record(
                    indicator_id=series_id,
                    group_code=group_code,
                    period_date=period_date,
                    market_tz="America/New_York",
                    value=value,
                    value_raw=raw_val,
                    realtime_start=realtime_start_date,
                )
            )
        return records
