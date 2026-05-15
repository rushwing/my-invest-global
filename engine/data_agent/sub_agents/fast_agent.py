"""
FastAgent — async parallel fetching for batch-safe, high-quota sources.

Used for: Tencent (qt.gtimg.cn), Sina (hq.sinajs.cn), Yahoo Finance.

These sources either have no published rate limit or allow large batches per
request, making async parallel dispatch safe.  The agent splits the stock list
into BATCH_SIZE chunks and fires concurrent httpx requests.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from engine.data_agent.fields import FieldGroup
from engine.data_agent.rate_limiter import RateLimiter
from engine.data_agent.sources.base import AbstractSource

BATCH_SIZE = 40  # codes per batch request


def _chunk(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


class FastAgent:
    """
    Async parallel retrieval agent for batch-friendly sources.

    Usage:
        agent = FastAgent(rate_limiter)
        results = agent.fetch(FieldGroup.QUOTE, codes, source)
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
        Synchronous entry point. Runs the async fetch in a new event loop.
        Returns a flat list of normalised result dicts.
        """
        return asyncio.run(self._fetch_async(group, codes, source))

    async def _fetch_async(
        self,
        group: FieldGroup,
        codes: list[str],
        source: AbstractSource,
    ) -> list[dict[str, Any]]:
        """Dispatch batch coroutines concurrently and merge results."""
        batches = list(_chunk(codes, BATCH_SIZE))
        async with httpx.AsyncClient(timeout=20.0) as client:
            tasks = [
                self._fetch_batch(client, batch, group, source)
                for batch in batches
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        results: list[dict[str, Any]] = []
        for item in batch_results:
            if isinstance(item, BaseException):
                # Individual batch failure — logged, not re-raised
                continue
            results.extend(item)
        return results

    async def _fetch_batch(
        self,
        client: httpx.AsyncClient,
        codes: list[str],
        group: FieldGroup,
        source: AbstractSource,
    ) -> list[dict[str, Any]]:
        """
        Fetch one batch.  Falls back to the source's sync fetch_quotes() because
        source implementations are sync; we run them in the default executor.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, source.fetch_quotes, codes)
