"""
Sina Finance data source — hq.sinajs.cn real-time quotes (backup for Tencent).

Response format: var hq_str_sh600000="name,open,prev_close,current,...";
Fields at indices (comma-separated, 1-based):
  [0]  company name
  [1]  open
  [2]  prev_close
  [3]  current price
  [4]  high
  [5]  low
  [7]  volume (shares)
  [8]  amount (yuan)
  [31] quote_time (HH:MM:SS)
  [30] quote_date (YYYY-MM-DD)
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from engine.data_agent.rate_limiter import RateLimiter
from engine.data_agent.sources.base import AbstractSource, SourceError

_BATCH_SIZE = 50  # sina can handle larger batches than tencent


def _sina_symbol(code: str) -> str:
    return ("sh" if code.startswith(("6", "9")) else "sz") + code


def _parse_float(v: str) -> float | None:
    try:
        return float(v) if v else None
    except ValueError:
        return None


def _chunk(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


class SinaSource(AbstractSource):
    """Sina Finance hq.sinajs.cn real-time quotes."""

    name = "sina"
    domain = "hq.sinajs.cn"

    def __init__(self, rate_limiter: RateLimiter) -> None:
        super().__init__(rate_limiter)
        self._session.headers.update({
            "Referer": "https://finance.sina.com.cn/",
        })

    def fetch_quotes(self, codes: list[str]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for batch in _chunk(codes, _BATCH_SIZE):
            results.extend(self._fetch_batch(batch))
        return results

    def _fetch_batch(self, codes: list[str]) -> list[dict[str, Any]]:
        symbols = ",".join(_sina_symbol(c) for c in codes)
        url = f"https://hq.sinajs.cn/list={symbols}"
        self._rl.acquire(self.domain)
        try:
            resp = self._session.get(url, timeout=15)
            resp.raise_for_status()
            self._rl.record_success(self.domain)
        except Exception as exc:
            self._rl.record_failure(self.domain, 0)
            raise SourceError(f"sina batch quote failed: {exc}") from exc

        return self._parse_response(resp.text, codes)

    def _parse_response(self, text: str, codes: list[str]) -> list[dict[str, Any]]:
        code_set = set(codes)
        results = []
        for line in text.strip().split(";"):
            line = line.strip()
            if not line:
                continue
            match = re.match(r'var hq_str_(\w+)="(.+)"', line)
            if not match:
                continue
            symbol = match.group(1)
            raw_code = symbol[2:]
            if raw_code not in code_set:
                continue
            fields = match.group(2).split(",")
            if len(fields) < 32:
                continue
            date_str = fields[30]
            time_str = fields[31]
            try:
                quote_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            results.append({
                "code": raw_code,
                "quote_time": quote_time,
                "price": _parse_float(fields[3]),
                "pct_change": None,  # calculated from prev_close if needed
                "volume": _parse_float(fields[8]),   # amount in yuan
                "amount": _parse_float(fields[8]),
                "market_cap": None,  # not provided by Sina real-time
                "dynamic_pe": None,
                "source": "sina",
            })
        return results
