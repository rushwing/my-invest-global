"""
Base class for macro indicator data sources.

Extends AbstractSource with helpers specific to macro data:
  - _make_period_record(): builds a dict matching macro_indicators DDL
  - _to_utc_ts(): converts a local datetime + tz string to UTC-aware datetime

Also registers macro-specific domain configs into the shared RateLimiter so
SEC EDGAR, FRED, and Yahoo Global are properly rate-limited without modifying
the core data_agent code.
"""

from __future__ import annotations

import datetime as dt
from typing import Any
from zoneinfo import ZoneInfo

from engine.data_agent.rate_limiter import DOMAIN_CONFIGS
from engine.data_agent.sources.base import AbstractSource

# Macro-specific rate limit configs merged into the shared DOMAIN_CONFIGS dict.
# sec.gov: official limit 10 req/s; we use 8 req/s (0.125s) for safety margin.
# stlouisfed.org: 120 req/min = 0.5s between requests.
# alphavantage.co: budget-gated separately; min_delay prevents rapid bursts.
_MACRO_DOMAIN_CONFIGS: dict[str, dict] = {
    "data.sec.gov":          {"min_delay": 0.125, "burst": 1, "cooldown_s": 60},
    "api.stlouisfed.org":    {"min_delay": 0.5,   "burst": 2},
    "query1.finance.yahoo.com": {"min_delay": 1.5, "burst": 2},
    "finance.yahoo.com":     {"min_delay": 2.0,   "burst": 1},
    "www.alphavantage.co":   {"min_delay": 60.0,  "burst": 1},  # budget-gated; slow floor
}
DOMAIN_CONFIGS.update(_MACRO_DOMAIN_CONFIGS)


class MacroAbstractSource(AbstractSource):
    """
    Base class for all macro indicator sources.

    Provides `_make_period_record()` and `_to_utc_ts()` helpers.
    Overrides `fetch_quotes()` to raise NotImplementedError — macro sources
    do not fetch per-stock quotes.
    """

    def fetch_quotes(self, codes: list[str]) -> list[dict[str, Any]]:
        raise NotImplementedError(
            f"{self.__class__.__name__} is a macro source; use specific fetch_* methods."
        )

    def _to_utc_ts(self, local_dt: dt.datetime, tz_str: str) -> dt.datetime:
        """Convert a naive or tz-aware local datetime to UTC-aware datetime."""
        if local_dt.tzinfo is None:
            local_dt = local_dt.replace(tzinfo=ZoneInfo(tz_str))
        return local_dt.astimezone(ZoneInfo("UTC"))

    def _make_period_record(
        self,
        *,
        indicator_id: str,
        group_code: str,
        period_date: dt.date,
        market_tz: str,
        value: float | None,
        value_unit: str = "",
        value_raw: str = "",
        source: str = "",
        realtime_start: dt.date | None = None,
        vintage_as_of: dt.date | None = None,
    ) -> dict[str, Any]:
        """
        Build a dict matching the macro_indicators DuckDB table schema.

        Field names here are authoritative — MacroStorage.upsert_indicators()
        consumes this dict directly.
        """
        now_utc = dt.datetime.now(tz=ZoneInfo("UTC"))
        return {
            "indicator_id":   indicator_id,
            "group_code":     group_code,
            "period_date":    period_date,
            "market_tz":      market_tz,
            "value":          value,
            "value_unit":     value_unit,
            "value_raw":      value_raw,
            "source":         source or self.name,
            "realtime_start": realtime_start,
            "vintage_as_of":  vintage_as_of or dt.date.today(),
            "utc_ts":         now_utc,
            "fetched_at":     now_utc,
        }
