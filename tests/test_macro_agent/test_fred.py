"""
Tests for FREDSource — covers TC-006-01 and TC-006-02.
"""

from __future__ import annotations

import datetime as dt
from unittest.mock import patch

import pytest

from engine.data_agent.rate_limiter import RateLimiter
from engine.shared.sources.fred import FREDSource


@pytest.fixture()
def rate_limiter() -> RateLimiter:
    return RateLimiter()


@pytest.fixture()
def fred(monkeypatch: pytest.MonkeyPatch, rate_limiter: RateLimiter) -> FREDSource:
    monkeypatch.setenv("FRED_API_KEY", "test_key")
    return FREDSource(rate_limiter)


# TC-006-01: fetch_series returns records with realtime_start and vintage_as_of fields
def test_fetch_series_returns_realtime_start(fred: FREDSource) -> None:
    mock_response = {
        "observations": [
            {"date": "2026-04-01", "value": "3.5", "realtime_start": "2026-04-11"},
        ]
    }
    with patch.object(fred, "_get", return_value=mock_response):
        results = fred.fetch_series(
            "CPIAUCSL",
            start_date="2026-01-01",
            realtime_start="2026-04-01",
        )

    assert len(results) >= 1
    rec = results[0]
    assert rec["indicator_id"] == "CPIAUCSL"
    assert rec["value"] == pytest.approx(3.5)
    assert rec["realtime_start"] == dt.date(2026, 4, 1)
    assert rec["vintage_as_of"] == dt.date.today()


# TC-006-01 supplement: "." values are skipped
def test_fetch_series_skips_missing_values(fred: FREDSource) -> None:
    mock_response = {
        "observations": [
            {"date": "2026-03-01", "value": ".", "realtime_start": "2026-04-01"},
            {"date": "2026-04-01", "value": "3.5", "realtime_start": "2026-04-01"},
        ]
    }
    with patch.object(fred, "_get", return_value=mock_response):
        results = fred.fetch_series("CPIAUCSL")
    assert len(results) == 1
    assert results[0]["value"] == pytest.approx(3.5)


# TC-006-02: missing FRED_API_KEY raises RuntimeError at construction time
def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch, rate_limiter: RateLimiter) -> None:
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="FRED_API_KEY"):
        FREDSource(rate_limiter)
