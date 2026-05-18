"""ReleaseCalendar — BLS/NBS official release date store (BP-7).

Reads from and writes to the `release_dates` DuckDB table.
HTTP failures are safe-degraded: existing data is preserved on error.
"""

from __future__ import annotations

import logging
from datetime import date

import httpx

from engine.macro_agent.storage import MacroStorage

log = logging.getLogger(__name__)

_BLS_URL = "https://www.bls.gov/schedule/{year}/home.htm"
_NBS_URL = "https://www.stats.gov.cn/sj/zxfb/"

# BLS indicator IDs that map to BLS release schedule
_BLS_INDICATORS = {"CPIAUCSL", "PPIACO"}
_NBS_INDICATORS = {"CPI_CHINA", "PPI_CHINA"}


class ReleaseCalendar:
    """Manages official data release dates for MONTHLY_FIXED indicators."""

    def __init__(self, storage: MacroStorage) -> None:
        self._storage = storage

    def is_release_day(self, indicator_id: str, check_date: date) -> bool:
        """Return True if check_date is an official release day for indicator_id."""
        row = self._storage._conn.execute(
            "SELECT 1 FROM release_dates WHERE indicator_id = ? AND release_date = ?",
            [indicator_id, check_date],
        ).fetchone()
        return row is not None

    def has_any_dates(self, indicator_id: str) -> bool:
        """Return True if release_dates contains at least one row for indicator_id."""
        row = self._storage._conn.execute(
            "SELECT 1 FROM release_dates WHERE indicator_id = ? LIMIT 1",
            [indicator_id],
        ).fetchone()
        return row is not None

    def populate_bls(self, year: int) -> None:
        """Parse BLS release schedule for year and store in release_dates.

        On HTTP or parse failure, logs a warning and preserves existing data.
        """
        url = _BLS_URL.format(year=year)
        try:
            resp = httpx.get(url, timeout=15)
            resp.raise_for_status()
            self._parse_and_store_bls(resp.text, year)
        except Exception as exc:
            log.warning("populate_bls(%d) failed — preserving existing data: %s", year, exc)

    def populate_nbs(self, year: int) -> None:
        """Parse NBS release schedule for year.

        On HTTP or parse failure, logs a warning and preserves existing data.
        """
        try:
            resp = httpx.get(_NBS_URL, timeout=15)
            resp.raise_for_status()
            self._parse_and_store_nbs(resp.text, year)
        except Exception as exc:
            log.warning("populate_nbs(%d) failed — preserving existing data: %s", year, exc)

    # ── Private ───────────────────────────────────────────────────────────────

    def _parse_and_store_bls(self, html: str, year: int) -> None:
        """Parse BLS HTML and insert release dates. Best-effort; no raise on bad HTML."""
        import re  # noqa: PLC0415
        # BLS schedule page lists dates in format "Month DD, YYYY"
        # e.g. "May 13, 2026"
        months = {"january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
                  "july":7,"august":8,"september":9,"october":10,"november":11,"december":12}
        pattern = re.compile(
            r'(january|february|march|april|may|june|july|august|september|october|november|december)'
            r'\s+(\d{1,2}),\s+' + str(year),
            re.IGNORECASE,
        )
        found: list[date] = []
        for m in pattern.finditer(html):
            month = months[m.group(1).lower()]
            day   = int(m.group(2))
            try:
                found.append(date(year, month, day))
            except ValueError:
                continue
        for indicator_id in _BLS_INDICATORS:
            for d in found:
                try:
                    self._storage._conn.execute(
                        "INSERT INTO release_dates (indicator_id, release_date, source) "
                        "VALUES (?, ?, 'BLS') ON CONFLICT DO NOTHING",
                        [indicator_id, d],
                    )
                except Exception:
                    pass

    def _parse_and_store_nbs(self, html: str, year: int) -> None:
        """Parse NBS schedule. Best-effort stub — NBS page format varies."""
        pass  # fallback: daily trigger via MONTHLY_FIXED fallback path
