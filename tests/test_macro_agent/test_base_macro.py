"""
Tests for MacroAbstractSource schema contract — covers TC-006-13.
"""

from __future__ import annotations

import datetime as dt

import pytest

from engine.data_agent.rate_limiter import RateLimiter
from engine.shared.sources.akshare_macro import AKShareMacroSource

_REQUIRED_KEYS = frozenset({
    "indicator_id",
    "group_code",
    "period_date",
    "market_tz",
    "value",
    "value_unit",
    "value_raw",
    "source",
    "realtime_start",
    "vintage_as_of",
    "utc_ts",
    "fetched_at",
})


@pytest.fixture()
def src() -> AKShareMacroSource:
    return AKShareMacroSource(RateLimiter())


# TC-006-13: _make_period_record() returns all required macro_indicators columns
def test_make_period_record_has_required_schema(src: AKShareMacroSource) -> None:
    rec = src._make_period_record(
        indicator_id="TEST",
        group_code="I",
        period_date=dt.date.today(),
        market_tz="UTC",
        value=1.0,
    )
    missing = _REQUIRED_KEYS - rec.keys()
    assert not missing, f"_make_period_record() missing keys: {missing}"


# Supplement: realtime_start defaults to None, vintage_as_of defaults to today
def test_make_period_record_defaults(src: AKShareMacroSource) -> None:
    rec = src._make_period_record(
        indicator_id="X",
        group_code="",
        period_date=dt.date(2026, 1, 1),
        market_tz="UTC",
        value=0.0,
    )
    assert rec["realtime_start"] is None
    assert rec["vintage_as_of"] == dt.date.today()
    assert rec["source"] == "akshare_macro"


# Supplement: explicit realtime_start is preserved
def test_make_period_record_preserves_realtime_start(src: AKShareMacroSource) -> None:
    rt = dt.date(2026, 3, 1)
    rec = src._make_period_record(
        indicator_id="X",
        group_code="",
        period_date=dt.date(2026, 4, 1),
        market_tz="UTC",
        value=1.5,
        realtime_start=rt,
    )
    assert rec["realtime_start"] == rt
