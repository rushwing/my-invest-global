"""
Tests for AKShareMacroSource — covers TC-006-14 and TC-006-15.
Requires pandas (transitive dep of akshare; skipped if not installed).
"""

from __future__ import annotations

import datetime as dt
from unittest.mock import patch

import pytest

from engine.data_agent.rate_limiter import RateLimiter
from engine.shared.sources.akshare_macro import AKShareMacroSource

pandas = pytest.importorskip("pandas")


@pytest.fixture()
def src() -> AKShareMacroSource:
    return AKShareMacroSource(RateLimiter())


# TC-006-14: _df_to_records returns records with full _make_period_record schema
def test_df_to_records_schema(src: AKShareMacroSource) -> None:
    df = pandas.DataFrame([{"日期": "2026-03-01", "今值": "2.1"}])
    records = src._df_to_records(
        df,
        indicator_id="CN_CPI",
        group_code="I",
        date_col="日期",
        value_col="今值",
        market_tz="Asia/Shanghai",
        value_unit="percent_yoy",
        start_date=None,
    )
    assert len(records) == 1
    rec = records[0]
    assert rec["indicator_id"] == "CN_CPI"
    assert rec["value"] == pytest.approx(2.1)
    # Must have _make_period_record fields
    for key in ("realtime_start", "vintage_as_of", "utc_ts", "fetched_at"):
        assert key in rec, f"missing key: {key}"


# TC-006-14 supplement: start_date filter applied correctly
def test_df_to_records_start_date_filter(src: AKShareMacroSource) -> None:
    df = pandas.DataFrame([
        {"日期": "2025-12-01", "今值": "1.5"},
        {"日期": "2026-03-01", "今值": "2.1"},
    ])
    records = src._df_to_records(
        df,
        indicator_id="CN_CPI",
        group_code="I",
        date_col="日期",
        value_col="今值",
        market_tz="Asia/Shanghai",
        value_unit="percent_yoy",
        start_date="2026-01-01",
    )
    assert len(records) == 1
    assert records[0]["period_date"] == dt.date(2026, 3, 1)


# TC-006-15: fetch_cls_news uses _make_period_record and has full schema
def test_fetch_cls_news_schema(src: AKShareMacroSource) -> None:
    df = pandas.DataFrame([{"title": "美联储降息", "content": "..."}])
    with patch.object(src, "_ak_call", return_value=df):
        records = src.fetch_cls_news(limit=1)

    assert len(records) == 1
    rec = records[0]
    assert rec["indicator_id"] == "CLS_NEWS"
    assert rec["value"] is None
    # These fields must come from _make_period_record (not hand-crafted)
    for key in ("value_unit", "vintage_as_of", "realtime_start", "utc_ts"):
        assert key in rec, f"fetch_cls_news missing key: {key}"
