"""Static SEC CIK map for Big-4 cloud CapEx companies (BP-2 — avoid repeat discovery)."""

from __future__ import annotations

# 10-digit zero-padded CIKs — avoids repeated CIK discovery requests.
SEC_CIK_MAP: dict[str, str] = {
    "MSFT":  "0000789019",
    "AMZN":  "0001018724",
    "GOOGL": "0001652044",
    "META":  "0001326801",
}

# Maps Group-L indicator_id suffix (e.g. "MSFT_CAPEX") to ticker (e.g. "MSFT").
_CAPEX_TICKER: dict[str, str] = {
    "MSFT_CAPEX":  "MSFT",
    "AMZN_CAPEX":  "AMZN",
    "GOOGL_CAPEX": "GOOGL",
    "META_CAPEX":  "META",
}


def cik_for_indicator(indicator_id: str) -> tuple[str, str]:
    """Return (cik, ticker) for a Group-L indicator_id like 'MSFT_CAPEX'.

    Falls back to (indicator_id, indicator_id) if not in map.
    """
    ticker = _CAPEX_TICKER.get(indicator_id, indicator_id)
    cik = SEC_CIK_MAP.get(ticker, ticker)
    return cik, ticker
