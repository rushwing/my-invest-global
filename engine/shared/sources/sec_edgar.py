"""
SEC EDGAR companyfacts source for quarterly CapEx data.

Fetches XBRL companyfacts JSON and de-cumulates 10-Q filings into single-quarter
values. 10-K annual filings yield Q4 = FY - Q3_cumulative (BP-3).

Rate limit: 8 req/s (official ceiling 10 req/s; safety margin applied).
User-Agent: hardcoded per SEC EDGAR compliance policy (BP-2).
Content-hash deduplication via SHA-256 (BP-10).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from typing import Any

from engine.data_agent.rate_limiter import RateLimiter
from engine.shared.sources.base_macro import MacroAbstractSource

_COMPANYFACTS_BASE = "https://data.sec.gov/api/xbrl/companyfacts"
_SEC_USER_AGENT = "my-invest-global ruoxu.wang@gmail.com"
_DEFAULT_TAG = "PaymentsToAcquirePropertyPlantAndEquipment"

# Maps EDGAR fiscal period code → quarter number (Q4 comes from FY in 10-K).
_FP_ORDER = {"Q1": 1, "Q2": 2, "Q3": 3, "FY": 4}


class SECEdgarSource(MacroAbstractSource):
    name = "sec_edgar"
    domain = "data.sec.gov"

    def __init__(self, rate_limiter: RateLimiter) -> None:
        super().__init__(rate_limiter)
        # SEC EDGAR requires a compliant User-Agent — override at class level (BP-2).
        self._session.headers["User-Agent"] = _SEC_USER_AGENT

    def fetch_capex_quarterly(
        self,
        cik: str,
        tag: str = _DEFAULT_TAG,
        company: str = "",
    ) -> list[dict[str, Any]]:
        """
        Fetch and de-cumulate quarterly CapEx for one company.

        Args:
            cik:     10-digit CIK with leading zeros (e.g. "0000789019").
            tag:     XBRL concept tag for CapEx.
            company: Ticker symbol stored in records (e.g. "MSFT").

        Returns:
            list of dicts with single-quarter capex_usd values (positive),
            compatible with capex_quarterly DDL.
        """
        url = f"{_COMPANYFACTS_BASE}/CIK{cik}.json"
        raw = self._get(url)
        raw_bytes = json.dumps(raw, sort_keys=True).encode()
        source_hash = hashlib.sha256(raw_bytes).hexdigest()

        units: list[dict] = (
            raw.get("facts", {})
               .get("us-gaap", {})
               .get(tag, {})
               .get("units", {})
               .get("USD", [])
        )
        if not units:
            return []

        return self._decumulate(units, cik=cik, company=company, tag=tag, source_hash=source_hash)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _decumulate(
        self,
        units: list[dict],
        *,
        cik: str,
        company: str,
        tag: str,
        source_hash: str,
    ) -> list[dict[str, Any]]:
        """
        Convert cumulative EDGAR filings into single-quarter values.

        Algorithm:
          Q1_single = Q1_cumulative            (first quarter of fiscal year)
          Q2_single = Q2_cumulative - Q1_cum
          Q3_single = Q3_cumulative - Q2_cum
          Q4_single = FY_annual    - Q3_cum    (from 10-K)

        Only uses the most recent filing for each (fy, fp) pair to avoid
        amendments doubling values.
        """
        # Deduplicate: keep latest accn (accession number) per (fy, fp).
        best: dict[tuple[int, str], dict] = {}
        for entry in units:
            fp = entry.get("fp", "")
            fy = entry.get("fy")
            if fp not in _FP_ORDER or fy is None:
                continue
            key = (int(fy), fp)
            if key not in best or entry.get("accn", "") > best[key].get("accn", ""):
                best[key] = entry

        # Group by fiscal year.
        by_fy: dict[int, dict[str, dict]] = {}
        for (fy, fp), entry in best.items():
            by_fy.setdefault(fy, {})[fp] = entry

        records: list[dict[str, Any]] = []
        for fy in sorted(by_fy):
            periods = by_fy[fy]
            q1_val  = float(periods["Q1"]["val"]) if "Q1" in periods else None
            q2_cum  = float(periods["Q2"]["val"]) if "Q2" in periods else None
            q3_cum  = float(periods["Q3"]["val"]) if "Q3" in periods else None
            fy_val  = float(periods["FY"]["val"]) if "FY" in periods else None

            if q1_val is not None and "Q1" in periods:
                records.append(self._capex_record(
                    periods["Q1"], fp="Q1", fy=fy, single=q1_val,
                    cik=cik, company=company, source_hash=source_hash,
                ))

            if q2_cum is not None and q1_val is not None and "Q2" in periods:
                records.append(self._capex_record(
                    periods["Q2"], fp="Q2", fy=fy, single=q2_cum - q1_val,
                    cik=cik, company=company, source_hash=source_hash,
                ))

            if q3_cum is not None and q2_cum is not None and "Q3" in periods:
                records.append(self._capex_record(
                    periods["Q3"], fp="Q3", fy=fy, single=q3_cum - q2_cum,
                    cik=cik, company=company, source_hash=source_hash,
                ))

            if fy_val is not None and q3_cum is not None and "FY" in periods:
                records.append(self._capex_record(
                    periods["FY"], fp="Q4", fy=fy, single=fy_val - q3_cum,
                    cik=cik, company=company, source_hash=source_hash,
                ))

        return records

    def _capex_record(
        self,
        entry: dict,
        *,
        fp: str,
        fy: int,
        single: float,
        cik: str,
        company: str,
        source_hash: str,
    ) -> dict[str, Any]:
        period_end = dt.date.fromisoformat(entry["end"])
        filing_form = "10-K" if fp == "Q4" else "10-Q"
        fiscal_quarter = f"{fy}Q{_FP_ORDER[entry['fp']] if entry['fp'] != 'FY' else 4}"
        if fp == "Q4":
            fiscal_quarter = f"{fy}Q4"
        return {
            "company":        company,
            "cik":            cik,
            "fiscal_quarter": fiscal_quarter,
            "period_end":     period_end,
            "capex_usd":      single,
            "capex_yoy_pct":  None,   # computed in storage layer after lookup
            "filing_form":    filing_form,
            "source":         self.name,
            "source_hash":    source_hash,
            "fetched_at":     dt.datetime.now(tz=__import__("zoneinfo").ZoneInfo("UTC")),
        }
