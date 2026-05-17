"""MacroScheduler — timezone-aware indicator scheduling.

Determines which indicators are due for collection at a given moment,
respecting market session windows, poll intervals, and release calendars.
"""

from __future__ import annotations

import datetime as dt
import logging
from zoneinfo import ZoneInfo

from engine.macro_agent.indicator_groups import INDICATOR_CONFIGS, IndicatorConfig
from engine.macro_agent.release_calendar import ReleaseCalendar
from engine.macro_agent.storage import MacroStorage
from engine.macro_agent.update_class import UpdateClass

log = logging.getLogger(__name__)

_UTC = ZoneInfo("UTC")


class MacroScheduler:
    """Returns indicators that are due for collection at the requested time."""

    def __init__(
        self,
        storage: MacroStorage,
        release_calendar: ReleaseCalendar,
    ) -> None:
        self._storage  = storage
        self._calendar = release_calendar

    def get_due_indicators(
        self,
        now: dt.datetime | None = None,
        groups_filter: list[str] | None = None,
    ) -> list[IndicatorConfig]:
        """Return indicators that should be fetched right now.

        Args:
            now:           Current time (UTC-aware). Defaults to wall clock.
            groups_filter: If set, restrict to indicators whose group.value is in this list.

        Returns:
            List of IndicatorConfig objects that are due.
        """
        if now is None:
            now = dt.datetime.now(tz=_UTC)
        elif now.tzinfo is None:
            now = now.replace(tzinfo=_UTC)

        due: list[IndicatorConfig] = []
        for cfg in INDICATOR_CONFIGS.values():
            if groups_filter and cfg.group_code not in groups_filter:
                continue
            if self._is_due(cfg, now):
                due.append(cfg)
        return due

    # ── Private ───────────────────────────────────────────────────────────────

    def _is_due(self, cfg: IndicatorConfig, now: dt.datetime) -> bool:
        uc = cfg.update_class
        if uc in (UpdateClass.STATIC_YAML, UpdateClass.EVENT_DRIVEN,
                  UpdateClass.QUARTERLY, UpdateClass.WEEKLY):
            return False

        if uc in (UpdateClass.INTRADAY_FAST, UpdateClass.INTRADAY_SLOW):
            return self._due_intraday(cfg, now)

        if uc == UpdateClass.DAILY:
            return self._due_daily(cfg, now)

        if uc == UpdateClass.MONTHLY_FIXED:
            return self._due_monthly_fixed(cfg, now)

        return False

    def _in_session(self, cfg: IndicatorConfig, now: dt.datetime) -> bool:
        """Return True if now is within the indicator's market session."""
        if cfg.session_hours is None:
            return True  # FX/futures: 24-hour
        tz = ZoneInfo(cfg.market_tz)
        local = now.astimezone(tz)
        open_t, close_t = cfg.session_hours
        return open_t <= local.time() < close_t

    def _last_fetched_at(self, indicator_id: str) -> dt.datetime | None:
        row = self._storage.get_latest_indicator(indicator_id)
        if row is None:
            return None
        fa = row.get("fetched_at")
        if fa is None:
            return None
        if isinstance(fa, dt.datetime):
            return fa if fa.tzinfo else fa.replace(tzinfo=_UTC)
        return None

    def _due_intraday(self, cfg: IndicatorConfig, now: dt.datetime) -> bool:
        if not self._in_session(cfg, now):
            return False
        last = self._last_fetched_at(cfg.indicator_id)
        if last is None:
            return True
        elapsed = (now - last.astimezone(_UTC)).total_seconds()
        return elapsed >= cfg.poll_interval_s

    def _due_daily(self, cfg: IndicatorConfig, now: dt.datetime) -> bool:
        tz = ZoneInfo(cfg.market_tz)
        local = now.astimezone(tz)
        close_t = cfg.session_hours[1] if cfg.session_hours else dt.time(16, 0)
        if local.time() < close_t:
            return False  # market not yet closed today
        today_local = local.date()
        last = self._last_fetched_at(cfg.indicator_id)
        if last is None:
            return True
        last_local = last.astimezone(tz).date()
        return last_local < today_local

    def _due_monthly_fixed(self, cfg: IndicatorConfig, now: dt.datetime) -> bool:
        today = now.astimezone(ZoneInfo(cfg.market_tz)).date()
        has_calendar = self._calendar.has_any_dates(cfg.indicator_id)

        if has_calendar:
            if not self._calendar.is_release_day(cfg.indicator_id, today):
                return False

        # Daily fallback (or release day): check if we already fetched today
        last = self._last_fetched_at(cfg.indicator_id)
        if last is None:
            return True
        last_date = last.astimezone(ZoneInfo(cfg.market_tz)).date()
        return last_date < today
