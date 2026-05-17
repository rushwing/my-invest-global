"""TC-008-01..07 — UpdateClass, IndicatorGroups, MacroScheduler, ReleaseCalendar."""

from __future__ import annotations

import datetime as dt
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from engine.macro_agent.storage import MacroStorage

_sched_mod = pytest.importorskip(
    "engine.macro_agent.scheduler",
    reason="MacroScheduler not yet implemented (pending req_impl)",
)
_groups_mod = pytest.importorskip(
    "engine.macro_agent.indicator_groups",
    reason="indicator_groups not yet implemented (pending req_impl)",
)
_cal_mod = pytest.importorskip(
    "engine.macro_agent.release_calendar",
    reason="ReleaseCalendar not yet implemented (pending req_impl)",
)

MacroScheduler = _sched_mod.MacroScheduler
ReleaseCalendar = _cal_mod.ReleaseCalendar
INDICATOR_CONFIGS = _groups_mod.INDICATOR_CONFIGS
UpdateClass = _groups_mod.UpdateClass
IndicatorGroup = _groups_mod.IndicatorGroup

# ── Helpers ───────────────────────────────────────────────────────────────────

_ET = ZoneInfo("America/New_York")
_KST = ZoneInfo("Asia/Seoul")


@pytest.fixture
def mem_store():
    s = MacroStorage(":memory:")
    yield s
    s.close()


@pytest.fixture
def mock_calendar():
    cal = MagicMock(spec=ReleaseCalendar)
    cal.is_release_day.return_value = False
    return cal


@pytest.fixture
def scheduler(mem_store, mock_calendar):
    return MacroScheduler(storage=mem_store, release_calendar=mock_calendar)


@pytest.fixture
def real_calendar(mem_store):
    return ReleaseCalendar(storage=mem_store)


# ── TC-008-01 ─────────────────────────────────────────────────────────────────


class TestIntradayFastOutsideNYSE:
    """TC-008-01: INTRADAY_FAST not returned at 01:00 ET (NYSE closed)."""

    def test_nvda_not_due_at_0100_et(self, scheduler):
        t_0100 = dt.datetime(2026, 5, 15, 1, 0, tzinfo=_ET)
        due = scheduler.get_due_indicators(now=t_0100)
        ids = [c.indicator_id for c in due]
        assert "NVDA" not in ids

    def test_no_intraday_fast_returned_outside_nyse(self, scheduler):
        t_0100 = dt.datetime(2026, 5, 15, 1, 0, tzinfo=_ET)
        due = scheduler.get_due_indicators(now=t_0100)
        for cfg in due:
            if cfg.update_class == UpdateClass.INTRADAY_FAST:
                tz = ZoneInfo(cfg.market_tz)
                now_local = t_0100.astimezone(tz)
                if cfg.session_hours:
                    open_t, close_t = cfg.session_hours
                    in_session = open_t <= now_local.time() < close_t
                    assert not in_session, (
                        f"{cfg.indicator_id} INTRADAY_FAST returned outside session"
                    )


# ── TC-008-02 ─────────────────────────────────────────────────────────────────


class TestIntradayFastInsideNYSE:
    """TC-008-02: NVDA is returned at 10:00 ET when poll_interval_s elapsed."""

    def test_nvda_due_at_1000_et(self, scheduler, mem_store):
        t_1000 = dt.datetime(2026, 5, 15, 10, 0, tzinfo=_ET)
        # No prior fetch record → NVDA is due
        due = scheduler.get_due_indicators(now=t_1000)
        ids = [c.indicator_id for c in due]
        assert "NVDA" in ids

    def test_nvda_config_update_class(self, scheduler, mem_store):
        t_1000 = dt.datetime(2026, 5, 15, 10, 0, tzinfo=_ET)
        due = scheduler.get_due_indicators(now=t_1000)
        nvda = next((c for c in due if c.indicator_id == "NVDA"), None)
        assert nvda is not None
        assert nvda.update_class == UpdateClass.INTRADAY_FAST

    def test_nvda_not_due_again_before_poll_interval(self, scheduler, mem_store):
        t_1000 = dt.datetime(2026, 5, 15, 10, 0, tzinfo=_ET)
        # Simulate recent fetch: write a record with fetched_at just 10s ago
        now_utc = t_1000.astimezone(ZoneInfo("UTC"))
        recent_fetch = now_utc - dt.timedelta(seconds=10)
        mem_store.upsert_indicators([{
            "indicator_id": "NVDA",
            "group_code": "K",
            "period_date": t_1000.date(),
            "market_tz": "America/New_York",
            "value": 900.0,
            "value_unit": "USD",
            "value_raw": "900.0",
            "source": "yahoo_global",
            "realtime_start": None,
            "vintage_as_of": t_1000.date(),
            "utc_ts": recent_fetch,
            "fetched_at": recent_fetch,
        }])
        due = scheduler.get_due_indicators(now=t_1000)
        ids = [c.indicator_id for c in due]
        assert "NVDA" not in ids


# ── TC-008-03 ─────────────────────────────────────────────────────────────────


class TestMonthlyFixedReleaseDay:
    """TC-008-03: MONTHLY_FIXED triggers on release day, not on others."""

    def test_is_release_day_true_on_bls_date(self, real_calendar, mem_store):
        # Seed release_dates
        mem_store._conn.execute(
            "INSERT OR IGNORE INTO release_dates (indicator_id, release_date, source) "
            "VALUES ('CPIAUCSL', '2026-05-13', 'BLS')"
        )
        assert real_calendar.is_release_day("CPIAUCSL", dt.date(2026, 5, 13)) is True

    def test_is_release_day_false_on_non_release_date(self, real_calendar, mem_store):
        mem_store._conn.execute(
            "INSERT OR IGNORE INTO release_dates (indicator_id, release_date, source) "
            "VALUES ('CPIAUCSL', '2026-05-13', 'BLS')"
        )
        assert real_calendar.is_release_day("CPIAUCSL", dt.date(2026, 5, 14)) is False

    def test_cpiaucsl_due_on_release_day(self, mem_store):
        real_cal = ReleaseCalendar(storage=mem_store)
        mem_store._conn.execute(
            "INSERT OR IGNORE INTO release_dates (indicator_id, release_date, source) "
            "VALUES ('CPIAUCSL', '2026-05-13', 'BLS')"
        )
        sched = MacroScheduler(storage=mem_store, release_calendar=real_cal)
        release_day = dt.datetime(2026, 5, 13, 9, 0, tzinfo=_ET)
        due = sched.get_due_indicators(now=release_day)
        ids = [c.indicator_id for c in due]
        assert "CPIAUCSL" in ids

    def test_cpiaucsl_not_due_on_non_release_day(self, mem_store):
        real_cal = ReleaseCalendar(storage=mem_store)
        mem_store._conn.execute(
            "INSERT OR IGNORE INTO release_dates (indicator_id, release_date, source) "
            "VALUES ('CPIAUCSL', '2026-05-13', 'BLS')"
        )
        sched = MacroScheduler(storage=mem_store, release_calendar=real_cal)
        non_release = dt.datetime(2026, 5, 14, 9, 0, tzinfo=_ET)
        due = sched.get_due_indicators(now=non_release)
        monthly = [
            c for c in due
            if c.indicator_id == "CPIAUCSL" and c.update_class == UpdateClass.MONTHLY_FIXED
        ]
        assert len(monthly) == 0


# ── TC-008-04 ─────────────────────────────────────────────────────────────────


class TestDailyKRXAfterClose:
    """TC-008-04: Samsung DAILY indicator is due after KRX closes at 16:00 KST."""

    def test_samsung_due_after_krx_close(self, scheduler):
        t_1600_kst = dt.datetime(2026, 5, 15, 16, 0, tzinfo=_KST)
        due = scheduler.get_due_indicators(now=t_1600_kst)
        ids = [c.indicator_id for c in due]
        assert "005930.KS" in ids

    def test_samsung_not_due_after_same_day_fetch(self, scheduler, mem_store):
        t_1600_kst = dt.datetime(2026, 5, 15, 16, 0, tzinfo=_KST)
        utc_now = t_1600_kst.astimezone(ZoneInfo("UTC"))
        # Simulate same-day fetch
        mem_store.upsert_indicators([{
            "indicator_id": "005930.KS",
            "group_code": "M",
            "period_date": dt.date(2026, 5, 15),
            "market_tz": "Asia/Seoul",
            "value": 75000.0,
            "value_unit": "KRW",
            "value_raw": "75000",
            "source": "yahoo_global",
            "realtime_start": None,
            "vintage_as_of": dt.date(2026, 5, 15),
            "utc_ts": utc_now,
            "fetched_at": utc_now,
        }])
        due = scheduler.get_due_indicators(now=t_1600_kst)
        ids = [c.indicator_id for c in due]
        assert "005930.KS" not in ids


# ── TC-008-05 ─────────────────────────────────────────────────────────────────


class TestPopulateBLSFailureSafety:
    """TC-008-05: HTTP failure during BLS calendar parse is safe-degraded."""

    def test_populate_bls_does_not_raise_on_http_500(self, real_calendar, mem_store):
        with patch("engine.macro_agent.release_calendar.httpx") as mock_httpx:
            mock_resp = MagicMock()
            mock_resp.status_code = 500
            mock_resp.raise_for_status.side_effect = Exception("500 Server Error")
            mock_httpx.get.return_value = mock_resp
            real_calendar.populate_bls(2026)  # must not raise

    def test_existing_release_dates_preserved_after_failure(self, real_calendar, mem_store):
        mem_store._conn.execute(
            "INSERT OR IGNORE INTO release_dates (indicator_id, release_date, source) "
            "VALUES ('CPIAUCSL', '2026-05-13', 'BLS')"
        )
        with patch("engine.macro_agent.release_calendar.httpx") as mock_httpx:
            mock_httpx.get.side_effect = Exception("network error")
            real_calendar.populate_bls(2026)

        rows = mem_store._conn.execute(
            "SELECT COUNT(*) FROM release_dates WHERE indicator_id = 'CPIAUCSL'"
        ).fetchone()
        assert rows[0] >= 1, "existing release_dates must not be deleted on HTTP failure"


# ── TC-008-06 ─────────────────────────────────────────────────────────────────


class TestIndicatorConfigsCompleteness:
    """TC-008-06: INDICATOR_CONFIGS covers ADR-007 Groups I–O."""

    # Representative sample: at least one indicator per group with expected UpdateClass
    _EXPECTED: list[tuple[str, str, str]] = [
        # (indicator_id, group_value, update_class_value)
        ("CPIAUCSL",   "I", UpdateClass.MONTHLY_FIXED.value),
        ("PPIACO",     "I", UpdateClass.MONTHLY_FIXED.value),
        ("BZ=F",       "J", UpdateClass.INTRADAY_SLOW.value),
        ("CL=F",       "J", UpdateClass.INTRADAY_SLOW.value),
        ("^SOX",       "K", UpdateClass.INTRADAY_SLOW.value),
        ("DGS10",      "K", UpdateClass.DAILY.value),
        ("DGS2",       "K", UpdateClass.DAILY.value),
        ("NVDA",       "K", UpdateClass.INTRADAY_FAST.value),
        ("005930.KS",  "M", UpdateClass.DAILY.value),
        ("SGX_A50",    "N", UpdateClass.INTRADAY_FAST.value),
        ("CLS_NEWS",   "O", UpdateClass.INTRADAY_SLOW.value),
        ("AV_SENTIMENT", "O", UpdateClass.INTRADAY_SLOW.value),
    ]

    def test_all_expected_indicators_present(self):
        missing = [iid for iid, _, _ in self._EXPECTED if iid not in INDICATOR_CONFIGS]
        assert not missing, f"missing from INDICATOR_CONFIGS: {missing}"

    def test_update_class_matches_adr007(self):
        mismatches = []
        for iid, _group, expected_uc in self._EXPECTED:
            if iid not in INDICATOR_CONFIGS:
                continue
            actual = INDICATOR_CONFIGS[iid].update_class
            if hasattr(actual, "value"):
                actual = actual.value
            if actual != expected_uc:
                mismatches.append((iid, expected_uc, actual))
        assert not mismatches, f"UpdateClass mismatches: {mismatches}"

    def test_intraday_fast_poll_interval_in_range(self):
        for iid, cfg in INDICATOR_CONFIGS.items():
            uc = cfg.update_class
            if hasattr(uc, "value"):
                uc = uc.value
            if uc == UpdateClass.INTRADAY_FAST.value:
                assert 60 <= cfg.poll_interval_s <= 300, (
                    f"{iid} INTRADAY_FAST poll_interval_s={cfg.poll_interval_s} out of range"
                )

    def test_intraday_slow_poll_interval_in_range(self):
        for iid, cfg in INDICATOR_CONFIGS.items():
            uc = cfg.update_class
            if hasattr(uc, "value"):
                uc = uc.value
            if uc == UpdateClass.INTRADAY_SLOW.value:
                assert 900 <= cfg.poll_interval_s <= 3600, (
                    f"{iid} INTRADAY_SLOW poll_interval_s={cfg.poll_interval_s} out of range"
                )

    def test_all_configs_have_primary_source(self):
        for iid, cfg in INDICATOR_CONFIGS.items():
            assert cfg.primary_source, f"{iid} has empty primary_source"

    def test_all_configs_have_market_tz(self):
        for iid, cfg in INDICATOR_CONFIGS.items():
            assert cfg.market_tz, f"{iid} has empty market_tz"


# ── TC-008-07 ─────────────────────────────────────────────────────────────────


class TestMonthlyFixedCalendarMissingFallback:
    """TC-008-07: MONTHLY_FIXED falls back to once-per-day when no calendar rows."""

    def test_cpiaucsl_due_first_call_without_calendar(self, mem_store, mock_calendar):
        mock_calendar.is_release_day.return_value = False
        sched = MacroScheduler(storage=mem_store, release_calendar=mock_calendar)
        t_0900 = dt.datetime(2026, 5, 15, 9, 0, tzinfo=_ET)
        due = sched.get_due_indicators(now=t_0900)
        ids = [c.indicator_id for c in due]
        assert "CPIAUCSL" in ids

    def test_cpiaucsl_not_due_after_same_day_fetch_no_calendar(
        self, mem_store, mock_calendar
    ):
        mock_calendar.is_release_day.return_value = False
        sched = MacroScheduler(storage=mem_store, release_calendar=mock_calendar)
        t_0900 = dt.datetime(2026, 5, 15, 9, 0, tzinfo=_ET)
        utc_now = t_0900.astimezone(ZoneInfo("UTC"))
        # Simulate today's successful fetch
        mem_store.upsert_indicators([{
            "indicator_id": "CPIAUCSL",
            "group_code": "I",
            "period_date": dt.date(2026, 4, 1),
            "market_tz": "America/New_York",
            "value": 3.2,
            "value_unit": "percent",
            "value_raw": "3.2",
            "source": "fred",
            "realtime_start": None,
            "vintage_as_of": dt.date(2026, 5, 15),
            "utc_ts": utc_now,
            "fetched_at": utc_now,
        }])
        due = sched.get_due_indicators(now=t_0900)
        monthly = [
            c for c in due
            if c.indicator_id == "CPIAUCSL" and c.update_class == UpdateClass.MONTHLY_FIXED
        ]
        assert len(monthly) == 0, "CPIAUCSL must not be triggered twice on same day"
