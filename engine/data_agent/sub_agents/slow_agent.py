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

from engine.data_agent.fields import GROUP_DISPATCH, GROUP_PER_CODE, FieldGroup
from engine.data_agent.rate_limiter import RateLimiter
from engine.data_agent.sources.base import AbstractSource, SourceError


class SlowAgent:
    """
    Serial, polite retrieval agent for web-scraping and rate-limited sources.

    Dispatches to the correct source method (fetch_quotes, fetch_kline_day,
    fetch_business_segments, etc.) based on FieldGroup rather than always
    calling fetch_quotes().

    Respects domain-level delays from the RateLimiter and stops early if the
    circuit breaker opens mid-batch.
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
        Dispatch to the right fetch method for this FieldGroup and iterate serially.
        """
        method_name = GROUP_DISPATCH.get(group)
        if not method_name:
            raise SourceError(f"No dispatch method configured for {group}")

        method = getattr(source, method_name, None)
        if method is None:
            raise SourceError(
                f"{source.name} does not implement {method_name} "
                f"(required for {group.value})"
            )

        if group in GROUP_PER_CODE:
            return self._fetch_per_code(method, codes, source)
        else:
            return self._fetch_batch(method, codes, source)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _fetch_per_code(
        self,
        method,
        codes: list[str],
        source: AbstractSource,
    ) -> list[dict[str, Any]]:
        """Call method(code) for each code serially; stop if circuit opens.

        Raises SourceError if the circuit trips before any code succeeds, so
        the orchestrator falls back to a backup source instead of recording a
        silent empty-result success.
        """
        results: list[dict[str, Any]] = []
        circuit_tripped = False
        for code in codes:
            if self._rl.is_circuit_open(source.domain):
                circuit_tripped = True
                break
            try:
                rows = method(code)
                # Normalise: methods may return list[dict] or dict or None
                if rows is None:
                    rows = []
                elif isinstance(rows, dict):
                    rows = [rows]
                results.extend(rows)
                self._rl.record_success(source.domain)
            except SourceError:
                self._rl.record_failure(source.domain, 0)
                if self._rl.is_circuit_open(source.domain):
                    circuit_tripped = True
                    break
            self._inter_code_sleep(source.domain)

        if circuit_tripped and not results:
            raise SourceError(
                f"{source.name} circuit opened before any successful fetch "
                f"(domain={source.domain})"
            )
        return results

    def _fetch_batch(
        self,
        method,
        codes: list[str],
        source: AbstractSource,
    ) -> list[dict[str, Any]]:
        """Call method(codes) once for the whole batch."""
        if self._rl.is_circuit_open(source.domain):
            raise SourceError(f"Circuit open for {source.domain}")
        try:
            rows = method(codes)
            self._rl.record_success(source.domain)
            return rows or []
        except SourceError:
            self._rl.record_failure(source.domain, 0)
            raise

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
