"""
FastAgent — async parallel fetching for batch-safe, high-quota sources.

Used for: Tencent (qt.gtimg.cn), Sina (hq.sinajs.cn), Yahoo Finance.

These sources either have no published rate limit or allow large batches per
request, making async parallel dispatch safe.  The agent dispatches to the
correct source method (fetch_quotes, fetch_kline_day, …) based on FieldGroup,
using the same GROUP_DISPATCH table as SlowAgent.
"""

from __future__ import annotations

import asyncio
from typing import Any

from engine.data_agent.fields import GROUP_DISPATCH, GROUP_PER_CODE, FieldGroup
from engine.data_agent.rate_limiter import RateLimiter
from engine.data_agent.sources.base import AbstractSource, SourceError

BATCH_SIZE = 40  # codes per batch for batch-type groups


def _chunk(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


class FastAgent:
    """
    Async parallel retrieval agent for batch-friendly sources.

    For batch groups (QUOTE, INDEX): chunks codes and runs fetch_quotes()
    concurrently.  For per-code groups (KLINE, SEGMENT, …): runs one
    fetch_<method>(code) per code concurrently in the thread pool.
    """

    def __init__(self, rate_limiter: RateLimiter) -> None:
        self._rl = rate_limiter

    def fetch(
        self,
        group: FieldGroup,
        codes: list[str],
        source: AbstractSource,
    ) -> list[dict[str, Any]]:
        """Synchronous entry point. Runs the async fetch in a new event loop."""
        method_name = GROUP_DISPATCH.get(group)
        if not method_name:
            raise SourceError(f"No dispatch method configured for {group}")

        method = getattr(source, method_name, None)
        if method is None:
            raise SourceError(
                f"{source.name} does not implement {method_name} "
                f"(required for {group.value})"
            )

        return asyncio.run(self._fetch_async(group, method, codes))

    # ── Async internals ───────────────────────────────────────────────────────

    async def _fetch_async(
        self,
        group: FieldGroup,
        method,
        codes: list[str],
    ) -> list[dict[str, Any]]:
        loop = asyncio.get_event_loop()

        if group in GROUP_PER_CODE:
            # Per-code: each code gets its own executor task
            tasks = [
                loop.run_in_executor(None, method, code)
                for code in codes
            ]
        else:
            # Batch: split into chunks, each chunk is one task
            tasks = [
                loop.run_in_executor(None, method, batch)
                for batch in _chunk(codes, BATCH_SIZE)
            ]

        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        results: list[dict[str, Any]] = []
        for item in raw_results:
            if isinstance(item, BaseException):
                continue  # individual task failure — skip, orchestrator handles fallback
            if item is None:
                continue
            if isinstance(item, dict):
                results.append(item)
            elif isinstance(item, list):
                results.extend(item)
        return results
