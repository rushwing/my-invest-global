"""
Yahoo Finance data source via yfinance — US observation pool only.

Used for the 18-stock US pool (NVDA, AMD, TSLA, MSFT, GOOGL, AMZN, META,
AVGO, ASML, AMAT, KLAC, LRCX, AAPL, TSM, ARM, SMCI, MRVL, QCOM).

Rate-limiting: yfinance is a scraper; be conservative (1.5s between calls).
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from engine.data_agent.rate_limiter import RateLimiter
from engine.data_agent.sources.base import AbstractSource, SourceError

_BATCH_SIZE = 10  # yfinance download() handles batches; keep small to avoid timeouts


class YahooSource(AbstractSource):
    """Yahoo Finance via yfinance — US stock pool only."""

    name = "yahoo"
    domain = "yahoo"

    def __init__(self, rate_limiter: RateLimiter) -> None:
        super().__init__(rate_limiter)
        try:
            import yfinance  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "yfinance is not installed. Run: uv sync --extra data"
            ) from exc

    # ── AbstractSource interface ──────────────────────────────────────────────

    def fetch_quotes(self, codes: list[str]) -> list[dict[str, Any]]:
        """
        Fetch real-time quotes for US ticker symbols.
        codes: list of Yahoo ticker symbols (e.g. ['NVDA', 'AMD', 'TSM']).
        """
        import yfinance as yf

        results: list[dict[str, Any]] = []
        for i in range(0, len(codes), _BATCH_SIZE):
            batch = codes[i : i + _BATCH_SIZE]
            self._rl.acquire(self.domain)
            try:
                tickers = yf.Tickers(" ".join(batch))
                self._rl.record_success(self.domain)
            except Exception as exc:
                self._rl.record_failure(self.domain, 0)
                raise SourceError(f"yahoo fetch_quotes batch failed: {exc}") from exc

            for symbol in batch:
                try:
                    info = tickers.tickers[symbol].fast_info
                    results.append({
                        "code": symbol,
                        "quote_time": dt.datetime.now(tz=dt.timezone.utc),
                        "price": getattr(info, "last_price", None),
                        "pct_change": None,  # computed from prev_close if needed
                        "volume": getattr(info, "last_volume", None),
                        "amount": None,
                        "market_cap": getattr(info, "market_cap", None),
                        "dynamic_pe": None,
                        "pb": None,
                        "turnover_rate": None,
                        "source": "yahoo",
                    })
                except Exception:
                    pass  # individual ticker failure is non-fatal

        return results

    # ── K-line ────────────────────────────────────────────────────────────────

    def fetch_kline_day(
        self,
        code: str,
        start: dt.date | None = None,
        end: dt.date | None = None,
        adjust: str = "qfq",
    ) -> list[dict[str, Any]]:
        """Daily K-line for a US ticker. adjust param is ignored (yfinance auto-adjusts)."""
        import yfinance as yf

        end_date   = end or dt.date.today()
        start_date = start or (end_date - dt.timedelta(days=420))

        self._rl.acquire(self.domain)
        try:
            df = yf.download(
                code,
                start=start_date.isoformat(),
                end=end_date.isoformat(),
                auto_adjust=True,
                progress=False,
                multi_level_index=False,
            )
            self._rl.record_success(self.domain)
        except Exception as exc:
            self._rl.record_failure(self.domain, 0)
            raise SourceError(f"yahoo kline_day({code}) failed: {exc}") from exc

        results = []
        for date_idx, row in df.iterrows():
            results.append({
                "code": code,
                "trade_date": str(date_idx)[:10],
                "open": row.get("Open"),
                "close": row.get("Close"),
                "high": row.get("High"),
                "low": row.get("Low"),
                "volume": row.get("Volume"),
                "amount": None,
                "adj_type": "auto",
                "source": "yahoo",
            })
        return results
