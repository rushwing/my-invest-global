"""
Tests for YahooGlobalSource — covers TC-006-09 and TC-006-10.
"""

from __future__ import annotations

import datetime as dt
from unittest.mock import MagicMock, patch

import pytest

from engine.data_agent.rate_limiter import RateLimiter
from engine.shared.sources.yahoo_global import YahooGlobalSource


@pytest.fixture()
def src() -> YahooGlobalSource:
    return YahooGlobalSource(RateLimiter())


def _make_session_mock(crumb: str = "test-crumb-xyz") -> MagicMock:
    """Build a session.get mock that handles the three Yahoo endpoints."""
    def side_effect(url: str, **kwargs):  # type: ignore[override]
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.status_code = 200
        if "getcrumb" in url:
            resp.text = crumb
        elif "quoteSummary" in url:
            resp.json.return_value = {
                "quoteSummary": {"result": [{"financialData": {}}]}
            }
            resp.text = ""
        else:
            resp.text = ""
        return resp
    return MagicMock(side_effect=side_effect)


# TC-006-09: crumb is cached; second call does not make additional HTTP requests
def test_refresh_crumb_caches_within_ttl(src: YahooGlobalSource) -> None:
    mock_get = _make_session_mock("cached-crumb")
    with patch.object(src._session, "get", mock_get):
        crumb1 = src._refresh_crumb()
        call_count_after_first = mock_get.call_count
        crumb2 = src._refresh_crumb()
        call_count_after_second = mock_get.call_count

    assert crumb1 == "cached-crumb"
    assert crumb2 == "cached-crumb"
    # Second call must not invoke session.get again
    assert call_count_after_second == call_count_after_first, (
        "crumb should be served from cache on second call within TTL"
    )
    assert src._crumb_refreshed_at is not None


# TC-006-09 supplement: expired crumb triggers a fresh HTTP fetch
def test_refresh_crumb_refetches_after_expiry(src: YahooGlobalSource) -> None:
    mock_get = _make_session_mock("fresh-crumb")
    # Force expiry by setting refreshed_at 25h in the past
    src._crumb = "stale-crumb"
    from zoneinfo import ZoneInfo
    stale = dt.datetime.now(tz=ZoneInfo("UTC")) - dt.timedelta(hours=25)
    src._crumb_refreshed_at = stale

    with patch.object(src._session, "get", mock_get):
        crumb = src._refresh_crumb()

    assert crumb == "fresh-crumb"
    assert mock_get.call_count >= 1


# TC-006-10: fetch_quote_summary calls the quoteSummary REST endpoint with crumb
def test_fetch_quote_summary_uses_crumb_endpoint(src: YahooGlobalSource) -> None:
    mock_get = _make_session_mock("test-crumb-xyz")
    with patch.object(src._session, "get", mock_get):
        result = src.fetch_quote_summary("MSFT")

    assert result == {"financialData": {}}

    # Find the quoteSummary call and verify crumb param
    qs_calls = [
        c for c in mock_get.call_args_list
        if "quoteSummary" in str(c.args[0] if c.args else "")
    ]
    assert qs_calls, "expected a call to the quoteSummary endpoint"
    call_kwargs = qs_calls[0].kwargs
    params = call_kwargs.get("params", {})
    assert params.get("crumb") == "test-crumb-xyz"
    assert "MSFT" in str(qs_calls[0].args[0] if qs_calls[0].args else "")


# TC-006-10 supplement: 401 triggers crumb refresh and retry
def test_fetch_quote_summary_retries_on_401(src: YahooGlobalSource) -> None:
    call_count: list[int] = [0]

    def side_effect(url: str, **kwargs):  # type: ignore[override]
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        if "getcrumb" in url:
            resp.status_code = 200
            resp.text = f"crumb-{call_count[0]}"
            call_count[0] += 1
        elif "quoteSummary" in url:
            if call_count[0] <= 1:
                # First quoteSummary attempt: return 401
                resp.status_code = 401
            else:
                resp.status_code = 200
                resp.json.return_value = {"quoteSummary": {"result": [{"ok": True}]}}
                resp.text = ""
        else:
            resp.status_code = 200
            resp.text = ""
        return resp

    with patch.object(src._session, "get", side_effect=side_effect):
        result = src.fetch_quote_summary("MSFT")

    assert result.get("ok") is True
