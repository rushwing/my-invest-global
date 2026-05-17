"""MacroOrchestrator — schedules and dispatches macro indicator collection."""

from __future__ import annotations

import datetime as dt
import logging
import time as _time
from typing import Any
from zoneinfo import ZoneInfo

from engine.data_agent.sources.base import SourceError
from engine.macro_agent.indicator_groups import IndicatorConfig
from engine.macro_agent.scheduler import MacroScheduler
from engine.macro_agent.storage import MacroStorage

log = logging.getLogger(__name__)

_UTC = ZoneInfo("UTC")

# Derived indicator: 10Y-2Y yield spread
_T10Y2Y_COMPONENTS = {"DGS10", "DGS2"}

# AKShare method dispatch by indicator_id
_AKSHARE_DISPATCH: dict[str, str] = {
    "CPIAUCSL": "fetch_us_cpi",
    "PPIACO":   "fetch_us_ppi",
    "CPI_CHINA": "fetch_china_cpi",
    "PPI_CHINA": "fetch_china_ppi",
}


def _call_source(source: Any, source_name: str, indicator_id: str) -> list[dict]:
    """Dispatch the correct fetch method based on source name and indicator."""
    if source_name == "fred":
        return source.fetch_series(indicator_id)
    if source_name == "yahoo_global":
        return source.fetch_ohlcv(indicator_id)
    if source_name in ("akshare_macro", "akshare"):
        method_name = _AKSHARE_DISPATCH.get(indicator_id, "fetch_quote")
        method = getattr(source, method_name)
        if method_name == "fetch_quote":
            return method(indicator_id)
        return method()
    if source_name in ("tushare_macro", "tushare"):
        return source.fetch_quote(indicator_id)
    if source_name == "alpha_vantage":
        return source.fetch_sentiment(indicator_id)
    # Generic fallback
    return source.fetch_series(indicator_id)


class MacroOrchestrator:
    """Orchestrates macro indicator collection across Groups I–O.

    Accepts injected dependencies for testability; use from_defaults() for
    production use.
    """

    def __init__(
        self,
        storage: MacroStorage,
        scheduler: MacroScheduler,
        sources: dict[str, Any],
        rate_limiter: Any,
    ) -> None:
        self._storage = storage
        self._scheduler = scheduler
        self._sources = sources
        self._rl = rate_limiter

    @classmethod
    def from_defaults(cls) -> MacroOrchestrator:
        """Factory: build orchestrator with default real sources."""
        from engine.data_agent.rate_limiter import RateLimiter
        from engine.macro_agent.release_calendar import ReleaseCalendar
        from engine.macro_agent.sources.akshare_macro import AKShareMacroSource
        from engine.macro_agent.sources.fred import FREDSource
        from engine.macro_agent.sources.yahoo_global import YahooGlobalSource

        storage = MacroStorage()
        rate_limiter = RateLimiter()
        sources: dict[str, Any] = {
            "fred": FREDSource(rate_limiter),
            "yahoo_global": YahooGlobalSource(rate_limiter),
            "akshare_macro": AKShareMacroSource(rate_limiter),
        }
        release_cal = ReleaseCalendar(storage)
        scheduler = MacroScheduler(storage=storage, release_calendar=release_cal)
        return cls(
            storage=storage,
            scheduler=scheduler,
            sources=sources,
            rate_limiter=rate_limiter,
        )

    def run_once(
        self,
        groups: list[str] | None = None,
        now: dt.datetime | None = None,
    ) -> None:
        """Collect all due indicators once, writing results and retrieval_log rows."""
        due: list[IndicatorConfig] = self._scheduler.get_due_indicators(
            now=now, groups_filter=groups
        )
        dgs_latest: dict[str, tuple[dt.date, float]] = {}

        for cfg in due:
            t0 = _time.perf_counter()
            records: list[dict] | None = None
            succeeded_source = cfg.primary_source
            last_error: Exception | None = None

            for source_name in [cfg.primary_source, *cfg.backups]:
                source = self._sources.get(source_name)
                if source is None:
                    continue
                try:
                    records = _call_source(source, source_name, cfg.indicator_id)
                    succeeded_source = source_name
                    last_error = None
                    break
                except SourceError as exc:
                    last_error = exc
                    succeeded_source = source_name

            latency_ms = int((_time.perf_counter() - t0) * 1000)

            if records is not None and last_error is None:
                self._storage.upsert_indicators(records)
                self._storage.log_retrieval(
                    group_code=cfg.group_code,
                    indicator_id=cfg.indicator_id,
                    source=succeeded_source,
                    status="ok",
                    latency_ms=latency_ms,
                )
                if cfg.indicator_id in _T10Y2Y_COMPONENTS:
                    for rec in records:
                        v = rec.get("value")
                        if v is not None:
                            dgs_latest[cfg.indicator_id] = (rec["period_date"], v)
            else:
                self._storage.log_retrieval(
                    group_code=cfg.group_code,
                    indicator_id=cfg.indicator_id,
                    source=succeeded_source,
                    status="failed",
                    latency_ms=latency_ms,
                    error_msg=str(last_error)[:200] if last_error else None,
                )
                log.warning(
                    "all sources failed for %s: %s",
                    cfg.indicator_id, last_error,
                )

        self._compute_t10y2y(dgs_latest, now)

    def run_loop(self, poll_s: int = 60) -> None:
        """Block forever, running run_once() every poll_s seconds."""
        log.info("starting macro orchestrator loop (poll=%ds)", poll_s)
        while True:
            try:
                self.run_once()
            except Exception as exc:
                log.error("run_once error: %s", exc)
            _time.sleep(poll_s)

    # ── Private ───────────────────────────────────────────────────────────────

    def _compute_t10y2y(
        self,
        dgs_latest: dict[str, tuple[dt.date, float]],
        now: dt.datetime | None,
    ) -> None:
        if "DGS10" not in dgs_latest or "DGS2" not in dgs_latest:
            return
        date_10, v10 = dgs_latest["DGS10"]
        date_2, v2 = dgs_latest["DGS2"]
        period_date = max(date_10, date_2)
        spread = round(v10 - v2, 6)
        utc_now = (
            now.astimezone(ZoneInfo("UTC"))
            if now and now.tzinfo
            else dt.datetime.now(tz=_UTC)
        )
        self._storage.upsert_indicators([{
            "indicator_id": "T10Y2Y",
            "group_code": "K",
            "period_date": period_date,
            "market_tz": "America/New_York",
            "value": spread,
            "value_unit": "percent",
            "value_raw": str(spread),
            "source": "computed",
            "realtime_start": None,
            "vintage_as_of": None,
            "utc_ts": utc_now,
            "fetched_at": utc_now,
        }])
