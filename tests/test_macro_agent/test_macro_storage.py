"""TC-007-01..06 — MacroStorage DuckDB schema and upsert behaviour."""

from datetime import UTC, date, datetime

import pytest

from engine.macro_agent.storage import MacroStorage


@pytest.fixture
def store():
    s = MacroStorage(":memory:")
    yield s
    s.close()


# ── TC-007-01 ────────────────────────────────────────────────────────────────


class TestRoundTripUpsert:
    """TC-007-01: macro_indicators ON CONFLICT DO UPDATE replaces existing row."""

    _base = {
        "indicator_id": "DGS10",
        "group_code": "K",
        "period_date": date(2026, 5, 15),
        "market_tz": "America/New_York",
        "value": 4.5,
        "value_unit": "percent",
        "value_raw": "4.5",
        "source": "fred",
        "realtime_start": None,
        "vintage_as_of": date(2026, 5, 16),
        "utc_ts": datetime(2026, 5, 16, 1, 0, tzinfo=UTC),
        "fetched_at": datetime(2026, 5, 16, 1, 0, tzinfo=UTC),
    }

    def test_upsert_returns_row_count(self, store):
        n = store.upsert_indicators([self._base])
        assert n == 1

    def test_conflict_updates_value(self, store):
        store.upsert_indicators([self._base])
        updated = {
            **self._base,
            "value": 4.6,
            "value_raw": "4.6",
            "fetched_at": datetime(2026, 5, 16, 2, 0, tzinfo=UTC),
        }
        n = store.upsert_indicators([updated])
        assert n == 1

        rows = store._conn.execute(
            "SELECT value, value_raw, fetched_at FROM macro_indicators WHERE indicator_id='DGS10'"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0][0] == pytest.approx(4.6)
        assert rows[0][1] == "4.6"
        assert rows[0][2] > datetime(2026, 5, 16, 1, 0, tzinfo=UTC)


# ── TC-007-02 ────────────────────────────────────────────────────────────────


class TestFredVintage:
    """TC-007-02: vintage fields persisted; get_latest_indicator returns fetched_at DESC."""

    _record_a = {
        "indicator_id": "CPIAUCSL",
        "group_code": "I",
        "period_date": date(2026, 3, 1),
        "market_tz": "America/New_York",
        "value": 3.4,
        "value_unit": "percent_yoy",
        "value_raw": "3.4",
        "source": "fred",
        "realtime_start": date(2026, 4, 1),
        "vintage_as_of": date(2026, 4, 11),
        "utc_ts": datetime(2026, 4, 11, 12, 0, tzinfo=UTC),
        "fetched_at": datetime(2026, 4, 11, 12, 0, tzinfo=UTC),
    }
    _record_b = {
        "indicator_id": "CPIAUCSL",
        "group_code": "I",
        "period_date": date(2026, 4, 1),
        "market_tz": "America/New_York",
        "value": 3.5,
        "value_unit": "percent_yoy",
        "value_raw": "3.5",
        "source": "fred",
        "realtime_start": date(2026, 5, 1),
        "vintage_as_of": date(2026, 5, 12),
        "utc_ts": datetime(2026, 5, 12, 12, 0, tzinfo=UTC),
        "fetched_at": datetime(2026, 5, 12, 12, 0, tzinfo=UTC),
    }

    def test_latest_indicator_returns_newest_fetched(self, store):
        store.upsert_indicators([self._record_a, self._record_b])
        latest = store.get_latest_indicator("CPIAUCSL")
        assert latest is not None
        assert latest["period_date"] == date(2026, 4, 1)
        assert latest["realtime_start"] == date(2026, 5, 1)
        assert latest["vintage_as_of"] == date(2026, 5, 12)
        assert latest["source"] == "fred"

    def test_source_filter_consistent(self, store):
        store.upsert_indicators([self._record_a, self._record_b])
        latest = store.get_latest_indicator("CPIAUCSL")
        latest_fred = store.get_latest_indicator("CPIAUCSL", source="fred")
        assert latest_fred is not None
        assert latest_fred["period_date"] == latest["period_date"]
        assert latest_fred["fetched_at"] == latest["fetched_at"]

    def test_unknown_indicator_returns_none(self, store):
        assert store.get_latest_indicator("DOES_NOT_EXIST") is None


# ── TC-007-03 ────────────────────────────────────────────────────────────────


class TestCapexQuarters:
    """TC-007-03: capex_quarterly persists values; get_capex_quarters returns period_end DESC."""

    _records = [
        {
            "company": "MSFT",
            "cik": "0000789019",
            "fiscal_quarter": "2025Q1",
            "period_end": date(2025, 3, 31),
            "capex_usd": 3.0e9,
            "capex_yoy_pct": None,
            "filing_form": "10-Q",
            "source": "sec_edgar",
            "source_hash": "aaa",
            "fetched_at": datetime(2026, 5, 1, 0, 0, tzinfo=UTC),
        },
        {
            "company": "MSFT",
            "cik": "0000789019",
            "fiscal_quarter": "2025Q2",
            "period_end": date(2025, 6, 30),
            "capex_usd": 4.0e9,
            "capex_yoy_pct": None,
            "filing_form": "10-Q",
            "source": "sec_edgar",
            "source_hash": "bbb",
            "fetched_at": datetime(2026, 5, 1, 0, 0, tzinfo=UTC),
        },
        {
            "company": "MSFT",
            "cik": "0000789019",
            "fiscal_quarter": "2025Q3",
            "period_end": date(2025, 9, 30),
            "capex_usd": 3.5e9,
            "capex_yoy_pct": None,
            "filing_form": "10-Q",
            "source": "sec_edgar",
            "source_hash": "ccc",
            "fetched_at": datetime(2026, 5, 1, 0, 0, tzinfo=UTC),
        },
        {
            "company": "MSFT",
            "cik": "0000789019",
            "fiscal_quarter": "2025Q4",
            "period_end": date(2025, 12, 31),
            "capex_usd": 3.5e9,
            "capex_yoy_pct": None,
            "filing_form": "10-K",
            "source": "sec_edgar",
            "source_hash": "ddd",
            "fetched_at": datetime(2026, 5, 1, 0, 0, tzinfo=UTC),
        },
    ]

    def test_upsert_returns_count(self, store):
        n = store.upsert_capex(self._records)
        assert n == 4

    def test_latest_quarter_first(self, store):
        store.upsert_capex(self._records)
        quarters = store.get_capex_quarters("MSFT", 4)
        assert len(quarters) == 4
        assert quarters[0]["fiscal_quarter"] == "2025Q4"
        assert quarters[0]["period_end"] == date(2025, 12, 31)
        assert quarters[0]["capex_usd"] == pytest.approx(3.5e9)

    def test_n_limits_results(self, store):
        store.upsert_capex(self._records)
        quarters = store.get_capex_quarters("MSFT", 2)
        assert len(quarters) == 2
        assert quarters[0]["fiscal_quarter"] == "2025Q4"
        assert quarters[1]["fiscal_quarter"] == "2025Q3"


# ── TC-007-04 ────────────────────────────────────────────────────────────────


class TestAvBudget:
    """TC-007-04: AV budget returns 0 when absent; increment accumulates correctly."""

    _date = date(2026, 5, 17)

    def test_initial_zero(self, store):
        assert store.get_av_budget(self._date) == 0

    def test_first_increment_gives_one(self, store):
        store.increment_av_budget(self._date)
        assert store.get_av_budget(self._date) == 1

    def test_accumulates_to_22(self, store):
        for _ in range(22):
            store.increment_av_budget(self._date)
        assert store.get_av_budget(self._date) == 22

    def test_single_row_per_date(self, store):
        for _ in range(5):
            store.increment_av_budget(self._date)
        row_count = store._conn.execute(
            "SELECT COUNT(*) FROM alpha_vantage_budget WHERE date = ?", [self._date]
        ).fetchone()[0]
        assert row_count == 1


# ── TC-007-05 ────────────────────────────────────────────────────────────────


class TestFomcUpcoming:
    """TC-007-05: get_fomc_upcoming returns closed interval [from_date, from_date+days] ASC."""

    _from_date = date(2026, 5, 17)
    _records = [
        {
            "meeting_date": date(2026, 5, 16),
            "meeting_type": "scheduled",
            "decision_date": None,
            "rate_decision": None,
            "target_lower": None,
            "target_upper": None,
            "source": "test",
            "updated_at": None,
        },
        {
            "meeting_date": date(2026, 5, 17),
            "meeting_type": "scheduled",
            "decision_date": None,
            "rate_decision": None,
            "target_lower": None,
            "target_upper": None,
            "source": "test",
            "updated_at": None,
        },
        {
            "meeting_date": date(2026, 7, 29),
            "meeting_type": "scheduled",
            "decision_date": None,
            "rate_decision": None,
            "target_lower": None,
            "target_upper": None,
            "source": "test",
            "updated_at": None,
        },
        {
            "meeting_date": date(2026, 8, 16),
            "meeting_type": "scheduled",
            "decision_date": None,
            "rate_decision": None,
            "target_lower": None,
            "target_upper": None,
            "source": "test",
            "updated_at": None,
        },
    ]

    def test_returns_only_window_meetings(self, store):
        store.upsert_fomc(self._records)
        items = store.get_fomc_upcoming(self._from_date, 90)
        assert len(items) == 2

    def test_from_date_included(self, store):
        store.upsert_fomc(self._records)
        items = store.get_fomc_upcoming(self._from_date, 90)
        assert items[0]["meeting_date"] == date(2026, 5, 17)

    def test_ascending_order(self, store):
        store.upsert_fomc(self._records)
        items = store.get_fomc_upcoming(self._from_date, 90)
        assert items[1]["meeting_date"] == date(2026, 7, 29)
        dates = [r["meeting_date"] for r in items]
        assert dates == sorted(dates)

    def test_boundary_excluded(self, store):
        store.upsert_fomc(self._records)
        items = store.get_fomc_upcoming(self._from_date, 90)
        meeting_dates = {r["meeting_date"] for r in items}
        assert date(2026, 5, 16) not in meeting_dates
        assert date(2026, 8, 16) not in meeting_dates


# ── TC-007-06 ────────────────────────────────────────────────────────────────


class TestRegimeRoundTrip:
    """TC-007-06: upsert_regime / get_regime_latest returns newest as_of_date with updates."""

    _older = {
        "as_of_date": date(2026, 5, 16),
        "capex_state": "yellow",
        "yield_curve_state": "flat",
        "risk_state": "neutral",
        "composite_state": "yellow",
        "capex_as_of": "2025-Q4",
        "yield_as_of": date(2026, 5, 15),
        "computed_at": datetime(2026, 5, 16, 8, 0, tzinfo=UTC),
    }
    _initial = {
        "as_of_date": date(2026, 5, 17),
        "capex_state": "green",
        "yield_curve_state": "normal",
        "risk_state": "risk_on",
        "composite_state": "green",
        "capex_as_of": "2026-Q1",
        "yield_as_of": date(2026, 5, 16),
        "computed_at": datetime(2026, 5, 17, 8, 0, tzinfo=UTC),
    }
    _updated = {
        **_initial,
        "risk_state": "neutral",
        "composite_state": "yellow",
        "computed_at": datetime(2026, 5, 17, 9, 0, tzinfo=UTC),
    }

    def test_latest_returns_newest_as_of_date(self, store):
        store.upsert_regime(self._older)
        store.upsert_regime(self._initial)
        store.upsert_regime(self._updated)
        latest = store.get_regime_latest()
        assert latest is not None
        assert latest["as_of_date"] == date(2026, 5, 17)

    def test_update_overwrites_fields(self, store):
        store.upsert_regime(self._older)
        store.upsert_regime(self._initial)
        store.upsert_regime(self._updated)
        latest = store.get_regime_latest()
        assert latest["capex_state"] == "green"
        assert latest["yield_curve_state"] == "normal"
        assert latest["risk_state"] == "neutral"
        assert latest["composite_state"] == "yellow"
        assert latest["capex_as_of"] == "2026-Q1"
        assert latest["yield_as_of"] == date(2026, 5, 16)

    def test_computed_at_updated(self, store):
        store.upsert_regime(self._initial)
        store.upsert_regime(self._updated)
        latest = store.get_regime_latest()
        assert latest["computed_at"] == datetime(2026, 5, 17, 9, 0, tzinfo=UTC)

    def test_none_when_empty(self, store):
        assert store.get_regime_latest() is None
