"""
Tests for AlphaVantageSource — covers TC-006-08.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from engine.data_agent.rate_limiter import RateLimiter
from engine.shared.sources.alpha_vantage import AlphaVantageSource, BudgetExhaustedError


@pytest.fixture()
def rate_limiter() -> RateLimiter:
    return RateLimiter()


# TC-006-08: budget >= 22 raises BudgetExhaustedError before any HTTP call
def test_budget_exhausted_raises_before_http(rate_limiter: RateLimiter) -> None:
    src = AlphaVantageSource(
        rate_limiter,
        api_key="test",
        get_budget=lambda: 22,
        inc_budget=lambda: None,
    )
    mock_get = MagicMock()
    with patch.object(src, "_get", mock_get):
        with pytest.raises(BudgetExhaustedError):
            src.fetch_news_sentiment()

    assert mock_get.call_count == 0, "_get must not be called when budget is exhausted"


# Supplement: budget < 22 proceeds to HTTP
def test_budget_under_limit_allows_http(rate_limiter: RateLimiter) -> None:
    def track_budget() -> int:
        return 21

    src = AlphaVantageSource(
        rate_limiter,
        api_key="test",
        get_budget=track_budget,
        inc_budget=lambda: None,
    )
    mock_response = {"feed": []}
    with patch.object(src, "_get", return_value=mock_response):
        result = src.fetch_news_sentiment()

    assert result == []


# Supplement: inc_budget is called on successful fetch
def test_inc_budget_called_on_success(rate_limiter: RateLimiter) -> None:
    inc_count: list[int] = [0]

    def inc() -> None:
        inc_count[0] += 1

    src = AlphaVantageSource(
        rate_limiter,
        api_key="test",
        get_budget=lambda: 0,
        inc_budget=inc,
    )
    with patch.object(src, "_get", return_value={"feed": []}):
        src.fetch_news_sentiment()

    assert inc_count[0] == 1
