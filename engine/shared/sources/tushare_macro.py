"""
Tushare Pro source for macro FX and index data.

Requires env var: TUSHARE_TOKEN
"""

from __future__ import annotations

import datetime as dt
import os
from typing import Any

from engine.data_agent.rate_limiter import RateLimiter
from engine.shared.sources.base_macro import MacroAbstractSource


class TushareMacroSource(MacroAbstractSource):
    name = "tushare_macro"
    domain = "tushare"

    def __init__(self, rate_limiter: RateLimiter, token: str | None = None) -> None:
        super().__init__(rate_limiter)
        self._token = token or os.environ.get("TUSHARE_TOKEN")
        self._pro: Any = None  # lazy-initialised on first use

    def _get_pro(self) -> Any:
        if self._pro is None:
            try:
                import tushare as ts
            except ImportError as exc:
                raise ImportError(
                    "tushare is required: uv pip install 'my-invest-global[tushare]'"
                ) from exc
            if not self._token:
                raise RuntimeError("TUSHARE_TOKEN environment variable is not set.")
            ts.set_token(self._token)
            self._pro = ts.pro_api()
        return self._pro

    def fetch_fx_daily(
        self,
        ts_code: str,
        start_date: str | dt.date | None = None,
        end_date: str | dt.date | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch daily FX rate (e.g. USDCNY.FXCM, USDCNH.FXCM).

        Returns records matching macro_indicators DDL.
        """
        self._rl.acquire(self.domain)
        try:
            pro = self._get_pro()
            kwargs: dict[str, str] = {"ts_code": ts_code}
            if start_date:
                kwargs["start_date"] = str(start_date).replace("-", "")
            if end_date:
                kwargs["end_date"] = str(end_date).replace("-", "")
            df = pro.fx_daily(**kwargs)
            self._rl.record_success(self.domain)
        except Exception:
            self._rl.record_failure(self.domain, 0)
            raise

        if df is None or df.empty:
            return []

        indicator_id = ts_code.split(".")[0]   # "USDCNY" from "USDCNY.FXCM"
        records: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            raw_date = str(row.get("trade_date", ""))[:8]
            try:
                period_date = dt.date(int(raw_date[:4]), int(raw_date[4:6]), int(raw_date[6:8]))
            except (ValueError, TypeError):
                continue
            close_val = row.get("close")
            if close_val is None:
                continue
            records.append(
                self._make_period_record(
                    indicator_id=indicator_id,
                    group_code="N",
                    period_date=period_date,
                    market_tz="Asia/Shanghai",
                    value=float(close_val),
                    value_unit="rate",
                    value_raw=str(close_val),
                )
            )
        return records

    def fetch_index_daily(
        self,
        ts_code: str,
        start_date: str | dt.date | None = None,
        end_date: str | dt.date | None = None,
        group_code: str = "",
    ) -> list[dict[str, Any]]:
        """Fetch daily index OHLCV (e.g. '000688.SH' for 科创50)."""
        self._rl.acquire(self.domain)
        try:
            pro = self._get_pro()
            kwargs: dict[str, str] = {"ts_code": ts_code}
            if start_date:
                kwargs["start_date"] = str(start_date).replace("-", "")
            if end_date:
                kwargs["end_date"] = str(end_date).replace("-", "")
            df = pro.index_daily(**kwargs)
            self._rl.record_success(self.domain)
        except Exception:
            self._rl.record_failure(self.domain, 0)
            raise

        if df is None or df.empty:
            return []

        records: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            raw_date = str(row.get("trade_date", ""))[:8]
            try:
                period_date = dt.date(int(raw_date[:4]), int(raw_date[4:6]), int(raw_date[6:8]))
            except (ValueError, TypeError):
                continue
            close_val = row.get("close")
            if close_val is None:
                continue
            records.append(
                self._make_period_record(
                    indicator_id=ts_code,
                    group_code=group_code,
                    period_date=period_date,
                    market_tz="Asia/Shanghai",
                    value=float(close_val),
                    value_unit="index_points",
                    value_raw=str(close_val),
                )
            )
        return records
