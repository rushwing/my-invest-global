"""UpdateClass — eight-tier fetch frequency classification for macro indicators."""

from __future__ import annotations

from enum import StrEnum


class UpdateClass(StrEnum):
    INTRADAY_FAST = "intraday_fast"   # 1–5 min
    INTRADAY_SLOW = "intraday_slow"   # 15–60 min
    DAILY         = "daily"           # post-close
    WEEKLY        = "weekly"          # reserved
    MONTHLY_FIXED = "monthly_fixed"   # BLS/NBS release day
    QUARTERLY     = "quarterly"       # SEC 10-Q/10-K after filing
    EVENT_DRIVEN  = "event_driven"    # FOMC decision day etc.
    STATIC_YAML   = "static_yaml"     # manually maintained
