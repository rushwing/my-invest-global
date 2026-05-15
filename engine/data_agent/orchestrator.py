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
    ) -> None:
        self._codes        = codes
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
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def run_once(self) -> dict[str, int]:
        """
        Execute one refresh cycle for all due FieldGroups.
        Returns a summary dict: {group_value: row_count}.
        """
        due = self._scheduler.get_due_groups(self._last_fetched)
        summary: dict[str, int] = {}

        for group in due:
            policy = FIELD_POLICIES[group]
            t0 = _time.perf_counter()
            try:
                rows = self._fetch_with_fallback(group, policy)
                count = self._storage.upsert(group, rows)
                latency = int((_time.perf_counter() - t0) * 1000)
                self._storage.log_retrieval(
                    group, policy.primary, "ok", latency_ms=latency
                )
                self._last_fetched[group] = dt.datetime.now(tz=dt.timezone.utc)
                summary[group.value] = count
                log.info("fetched %s: %d rows in %dms", group.value, count, latency)
            except AllSourcesFailedError as exc:
                latency = int((_time.perf_counter() - t0) * 1000)
                self._storage.log_retrieval(
                    group, policy.primary, "error",
                    latency_ms=latency, error_msg=str(exc)[:200],
                )
                log.warning("all sources failed for %s: %s", group.value, exc)
                summary[group.value] = 0

        return summary

    def run_loop(self) -> None:
        """Block forever, running run_once() every poll_s seconds."""
        log.info("starting orchestrator loop (poll=%ds, codes=%d)", self._poll_s, len(self._codes))
        while True:
            try:
                summary = self.run_once()
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
        policy: SourcePolicy,
    ) -> list[dict[str, Any]]:
        """
        Try primary source then each backup in order.
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
                return agent.fetch(group, self._codes, source)
            except (SourceError, Exception) as exc:
                errors.append(f"{src_name}: {exc!s:.100}")
                log.debug("source %s failed for %s: %s", src_name, group.value, exc)

        raise AllSourcesFailedError(
            f"{group.value}: all sources failed — {'; '.join(errors)}"
        )
