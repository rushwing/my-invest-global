"""FOMCCalendarSource — parse Fed ICS feed into fomc_calendar rows (BP-6).

Falls back to fomc_calendar.yaml on any HTTP or parse failure.
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any
from zoneinfo import ZoneInfo

from engine.data_agent.storage import _find_project_root
from engine.macro_agent.storage import MacroStorage

log = logging.getLogger(__name__)

_UTC = ZoneInfo("UTC")

# Official Fed FOMC ICS feed
_FOMC_ICS_URL = (
    "https://www.federalreserve.gov/apps/fomccalendar/fomccalendar.ics"
)

# Fallback static YAML relative to project root
_FOMC_YAML_REL = "data/fomc_calendar.yaml"


class FOMCCalendarSource:
    """Fetches and parses the Fed FOMC ICS calendar into DuckDB fomc_calendar rows."""

    name = "fomc_ical"

    def __init__(self, storage: MacroStorage) -> None:
        self._storage = storage

    def refresh(self) -> int:
        """Fetch the ICS feed and upsert into fomc_calendar; falls back to YAML.

        Returns:
            Number of rows upserted (0 if both sources failed).
        """
        records = self._fetch_ics() or self._load_yaml()
        if not records:
            log.warning("fomc_ical: no FOMC calendar data available from either source")
            return 0
        return self._storage.upsert_fomc(records)

    # ── Private ───────────────────────────────────────────────────────────────

    def _fetch_ics(self) -> list[dict[str, Any]] | None:
        try:
            import icalendar
        except ImportError:
            log.warning("icalendar not installed; skipping ICS fetch (pip install icalendar)")
            return None

        try:
            import httpx
            resp = httpx.get(_FOMC_ICS_URL, timeout=15, follow_redirects=True)
            resp.raise_for_status()
            raw = resp.content
        except Exception as exc:
            log.warning("fomc_ical: ICS fetch failed: %s", exc)
            return None

        try:
            cal = icalendar.Calendar.from_ical(raw)
            return self._parse_cal(cal)
        except Exception as exc:
            log.warning("fomc_ical: ICS parse failed: %s", exc)
            return None

    def _parse_cal(self, cal: Any) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        now_utc = dt.datetime.now(tz=_UTC)
        for component in cal.walk():
            if component.name != "VEVENT":
                continue
            dtstart = component.get("dtstart")
            if dtstart is None:
                continue
            meeting_date = self._to_date(dtstart.dt)
            if meeting_date is None:
                continue
            records.append({
                "meeting_date":   meeting_date,
                "meeting_type":   "regular",
                "decision_date":  None,
                "rate_decision":  None,
                "target_lower":   None,
                "target_upper":   None,
                "source":         self.name,
                "updated_at":     now_utc,
            })
        return records

    def _load_yaml(self) -> list[dict[str, Any]] | None:
        yaml_path = _find_project_root() / _FOMC_YAML_REL
        if not yaml_path.exists():
            log.warning("fomc_ical: fallback YAML not found at %s", yaml_path)
            return None
        try:
            import yaml
            data = yaml.safe_load(yaml_path.read_text())
            if not isinstance(data, list):
                return None
            now_utc = dt.datetime.now(tz=_UTC)
            records: list[dict[str, Any]] = []
            for row in data:
                meeting_date = row.get("meeting_date")
                if meeting_date is None:
                    continue
                if isinstance(meeting_date, str):
                    meeting_date = dt.date.fromisoformat(meeting_date)
                records.append({
                    "meeting_date":   meeting_date,
                    "meeting_type":   row.get("meeting_type", "regular"),
                    "decision_date":  row.get("decision_date"),
                    "rate_decision":  row.get("rate_decision"),
                    "target_lower":   row.get("target_lower"),
                    "target_upper":   row.get("target_upper"),
                    "source":         "yaml",
                    "updated_at":     now_utc,
                })
            return records
        except Exception as exc:
            log.warning("fomc_ical: YAML load failed: %s", exc)
            return None

    @staticmethod
    def _to_date(val: Any) -> dt.date | None:
        if isinstance(val, dt.datetime):
            return val.date()
        if isinstance(val, dt.date):
            return val
        return None
