"""
StockDataOrchestrator — main agent loop.

Drives the fetch cycle:
  1. Ask the Scheduler which FieldGroups are due.
  2. For each due group, try the primary source; fall back through backups.
  3. Route to FastAgent (async batch) or SlowAgent (serial) based on source type.
  4. Upsert results into Storage and log each attempt to retrieval_log.
  5. Sleep poll_s seconds and repeat.

Usage:
    from engine.data_agent.orchestrator import StockDataOrchestrator
    orch = StockDataOrchestrator.from_defaults(codes)
    orch.run_loop()         # blocking
    # or:
    summary = orch.run_once()   # one cycle
"""

from __future__ import annotations

import datetime as dt
import time as _time
import logging
from typing import Any

from engine.data_agent.fields import (
    FAST_SOURCES,
    FIELD_POLICIES,
    FieldGroup,
    SourcePolicy,
)
from engine.data_agent.rate_limiter import RateLimiter
from engine.data_agent.scheduler import Schedule
from engine.data_agent.sources.base import AbstractSource, SourceError
from engine.data_agent.storage import Storage
from engine.data_agent.sub_agents.fast_agent import FastAgent
from engine.data_agent.sub_agents.slow_agent import SlowAgent

log = logging.getLogger(__name__)

# Default Chinese market index symbols to fetch for FieldGroup.INDEX.
# These are passed to fetch_index_quotes() as pre-prefixed Tencent/Sina symbols.
DEFAULT_INDEX_CODES: list[str] = [
    "sh000001",  # 上证综指
    "sz399001",  # 深证成指
    "sz399006",  # 创业板指
    "sh000016",  # 上证50
    "sh000300",  # 沪深300
]


class AllSourcesFailedError(Exception):
    pass


class StockDataOrchestrator:
    """
    Main orchestrator: schedule → dispatch → merge → persist.
    """

    def __init__(
        self,
        codes: list[str],
        sources: dict[str, AbstractSource],
        storage: Storage,
        fast: FastAgent,
        slow: SlowAgent,
        scheduler: Schedule,
        rate_limiter: RateLimiter,
        poll_s: int = 30,
        index_codes: list[str] | None = None,
    ) -> None:
        self._codes        = codes
        self._index_codes  = index_codes if index_codes is not None else DEFAULT_INDEX_CODES
        self._sources      = sources
        self._storage      = storage
        self._fast         = fast
        self._slow         = slow
        self._scheduler    = scheduler
        self._rl           = rate_limiter
        self._poll_s       = poll_s
        self._last_fetched: dict[FieldGroup, dt.datetime | None] = {
            g: None for g in FieldGroup
        }

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def from_defaults(
        cls,
        codes: list[str],
        poll_s: int = 30,
        extra_sources: dict[str, AbstractSource] | None = None,
        rate_limiter: RateLimiter | None = None,
        index_codes: list[str] | None = None,
    ) -> "StockDataOrchestrator":
        """
        Build an orchestrator with all default sources wired up.
        Only Tencent and Eastmoney are available at this stage;
        remaining sources (akshare, tushare, sina, yahoo, cninfo) are added
        as they are implemented.

        Pass ``rate_limiter`` to share a single RateLimiter instance across all
        sources and agents so circuit-breaker and backoff state is global.
        """
        from engine.data_agent.sources.tencent import TencentSource
        from engine.data_agent.sources.eastmoney import EastmoneySource

        rl = rate_limiter if rate_limiter is not None else RateLimiter()
        sources: dict[str, AbstractSource] = {
            "tencent":   TencentSource(rl),
            "eastmoney": EastmoneySource(rl),
        }
        if extra_sources:
            sources.update(extra_sources)

        storage   = Storage()
        fast      = FastAgent(rl)
        slow      = SlowAgent(rl)
        scheduler = Schedule()

        return cls(
            codes=codes,
            sources=sources,
            storage=storage,
            fast=fast,
            slow=slow,
            scheduler=scheduler,
            rate_limiter=rl,
            poll_s=poll_s,
            index_codes=index_codes,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def run_once(
        self,
        groups: list[FieldGroup] | None = None,
    ) -> dict[str, int]:
        """
        Execute one refresh cycle.
        Pass ``groups`` to force-fetch specific FieldGroups regardless of schedule;
        omit to let the scheduler decide which groups are due.
        Returns a summary dict: {group_value: row_count}.
        """
        due: list[FieldGroup] = groups if groups is not None else self._scheduler.get_due_groups(self._last_fetched)
        summary: dict[str, int] = {}

        for group in due:
            policy = FIELD_POLICIES[group]
            # INDEX group uses its own universe of index symbols, not the stock pool
            codes = self._index_codes if group == FieldGroup.INDEX else self._codes
            t0 = _time.perf_counter()
            try:
                actual_src, rows = self._fetch_with_fallback(group, codes, policy)
                count = self._storage.upsert(group, rows)
                latency = int((_time.perf_counter() - t0) * 1000)
                self._storage.log_retrieval(
                    group, actual_src, "ok", latency_ms=latency
                )
                self._last_fetched[group] = dt.datetime.now(tz=dt.timezone.utc)
                summary[group.value] = count
                log.info(
                    "fetched %s via %s: %d rows in %dms",
                    group.value, actual_src, count, latency,
                )
            except AllSourcesFailedError as exc:
                latency = int((_time.perf_counter() - t0) * 1000)
                self._storage.log_retrieval(
                    group, policy.primary, "error",
                    latency_ms=latency, error_msg=str(exc)[:200],
                )
                log.warning("all sources failed for %s: %s", group.value, exc)
                summary[group.value] = 0

        return summary

    def run_loop(self, groups: list[FieldGroup] | None = None) -> None:
        """Block forever, running run_once() every poll_s seconds.
        Pass ``groups`` to restrict every cycle to specific FieldGroups."""
        log.info("starting orchestrator loop (poll=%ds, codes=%d)", self._poll_s, len(self._codes))
        while True:
            try:
                summary = self.run_once(groups=groups)
                if summary:
                    log.info("cycle complete: %s", summary)
            except Exception as exc:
                log.exception("unexpected error in orchestrator loop: %s", exc)
            _time.sleep(self._poll_s)

    def close(self) -> None:
        self._storage.close()

    def __enter__(self) -> "StockDataOrchestrator":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _fetch_with_fallback(
        self,
        group: FieldGroup,
        codes: list[str],
        policy: SourcePolicy,
    ) -> tuple[str, list[dict[str, Any]]]:
        """
        Try primary source then each backup in order.
        Returns (actual_source_name, rows) so callers can log the real source.
        Raises AllSourcesFailedError if every source is unavailable or fails.
        """
        errors: list[str] = []
        for src_name in [policy.primary] + list(policy.backups):
            source = self._sources.get(src_name)
            if source is None:
                errors.append(f"{src_name}: not configured")
                continue
            # Check circuit by domain (where rate-limiter state is actually stored)
            if self._rl.is_circuit_open(source.domain):
                errors.append(f"{src_name}: circuit open ({source.domain})")
                continue
            try:
                agent = self._fast if src_name in FAST_SOURCES else self._slow
                rows = agent.fetch(group, codes, source)
                return src_name, rows
            except (SourceError, Exception) as exc:
                errors.append(f"{src_name}: {exc!s:.100}")
                log.debug("source %s failed for %s: %s", src_name, group.value, exc)

        raise AllSourcesFailedError(
            f"{group.value}: all sources failed — {'; '.join(errors)}"
        )
