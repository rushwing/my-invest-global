"""
Alpha Vantage source for news sentiment data.

Free tier: 25 requests/day hard limit.
Budget is tracked via injected get_budget / inc_budget callables — the actual
storage backend (DuckDB alpha_vantage_budget table) is wired in by the
orchestrator (REQ-009) after MacroStorage is available.

Default (no callables injected): budget check is disabled, suitable for tests
and initial bring-up.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from engine.data_agent.rate_limiter import RateLimiter
from engine.shared.sources.base_macro import MacroAbstractSource

_AV_BASE = "https://www.alphavantage.co/query"
_BUDGET_LIMIT = 22  # refuse above this; keeps 3 in reserve for emergencies


class BudgetExhaustedError(Exception):
    """Raised when the Alpha Vantage daily request budget is exhausted."""


class AlphaVantageSource(MacroAbstractSource):
    name = "alpha_vantage"
    domain = "www.alphavantage.co"

    def __init__(
        self,
        rate_limiter: RateLimiter,
        api_key: str | None = None,
        get_budget: Callable[[], int] | None = None,
        inc_budget: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(rate_limiter)
        self._api_key = api_key or os.environ.get("ALPHA_VANTAGE_KEY", "")
        # Dependency-injected budget ledger (REQ-007 wires in real storage).
        self._get_budget: Callable[[], int] = get_budget or (lambda: 0)
        self._inc_budget: Callable[[], None] = inc_budget or (lambda: None)

    def fetch_news_sentiment(
        self,
        tickers: list[str] | None = None,
        topics: list[str] | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Fetch global news sentiment from Alpha Vantage NEWS_SENTIMENT endpoint.

        Raises:
            BudgetExhaustedError: if today's usage has reached _BUDGET_LIMIT.

        Returns:
            list of article dicts with title, url, time_published, summary,
            overall_sentiment_score, overall_sentiment_label, ticker_sentiments.
        """
        if self._get_budget() >= _BUDGET_LIMIT:
            raise BudgetExhaustedError(
                f"Alpha Vantage daily budget reached {_BUDGET_LIMIT} requests. "
                "Remaining capacity is reserved for emergency use."
            )

        params: dict[str, Any] = {
            "function": "NEWS_SENTIMENT",
            "apikey":   self._api_key,
            "limit":    limit,
            "sort":     "LATEST",
        }
        if tickers:
            params["tickers"] = ",".join(tickers)
        if topics:
            params["topics"] = ",".join(topics)

        data = self._get(_AV_BASE, params=params)
        self._inc_budget()

        feed: list[dict] = data.get("feed", [])
        return [
            {
                "title":                    art.get("title", ""),
                "url":                      art.get("url", ""),
                "time_published":           art.get("time_published", ""),
                "summary":                  art.get("summary", ""),
                "overall_sentiment_score":  art.get("overall_sentiment_score"),
                "overall_sentiment_label":  art.get("overall_sentiment_label", ""),
                "ticker_sentiments":        art.get("ticker_sentiment", []),
            }
            for art in feed
        ]
