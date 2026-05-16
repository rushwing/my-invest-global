"""Tests for engine.data_agent.scheduler — due-group logic and trading calendar."""

import datetime as dt
from unittest.mock import patch

from engine.data_agent.fields import FieldGroup
from engine.data_agent.scheduler import Schedule

CST = dt.timezone(dt.timedelta(hours=8))


def _cst(hour: int, minute: int, day: int = 15) -> dt.datetime:
    """Build a CST datetime on 2026-05-15 (a Friday)."""
    return dt.datetime(2026, 5, 15, hour, minute, tzinfo=CST)


class TestIsTradingHours:
    def setup_method(self):
        self.sched = Schedule()

    def test_market_open_is_trading(self):
        assert self.sched.is_trading_hours(dt.time(10, 0))

    def test_before_open_is_not_trading(self):
        assert not self.sched.is_trading_hours(dt.time(9, 0))

    def test_after_close_is_not_trading(self):
        assert not self.sched.is_trading_hours(dt.time(15, 30))

    def test_lunch_break_is_not_trading(self):
        assert not self.sched.is_trading_hours(dt.time(12, 0))

    def test_just_before_lunch_is_trading(self):
        assert self.sched.is_trading_hours(dt.time(11, 29))

    def test_just_after_lunch_is_trading(self):
        assert self.sched.is_trading_hours(dt.time(13, 1))


class TestInDenseWindow:
    def setup_method(self):
        self.sched = Schedule()

    def test_morning_open_window(self):
        assert self.sched.in_dense_window(["morning_open"], dt.time(9, 35))

    def test_outside_dense_window(self):
        assert not self.sched.in_dense_window(["morning_open"], dt.time(10, 0))

    def test_afternoon_close_window(self):
        assert self.sched.in_dense_window(["afternoon_close"], dt.time(14, 45))


class TestGetDueGroups:
    def setup_method(self):
        self.sched = Schedule()

    def _due(self, now_cst: dt.datetime, last_fetched=None) -> list[FieldGroup]:
        last = last_fetched or {g: None for g in FieldGroup}
        with (
            patch.object(self.sched, "now_cst", return_value=now_cst),
            patch.object(self.sched, "is_trading_day", return_value=True),
        ):
            return self.sched.get_due_groups(last)

    def test_all_groups_due_on_first_run(self):
        # During trading hours — all groups due (none ever fetched)
        now = _cst(10, 0)
        due = self._due(now)
        assert FieldGroup.QUOTE in due
        assert FieldGroup.INDEX in due

    def test_quote_not_due_before_interval(self):
        now = _cst(10, 0)
        # Quote fetched 30s ago — interval is 90s, shouldn't be due
        last = {g: None for g in FieldGroup}
        last[FieldGroup.QUOTE] = now - dt.timedelta(seconds=30)
        due = self._due(now, last)
        assert FieldGroup.QUOTE not in due

    def test_quote_due_after_interval(self):
        now = _cst(10, 0)
        last = {g: None for g in FieldGroup}
        last[FieldGroup.QUOTE] = now - dt.timedelta(seconds=100)
        due = self._due(now, last)
        assert FieldGroup.QUOTE in due

    def test_intraday_groups_skipped_when_market_closed(self):
        now = _cst(20, 0)  # after market close
        last = {g: None for g in FieldGroup}
        with (
            patch.object(self.sched, "now_cst", return_value=now),
            patch.object(self.sched, "is_trading_day", return_value=True),
        ):
            due = self.sched.get_due_groups(last)
        # QUOTE and INDEX require during_trading=True → not due
        assert FieldGroup.QUOTE not in due
        assert FieldGroup.INDEX not in due

    def test_fund_flow_post_close_fixed_time_fires(self):
        # FUND_FLOW has during_trading=True AND fixed_times=[17:30].
        # At 17:31 (post-market), the fixed-time window should still fire.
        now = _cst(17, 31)
        last = {g: None for g in FieldGroup}
        # Mark FUND_FLOW as last fetched before the 17:30 window
        last[FieldGroup.FUND_FLOW] = now - dt.timedelta(hours=3)
        with (
            patch.object(self.sched, "now_cst", return_value=now),
            patch.object(self.sched, "is_trading_day", return_value=True),
        ):
            due = self.sched.get_due_groups(last)
        assert FieldGroup.FUND_FLOW in due

    def test_fund_flow_post_close_not_due_if_already_fetched(self):
        now = _cst(17, 31)
        last = {g: None for g in FieldGroup}
        # Already fetched during the 17:30 window
        last[FieldGroup.FUND_FLOW] = now - dt.timedelta(seconds=30)
        with (
            patch.object(self.sched, "now_cst", return_value=now),
            patch.object(self.sched, "is_trading_day", return_value=True),
        ):
            due = self.sched.get_due_groups(last)
        assert FieldGroup.FUND_FLOW not in due

    def test_fixed_time_group_due_within_window(self):
        # KLINE fixed_times = [15:05, 17:30]
        now = _cst(15, 6)  # 1 minute past 15:05
        last = {g: None for g in FieldGroup}
        last[FieldGroup.KLINE] = now - dt.timedelta(hours=6)  # not recently fetched
        with (
            patch.object(self.sched, "now_cst", return_value=now),
            patch.object(self.sched, "is_trading_day", return_value=True),
        ):
            due = self.sched.get_due_groups(last)
        assert FieldGroup.KLINE in due

    def test_fixed_time_group_not_due_after_already_fetched(self):
        now = _cst(15, 6)
        last = {g: None for g in FieldGroup}
        # Already fetched during the 15:05 window
        last[FieldGroup.KLINE] = now - dt.timedelta(seconds=30)
        with (
            patch.object(self.sched, "now_cst", return_value=now),
            patch.object(self.sched, "is_trading_day", return_value=True),
        ):
            due = self.sched.get_due_groups(last)
        assert FieldGroup.KLINE not in due

    def test_dense_window_uses_shorter_interval(self):
        # During morning_open (9:30-9:40) QUOTE interval is 30s not 90s
        now = _cst(9, 35)
        last = {g: None for g in FieldGroup}
        last[FieldGroup.QUOTE] = now - dt.timedelta(seconds=35)
        with (
            patch.object(self.sched, "now_cst", return_value=now),
            patch.object(self.sched, "is_trading_day", return_value=True),
        ):
            due = self.sched.get_due_groups(last)
        # 35s elapsed > 30s dense_interval → should be due
        assert FieldGroup.QUOTE in due
