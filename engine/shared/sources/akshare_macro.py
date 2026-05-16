"""
AKShare source for macro indicator data.

Wraps AKShare library functions for:
  - China CPI / PPI (NBS monthly releases)
  - US CPI (via AKShare wrapper for BLS data)
  - CaiLianShe (CLS) financial news telegrams
  - SGX A50 futures (pre-open A-share signal)
  - A-share two-market daily turnover

Requires: akshare==1.18.60 (pinned; AKShare API is unstable across versions)
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from engine.data_agent.rate_limiter import RateLimiter
from engine.shared.sources.base_macro import MacroAbstractSource


class AKShareMacroSource(MacroAbstractSource):
    name = "akshare_macro"
    domain = "akshare"

    def __init__(self, rate_limiter: RateLimiter) -> None:
        super().__init__(rate_limiter)

    def _ak_call(self, func_name: str, **kwargs: Any) -> Any:
        """Acquire rate-limit slot, call an AKShare function, record result."""
        try:
            import akshare as ak  # optional dependency
        except ImportError as exc:
            raise ImportError(
                "akshare is required: uv pip install 'my-invest-global[data]'"
            ) from exc

        self._rl.acquire(self.domain)
        try:
            result = getattr(ak, func_name)(**kwargs)
            self._rl.record_success(self.domain)
            return result
        except Exception:
            self._rl.record_failure(self.domain, 0)
            raise

    def fetch_china_cpi(self, start_date: str | dt.date | None = None) -> list[dict[str, Any]]:
        """China CPI monthly YoY/MoM from NBS via AKShare."""
        df = self._ak_call("macro_china_cpi_monthly")
        return self._df_to_records(df, indicator_id="CN_CPI", group_code="I",
                                   date_col="日期", value_col="今值", market_tz="Asia/Shanghai",
                                   value_unit="percent_yoy", start_date=start_date)

    def fetch_china_ppi(self, start_date: str | dt.date | None = None) -> list[dict[str, Any]]:
        """China PPI monthly YoY from NBS via AKShare."""
        df = self._ak_call("macro_china_ppi_monthly")
        return self._df_to_records(df, indicator_id="CN_PPI", group_code="I",
                                   date_col="日期", value_col="今值", market_tz="Asia/Shanghai",
                                   value_unit="percent_yoy", start_date=start_date)

    def fetch_us_cpi(self, start_date: str | dt.date | None = None) -> list[dict[str, Any]]:
        """US CPI monthly YoY via AKShare BLS wrapper."""
        df = self._ak_call("macro_usa_cpi_monthly")
        return self._df_to_records(df, indicator_id="CPIAUCSL", group_code="I",
                                   date_col="日期", value_col="今值", market_tz="America/New_York",
                                   value_unit="percent_yoy", start_date=start_date)

    def fetch_cls_news(self, limit: int = 50) -> list[dict[str, Any]]:
        """CaiLianShe (财联社) financial news telegrams."""
        df = self._ak_call("stock_info_global_cls", symbol="全部")
        if df is None or df.empty:
            return []
        now_utc = dt.datetime.now(tz=__import__("zoneinfo").ZoneInfo("UTC"))
        rows = df.head(limit).to_dict(orient="records")
        return [
            {
                "indicator_id": "CLS_NEWS",
                "group_code":   "O",
                "period_date":  dt.date.today(),
                "market_tz":    "Asia/Shanghai",
                "value":        None,
                "value_raw":    str(r),
                "source":       self.name,
                "utc_ts":       now_utc,
                "fetched_at":   now_utc,
            }
            for r in rows
        ]

    def fetch_sgx_a50(self) -> list[dict[str, Any]]:
        """SGX Xinhua A50 futures — pre-open A-share leading indicator."""
        df = self._ak_call("futures_foreign_hist", symbol="A50")
        if df is None or df.empty:
            return []
        row = df.iloc[-1]
        local_date = _parse_date(row.get("日期") or row.get("date"))
        return [
            self._make_period_record(
                indicator_id="SGX_A50",
                group_code="N",
                period_date=local_date or dt.date.today(),
                market_tz="Asia/Singapore",
                value=float(row.get("收盘价") or row.get("close") or 0),
                value_unit="index_points",
                value_raw=str(row.to_dict()),
            )
        ]

    def fetch_a_share_turnover(self) -> list[dict[str, Any]]:
        """A-share two-market daily turnover (两市成交额)."""
        df = self._ak_call("stock_market_deal_em")
        if df is None or df.empty:
            return []
        row = df.iloc[-1]
        local_date = _parse_date(row.get("日期") or row.get("date"))
        return [
            self._make_period_record(
                indicator_id="A_SHARE_TURNOVER",
                group_code="N",
                period_date=local_date or dt.date.today(),
                market_tz="Asia/Shanghai",
                value=float(row.get("成交额") or row.get("amount") or 0),
                value_unit="CNY",
                value_raw=str(row.to_dict()),
            )
        ]

    def _df_to_records(
        self,
        df: Any,
        *,
        indicator_id: str,
        group_code: str,
        date_col: str,
        value_col: str,
        market_tz: str,
        value_unit: str,
        start_date: str | dt.date | None,
    ) -> list[dict[str, Any]]:
        if df is None or df.empty:
            return []
        cutoff = dt.date.fromisoformat(str(start_date)) if start_date else None
        records: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            period_date = _parse_date(row.get(date_col))
            if period_date is None:
                continue
            if cutoff and period_date < cutoff:
                continue
            raw = str(row.get(value_col, ""))
            try:
                value = float(raw.replace("%", ""))
            except (ValueError, AttributeError):
                continue
            records.append(
                self._make_period_record(
                    indicator_id=indicator_id,
                    group_code=group_code,
                    period_date=period_date,
                    market_tz=market_tz,
                    value=value,
                    value_unit=value_unit,
                    value_raw=raw,
                )
            )
        return records


def _parse_date(raw: Any) -> dt.date | None:
    if raw is None:
        return None
    if isinstance(raw, dt.date):
        return raw if not isinstance(raw, dt.datetime) else raw.date()
    try:
        return dt.date.fromisoformat(str(raw)[:10])
    except (ValueError, TypeError):
        return None
