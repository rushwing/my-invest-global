"""
Per-FieldGroup retrieval schedules with A-share trading calendar awareness.

Each FieldGroup has a schedule that specifies:
  - Whether fetching is restricted to trading hours (during_trading)
  - A base polling interval in seconds
  - Dense windows (shorter intervals at market-sensitive moments)
  - Fixed daily timestamps for post-close or early-morning runs
  - Earnings-season overrides (Jan/Apr/Jul/Oct) for quarterly data

Trade calendar:
  The scheduler lazily loads the A-share holiday calendar via AKShare
  (ak.tool_trade_date_hist_sina) and caches it for the current process.
  Falls back to a simple weekday check if AKShare is unavailable.
"""

from __future__ import annotations

import datetime as dt
from typing import NamedTuple

from engine.data_agent.fields import FieldGroup


# ── Trading windows (China A-share, UTC+8) ───────────────────────────────────

class _Window(NamedTuple):
    start: dt.time
    end: dt.time


TRADING_WINDOWS: dict[str, _Window] = {
    "morning_open":    _Window(dt.time(9, 30),  dt.time(9, 40)),
    "morning_mid":     _Window(dt.time(11, 0),  dt.time(11, 30)),
    "afternoon_open":  _Window(dt.time(13, 0),  dt.time(13, 10)),
    "afternoon_close": _Window(dt.time(14, 30), dt.time(15, 0)),
    "post_close":      _Window(dt.time(15, 5),  dt.time(15, 15)),
}

TRADING_HOURS = (dt.time(9, 30), dt.time(15, 0))
LUNCH_BREAK   = (dt.time(11, 30), dt.time(13, 0))

# Earnings-season months: quarterly reports flood in during these months
EARNINGS_MONTHS = frozenset({1, 4, 7, 10})


# ── Per-FieldGroup schedule config ────────────────────────────────────────────

_ScheduleConfig = dict  # typed for readability

FIELD_SCHEDULES: dict[FieldGroup, _ScheduleConfig] = {
    FieldGroup.QUOTE: {
        "during_trading": True,
        "interval_s": 90,
        "dense_windows": ["morning_open", "afternoon_open"],
        "dense_interval_s": 30,
    },
    FieldGroup.KLINE: {
        "during_trading": False,
        "fixed_times": [dt.time(15, 5), dt.time(17, 30)],
    },
    FieldGroup.KLINE_MIN: {
        "during_trading": True,
        "interval_s": 60,
    },
    FieldGroup.FUNDAMENTAL: {
        "during_trading": False,
        "fixed_times": [dt.time(17, 30)],
        "earnings_months": EARNINGS_MONTHS,
        "normal_interval_days": 7,
    },
    FieldGroup.SEGMENT: {
        "during_trading": False,
        "fixed_times": [dt.time(18, 0)],
        "earnings_months": EARNINGS_MONTHS,
        "normal_interval_days": 30,
    },
    FieldGroup.FUND_FLOW: {
        "during_trading": True,
        "interval_s": 600,
        "dense_windows": ["morning_mid", "afternoon_close"],
        "dense_interval_s": 300,
        "fixed_times": [dt.time(17, 30)],
    },
    FieldGroup.SHAREHOLDER: {
        "during_trading": False,
        "fixed_times": [dt.time(20, 0)],
        "earnings_months": EARNINGS_MONTHS,
        "normal_interval_days": 30,
    },
    FieldGroup.ANNOUNCEMENT: {
        "during_trading": False,
        "fixed_times": [dt.time(8, 30), dt.time(12, 30), dt.time(16, 0), dt.time(21, 0)],
    },
    FieldGroup.INDEX: {
        "during_trading": True,
        "interval_s": 120,
        "dense_windows": ["morning_open", "afternoon_close"],
        "dense_interval_s": 30,
    },
}


# ── Trade calendar ────────────────────────────────────────────────────────────

class _TradeCalendar:
    """Lazy-loaded A-share trade date cache."""

    def __init__(self) -> None:
        self._trade_dates: set[dt.date] = set()
        self._loaded_year: int = 0

    def is_trading_day(self, d: dt.date) -> bool:
        if d.weekday() >= 5:  # fast path: weekend
            return False
        self._ensure_loaded(d.year)
        if self._trade_dates:
            return d in self._trade_dates
        # Fallback: weekdays only (ignores holidays)
        return True

    def _ensure_loaded(self, year: int) -> None:
        if self._loaded_year == year:
            return
        try:
            import akshare as ak  # optional dep
            df = ak.tool_trade_date_hist_sina()
            self._trade_dates = {
                dt.date.fromisoformat(str(d)[:10])
                for d in df["trade_date"]
            }
            self._loaded_year = year
        except Exception:
            # AKShare unavailable or network error — fall back to weekday logic
            self._trade_dates = set()
            self._loaded_year = year


_calendar = _TradeCalendar()


# ── Scheduler ────────────────────────────────────────────────────────────────

class Schedule:
    """
    Determines which FieldGroups are due to fetch given current time.

    All times are in China Standard Time (UTC+8) regardless of the machine timezone.
    """

    CST = dt.timezone(dt.timedelta(hours=8))

    def now_cst(self) -> dt.datetime:
        return dt.datetime.now(tz=self.CST)

    def is_trading_day(self, d: dt.date | None = None) -> bool:
        return _calendar.is_trading_day(d or self.now_cst().date())

    def is_trading_hours(self, t: dt.time | None = None) -> bool:
        """Return True if current CST time is within trading hours (excl. lunch)."""
        t = t or self.now_cst().time()
        if not (TRADING_HOURS[0] <= t <= TRADING_HOURS[1]):
            return False
        if LUNCH_BREAK[0] <= t <= LUNCH_BREAK[1]:
            return False
        return True

    def in_dense_window(self, window_names: list[str], t: dt.time | None = None) -> bool:
        t = t or self.now_cst().time()
        for name in window_names:
            w = TRADING_WINDOWS.get(name)
            if w and w.start <= t <= w.end:
                return True
        return False

    def get_due_groups(
        self,
        last_fetched: dict[FieldGroup, dt.datetime | None],
    ) -> list[FieldGroup]:
        """
        Return the list of FieldGroups that should be fetched right now.

        last_fetched: maps each FieldGroup to the datetime of its last successful
        fetch (None if never fetched).
        """
        now_cst = self.now_cst()
        today = now_cst.date()
        is_td = self.is_trading_day(today)
        is_th = self.is_trading_hours(now_cst.time()) if is_td else False

        due: list[FieldGroup] = []
        for group, cfg in FIELD_SCHEDULES.items():
            if cfg.get("during_trading") and not is_th:
                continue  # skip intraday groups when market is closed
            if self._is_due(group, cfg, now_cst, last_fetched.get(group), is_td, is_th):
                due.append(group)
        return due

    def _is_due(
        self,
        group: FieldGroup,
        cfg: _ScheduleConfig,
        now: dt.datetime,
        last: dt.datetime | None,
        is_trading_day: bool,
        is_trading_hours: bool,
    ) -> bool:
        t = now.time()

        # Fixed-time groups: due if current time is within 5 min past a fixed time
        # and we haven't already fetched since that time today.
        if "fixed_times" in cfg:
            for fixed_t in cfg["fixed_times"]:
                window_start = dt.datetime.combine(now.date(), fixed_t, tzinfo=self.CST)
                window_end   = window_start + dt.timedelta(minutes=5)
                if window_start <= now <= window_end:
                    if last is None or last < window_start:
                        return True
            return False

        # Interval-based groups
        interval = cfg["interval_s"]
        dense_windows: list[str] = cfg.get("dense_windows", [])
        if dense_windows and self.in_dense_window(dense_windows, t):
            interval = cfg.get("dense_interval_s", interval)

        if last is None:
            return True
        elapsed = (now - last).total_seconds()
        return elapsed >= interval
