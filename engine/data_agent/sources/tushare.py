"""
Tushare Pro data source — fundamentals and adj_factor.

Reads TUSHARE_TOKEN from environment (set in ~/.zshrc).
Used as primary source for FUNDAMENTAL and SHAREHOLDER field groups.

API limits (free tier): 500 calls/min; fields marked [pro] require points.
"""

from __future__ import annotations

import datetime as dt
import os
from typing import Any

from engine.data_agent.rate_limiter import RateLimiter
from engine.data_agent.sources.base import AbstractSource, SourceError


class TushareSource(AbstractSource):
    """Tushare Pro wrapper — fundamentals, adj_factor, shareholders."""

    name = "tushare"
    domain = "tushare"

    def __init__(self, rate_limiter: RateLimiter) -> None:
        super().__init__(rate_limiter)
        token = os.environ.get("TUSHARE_TOKEN") or os.environ.get("TSPRO_TOKEN")
        if not token:
            raise OSError(
                "TUSHARE_TOKEN is not set. Add it to ~/.zshrc and run: source ~/.zshrc"
            )
        try:
            import tushare as ts
            ts.set_token(token)
            self._pro = ts.pro_api()
        except ImportError as exc:
            raise ImportError(
                "tushare is not installed. Run: uv sync --extra tushare"
            ) from exc

    # ── AbstractSource interface ──────────────────────────────────────────────

    def fetch_quotes(self, codes: list[str]) -> list[dict[str, Any]]:
        """Tushare real-time quotes via pro.realtime_list (requires >= 2000 points)."""
        raise SourceError(
            "TushareSource does not support real-time quotes; use Tencent/Eastmoney/Sina"
        )

    # ── Fundamentals ──────────────────────────────────────────────────────────

    def fetch_fundamentals(
        self,
        codes: list[str],
        period: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch income + balance + cashflow + financial indicators.
        period: 'YYYYMMDD' of report period end (e.g. '20241231'); defaults to latest.
        """
        if period is None:
            # Latest annual report
            now = dt.date.today()
            year = now.year - 1 if now.month < 5 else now.year
            period = f"{year}1231"

        ts_codes = [self._ts_code(c) for c in codes]
        results: list[dict[str, Any]] = []

        for ts_code, code in zip(ts_codes, codes):
            self._rl.acquire(self.domain)
            try:
                row = self._fetch_one_fundamental(ts_code, code, period)
                if row:
                    results.append(row)
                self._rl.record_success(self.domain)
            except Exception as exc:
                self._rl.record_failure(self.domain, 0)
                raise SourceError(f"tushare fundamentals({code}) failed: {exc}") from exc

        return results

    def _fetch_one_fundamental(
        self,
        ts_code: str,
        code: str,
        period: str,
    ) -> dict[str, Any] | None:
        try:
            inc = self._pro.income(ts_code=ts_code, period=period, fields=(
                "ts_code,ann_date,end_date,total_revenue,n_income_attr_p,"
                "ebit,rd_exp"
            ))
        except Exception:
            inc = None

        try:
            bal = self._pro.balancesheet(ts_code=ts_code, period=period, fields=(
                "ts_code,end_date,total_assets,total_liab,goodwill"
            ))
        except Exception:
            bal = None

        try:
            ind = self._pro.fina_indicator(ts_code=ts_code, period=period, fields=(
                "ts_code,end_date,roe,roa,grossprofit_margin,netprofit_margin,"
                "eps,bps,debt_to_assets,op_income"
            ))
        except Exception:
            ind = None

        if inc is None and bal is None and ind is None:
            return None

        report_date = period[:4] + "-" + period[4:6] + "-" + period[6:]
        row: dict[str, Any] = {
            "code": code,
            "report_date": report_date,
            "period_type": "annual" if period.endswith("1231") else "quarterly",
            "source": "tushare",
            "fetched_at": dt.datetime.now(tz=dt.UTC),
        }

        if inc is not None and not inc.empty:
            r = inc.iloc[0]
            row["revenue"]    = r.get("total_revenue")
            row["net_profit"] = r.get("n_income_attr_p")
            row["rd_ratio"]   = None  # computed from rd_exp / revenue if needed

        if bal is not None and not bal.empty:
            r = bal.iloc[0]
            row["goodwill"] = r.get("goodwill")

        if ind is not None and not ind.empty:
            r = ind.iloc[0]
            row["gross_margin"] = r.get("grossprofit_margin")
            row["net_margin"]   = r.get("netprofit_margin")
            row["roe"]          = r.get("roe")
            row["roa"]          = r.get("roa")
            row["eps"]          = r.get("eps")
            row["bps"]          = r.get("bps")
            row["debt_ratio"]   = r.get("debt_to_assets")
            row["op_cashflow"]  = r.get("op_income")

        return row

    # ── Adj factor ────────────────────────────────────────────────────────────

    def fetch_adj_factor(
        self,
        code: str,
        start: dt.date | None = None,
        end: dt.date | None = None,
    ) -> list[dict[str, Any]]:
        """Adjustment factors for back-adjusted prices."""
        end_date   = end or dt.date.today()
        start_date = start or (end_date - dt.timedelta(days=365))
        self._rl.acquire(self.domain)
        try:
            df = self._pro.adj_factor(
                ts_code=self._ts_code(code),
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
            )
            self._rl.record_success(self.domain)
        except Exception as exc:
            self._rl.record_failure(self.domain, 0)
            raise SourceError(f"tushare adj_factor({code}) failed: {exc}") from exc

        results = []
        for _, row in df.iterrows():
            results.append({
                "code": code,
                "trade_date": str(row.get("trade_date", ""))[:8],
                "adj_factor": row.get("adj_factor"),
                "source": "tushare",
            })
        return results

    # ── Shareholders ──────────────────────────────────────────────────────────

    def fetch_shareholders(
        self,
        code: str,
        period: str | None = None,
    ) -> list[dict[str, Any]]:
        """Top-10 free-float shareholders via top10_floatholders."""
        if period is None:
            now = dt.date.today()
            year = now.year - 1 if now.month < 5 else now.year
            period = f"{year}1231"

        self._rl.acquire(self.domain)
        try:
            df = self._pro.top10_floatholders(
                ts_code=self._ts_code(code),
                period=period,
            )
            self._rl.record_success(self.domain)
        except Exception as exc:
            self._rl.record_failure(self.domain, 0)
            raise SourceError(f"tushare top10_floatholders({code}) failed: {exc}") from exc

        report_date = period[:4] + "-" + period[4:6] + "-" + period[6:]
        results = []
        for _, row in df.iterrows():
            results.append({
                "code": code,
                "report_date": report_date,
                "holder_name": str(row.get("holder_name", "")),
                "hold_amount": row.get("hold_amount"),
                "hold_ratio": row.get("hold_ratio"),
                "source": "tushare",
            })
        return results

    # ── Business segments ─────────────────────────────────────────────────────

    def fetch_business_segments(self, code: str) -> list[dict[str, Any]]:
        """Main business composition via fina_mainbz."""
        self._rl.acquire(self.domain)
        try:
            df = self._pro.fina_mainbz(ts_code=self._ts_code(code), type="P")
            self._rl.record_success(self.domain)
        except Exception as exc:
            self._rl.record_failure(self.domain, 0)
            raise SourceError(f"tushare fina_mainbz({code}) failed: {exc}") from exc

        results = []
        for _, row in df.iterrows():
            end_date = str(row.get("end_date", ""))
            report_date = (end_date[:4] + "-" + end_date[4:6] + "-" + end_date[6:]
                           if len(end_date) == 8 else end_date[:10])
            results.append({
                "code": code,
                "report_date": report_date,
                "segment_name": str(row.get("bz_item", "")),
                "revenue": row.get("bz_sales"),
                "profit": row.get("bz_profit"),
                "revenue_ratio": row.get("bz_sales_ratio"),
                "profit_ratio": row.get("bz_profit_ratio"),
                "source": "tushare",
            })
        return results

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _ts_code(code: str) -> str:
        """Convert bare 6-digit code to Tushare ts_code format (e.g. '600000.SH')."""
        suffix = "SH" if code.startswith(("6", "9")) else "SZ"
        return f"{code}.{suffix}"
