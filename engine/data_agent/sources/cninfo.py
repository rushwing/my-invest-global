"""
CNINFO (巨潮资讯) data source — company announcements.

Uses the CNINFO open API: http://www.cninfo.com.cn/new/hisAnnouncement/query

This is a slow, polite scraper. Rate limit: 5s min_delay, burst=1,
cooldown_s=1800 (configured in rate_limiter.DOMAIN_CONFIGS).

CNINFO requires a query_time cursor for pagination. We fetch the last
30 days of announcements per stock.

Note: CNINFO uses its own stock code format (e.g. '000001' without exchange prefix).
The exchange is passed separately as 'szse' or 'sse'.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from engine.data_agent.rate_limiter import RateLimiter
from engine.data_agent.sources.base import AbstractSource, SourceError

_API_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
_PAGE_SIZE = 30


def _exchange(code: str) -> str:
    return "sse" if code.startswith(("6", "9")) else "szse"


class CNINFOSource(AbstractSource):
    """巨潮资讯 announcement fetcher — slow, polite."""

    name = "cninfo"
    domain = "cninfo.com.cn"

    def __init__(self, rate_limiter: RateLimiter) -> None:
        super().__init__(rate_limiter)
        self._session.headers.update({
            "Referer": "http://www.cninfo.com.cn/new/index",
            "Origin":  "http://www.cninfo.com.cn",
        })

    # ── AbstractSource interface ──────────────────────────────────────────────

    def fetch_quotes(self, codes: list[str]) -> list[dict[str, Any]]:
        raise SourceError("CNINFOSource does not support real-time quotes")

    # ── Announcements ─────────────────────────────────────────────────────────

    def fetch_announcements(
        self,
        code: str,
        days: int = 30,
    ) -> list[dict[str, Any]]:
        """
        Fetch announcement list for a single stock for the past `days` days.
        Returns list of announcement metadata (title, date, URL — not full text).
        """
        end_dt   = dt.date.today()
        start_dt = end_dt - dt.timedelta(days=days)
        exchange = _exchange(code)

        self._rl.acquire(self.domain)
        try:
            resp = self._session.post(
                _API_URL,
                data={
                    "stock":      f"{code},{exchange}",
                    "tabName":    "fulltext",
                    "pageSize":   _PAGE_SIZE,
                    "pageNum":    1,
                    "column":     exchange,
                    "category":   "",
                    "plate":      "",
                    "seDate":     f"{start_dt.isoformat()}~{end_dt.isoformat()}",
                    "searchkey":  "",
                    "secid":      "",
                    "sortName":   "",
                    "sortType":   "",
                    "isHLtitle":  "true",
                },
                timeout=30,
            )
            resp.raise_for_status()
            self._rl.record_success(self.domain)
        except Exception as exc:
            self._rl.record_failure(self.domain, 0)
            raise SourceError(f"cninfo announcements({code}) failed: {exc}") from exc

        try:
            data = resp.json()
        except Exception as exc:
            raise SourceError(f"cninfo JSON parse failed for {code}: {exc}") from exc

        announcements = data.get("announcements") or []
        results = []
        for ann in announcements:
            ann_time_ms = ann.get("announcementTime")
            if ann_time_ms:
                ann_dt = dt.datetime.fromtimestamp(
                    ann_time_ms / 1000, tz=dt.UTC
                )
            else:
                ann_dt = None

            results.append({
                "code":           code,
                "ann_id":         ann.get("announcementId", ""),
                "title":          ann.get("announcementTitle", ""),
                "ann_time":       ann_dt,
                "category":       ann.get("announcementTypeName", ""),
                "adjunct_url":    ann.get("adjunctUrl", ""),
                "source":         "cninfo",
            })
        return results
