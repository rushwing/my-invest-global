"""
SlowAgent — serial retrieval with anti-blacklist delays.

Used for: Eastmoney F10/datacenter, CNINFO, AKShare wrappers, Tushare.

These sources either rate-limit aggressively, use HTML scraping that requires
polite pacing, or rely on session/cookie state that makes concurrent use unsafe.
The agent iterates through codes sequentially with configurable per-domain delays.
"""

from __future__ import annotations

import random
import time
from typing import Any

from engine.data_agent.fields import FieldGroup
from engine.data_agent.rate_limiter import RateLimiter
from engine.data_agent.sources.base import AbstractSource, SourceError


class SlowAgent:
    """
    Serial, polite retrieval agent for web-scraping and rate-limited sources.

    Respects domain-level delays from the RateLimiter and stops early if the
    circuit breaker opens mid-batch (signalling the source should be abandoned
    for this cycle; the orchestrator will try a backup source).
    """

    def __init__(self, rate_limiter: RateLimiter) -> None:
        self._rl = rate_limiter

    def fetch(
        self,
        group: FieldGroup,
        codes: list[str],
        source: AbstractSource,
    ) -> list[dict[str, Any]]:
        """
        Iterate through codes, fetching one at a time with paced delays.
        Returns all successfully retrieved rows; stops if circuit opens.
        """
        results: list[dict[str, Any]] = []
        for code in codes:
            if self._rl.is_circuit_open(source.domain):
                break  # let orchestrator fall back to backup source
            try:
                rows = source.fetch_quotes([code])
                results.extend(rows)
                self._rl.record_success(source.domain)
            except SourceError as exc:
                self._rl.record_failure(source.domain, 0)
                # On circuit open after this failure, the outer loop will break
                if self._rl.is_circuit_open(source.domain):
                    break
            # Add a small random jitter between codes to reduce detection probability
            self._inter_code_sleep(source.domain)
        return results

    def fetch_segments(
        self,
        codes: list[str],
        source: AbstractSource,
    ) -> list[dict[str, Any]]:
        """
        Fetch business segment rows (主营构成) for a list of codes.
        Source must implement fetch_business_segments(code).
        """
        results: list[dict[str, Any]] = []
        for code in codes:
            if self._rl.is_circuit_open(source.domain):
                break
            try:
                rows = source.fetch_business_segments(code)  # type: ignore[attr-defined]
                results.extend(rows)
                self._rl.record_success(source.domain)
            except (SourceError, AttributeError):
                self._rl.record_failure(source.domain, 0)
                if self._rl.is_circuit_open(source.domain):
                    break
            self._inter_code_sleep(source.domain)
        return results

    # ── Internal ──────────────────────────────────────────────────────────────

    def _inter_code_sleep(self, domain: str) -> None:
        """
        Sleep between codes using the domain's min_delay with ±20% jitter.
        The RateLimiter.acquire() already handles request-level pacing;
        this adds an extra per-code buffer to further reduce detection risk.
        """
        from engine.data_agent.rate_limiter import DOMAIN_CONFIGS, _DEFAULT_CONFIG
        cfg = DOMAIN_CONFIGS.get(domain, _DEFAULT_CONFIG)
        base = cfg.get("min_delay", 2.0) * 0.5  # half the min_delay as inter-code buffer
        jitter = base * 0.2 * (2 * random.random() - 1)
        sleep_s = max(0.0, base + jitter)
        if sleep_s > 0:
            time.sleep(sleep_s)
