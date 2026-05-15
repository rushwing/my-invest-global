"""
Abstract base class for all data sources.

Provides:
  - requests.Session with UA rotation and domain-appropriate Referer
  - _get(): rate-limited JSON fetch with retry and failure recording
  - Subclasses must implement fetch_quotes() and may implement other fetch_* methods
"""

from __future__ import annotations

import random
import time
from abc import ABC, abstractmethod
from typing import Any

import requests

from engine.data_agent.rate_limiter import RateLimiter


# User-Agent pool — rotate to reduce fingerprinting
_UA_POOL = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]

# Per-domain Referer headers expected by each source's CDN/WAF
_DOMAIN_REFERER: dict[str, str] = {
    "qt.gtimg.cn":                    "https://finance.qq.com/",
    "web.ifzq.gtimg.cn":              "https://finance.qq.com/",
    "hq.sinajs.cn":                   "https://finance.sina.com.cn/",
    "push2.eastmoney.com":            "https://quote.eastmoney.com/",
    "push2his.eastmoney.com":         "https://quote.eastmoney.com/",
    "datacenter.eastmoney.com":       "https://data.eastmoney.com/",
    "emweb.securities.eastmoney.com": "https://emweb.securities.eastmoney.com/",
    "data.eastmoney.com":             "https://data.eastmoney.com/",
    "cninfo.com.cn":                  "https://www.cninfo.com.cn/",
}

# HTTP error codes worth recording as rate-limit failures
_RATE_LIMIT_STATUSES = frozenset({429, 403, 503})


class SourceError(Exception):
    """Raised when a source fails after all retries are exhausted."""


class AbstractSource(ABC):
    """Base class for all data sources."""

    name: str   # short identifier, matches keys in FIELD_POLICIES / DOMAIN_CONFIGS
    domain: str  # primary hostname for rate-limiter lookups

    def __init__(self, rate_limiter: RateLimiter) -> None:
        self._rl = rate_limiter
        self._session = self._new_session()

    def _new_session(self) -> requests.Session:
        s = requests.Session()
        s.headers.update({
            "User-Agent": random.choice(_UA_POOL),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
        })
        referer = _DOMAIN_REFERER.get(self.domain)
        if referer:
            s.headers["Referer"] = referer
        return s

    def _rotate_ua(self) -> None:
        self._session.headers["User-Agent"] = random.choice(_UA_POOL)

    def _get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        retries: int = 3,
        timeout: int = 20,
    ) -> Any:
        """
        Rate-limited GET with retry and circuit-breaker integration.
        Returns parsed JSON on success; raises SourceError after all retries.
        """
        if self._rl.is_circuit_open(self.domain):
            raise SourceError(f"Circuit open for {self.domain}")

        last_exc: Exception | None = None
        for attempt in range(retries):
            self._rl.acquire(self.domain)
            try:
                resp = self._session.get(url, params=params, timeout=timeout)
                if resp.status_code in _RATE_LIMIT_STATUSES:
                    # Rate-limit responses: record once and give up immediately
                    self._rl.record_failure(self.domain, resp.status_code)
                    raise SourceError(
                        f"{self.domain} returned {resp.status_code} on {url}"
                    )
                resp.raise_for_status()
                self._rl.record_success(self.domain)
                return resp.json()
            except SourceError:
                raise
            except Exception as exc:
                last_exc = exc
                if attempt < retries - 1:
                    # Rotate UA on retry to vary fingerprint; don't record yet
                    self._rotate_ua()
                    time.sleep(2 ** attempt)  # 1s, 2s before final attempt

        # Record a single failure after all retries are exhausted
        self._rl.record_failure(self.domain, 0)
        raise SourceError(
            f"{self.domain} failed after {retries} attempts: {last_exc}"
        ) from last_exc

    # ── Interface ─────────────────────────────────────────────────────────────

    @abstractmethod
    def fetch_quotes(self, codes: list[str]) -> list[dict[str, Any]]:
        """Fetch real-time quote snapshots for the given stock codes."""
        ...
