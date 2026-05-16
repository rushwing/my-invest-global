"""
Tests for SECEdgarSource — covers TC-006-03 through TC-006-07.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from engine.data_agent.rate_limiter import RateLimiter
from engine.shared.sources.sec_edgar import SECEdgarSource

_CIK = "0000789019"

# Minimal fixture: one Q1 record only
_FIXTURE_Q1_ONLY = {
    "facts": {
        "us-gaap": {
            "PaymentsToAcquirePropertyPlantAndEquipment": {
                "units": {
                    "USD": [
                        {
                            "end": "2025-03-31",
                            "val": 3_000_000_000,
                            "form": "10-Q",
                            "fp": "Q1",
                            "fy": 2025,
                            "accn": "0000789019-25-000001",
                        }
                    ]
                }
            }
        }
    }
}

# Fixture: Q1 + Q2 cumulative (10-Q de-cumulation)
_FIXTURE_Q1_Q2 = {
    "facts": {
        "us-gaap": {
            "PaymentsToAcquirePropertyPlantAndEquipment": {
                "units": {
                    "USD": [
                        {
                            "end": "2025-03-31",
                            "val": 3_000_000_000,
                            "form": "10-Q",
                            "fp": "Q1",
                            "fy": 2025,
                            "accn": "0000789019-25-000001",
                        },
                        {
                            "end": "2025-06-30",
                            "val": 7_000_000_000,
                            "form": "10-Q",
                            "fp": "Q2",
                            "fy": 2025,
                            "accn": "0000789019-25-000002",
                        },
                    ]
                }
            }
        }
    }
}

# Fixture: Q1 + Q2 + Q3 + FY (full-year, 10-K Q4 de-cumulation)
_FIXTURE_FULL_YEAR = {
    "facts": {
        "us-gaap": {
            "PaymentsToAcquirePropertyPlantAndEquipment": {
                "units": {
                    "USD": [
                        {
                            "end": "2025-03-31",
                            "val": 3_000_000_000,
                            "form": "10-Q",
                            "fp": "Q1",
                            "fy": 2025,
                            "accn": "0000789019-25-000001",
                        },
                        {
                            "end": "2025-06-30",
                            "val": 7_000_000_000,
                            "form": "10-Q",
                            "fp": "Q2",
                            "fy": 2025,
                            "accn": "0000789019-25-000002",
                        },
                        {
                            "end": "2025-09-30",
                            "val": 10_500_000_000,
                            "form": "10-Q",
                            "fp": "Q3",
                            "fy": 2025,
                            "accn": "0000789019-25-000003",
                        },
                        {
                            "end": "2025-12-31",
                            "val": 14_000_000_000,
                            "form": "10-K",
                            "fp": "FY",
                            "fy": 2025,
                            "accn": "0000789019-26-000001",
                        },
                    ]
                }
            }
        }
    }
}


@pytest.fixture()
def src() -> SECEdgarSource:
    return SECEdgarSource(RateLimiter())


# TC-006-03: URL must contain CIK{cik} prefix
def test_url_contains_cik_prefix(src: SECEdgarSource) -> None:
    captured_url: list[str] = []

    def fake_get(url: str, **kwargs):  # type: ignore[override]
        captured_url.append(url)
        return _FIXTURE_Q1_ONLY

    with patch.object(src, "_get", side_effect=fake_get):
        src.fetch_capex_quarterly(_CIK)

    assert captured_url, "expected _get to be called"
    url = captured_url[0]
    assert f"CIK{_CIK}" in url, f"URL should contain 'CIK{_CIK}', got: {url}"
    assert f"/{_CIK}.json" not in url, f"URL must not use bare CIK path: {url}"


# TC-006-04: User-Agent contains compliance email
def test_user_agent_contains_compliance_email(src: SECEdgarSource) -> None:
    ua = src._session.headers["User-Agent"]
    assert "my-invest-global ruoxu.wang@gmail.com" in ua


# TC-006-05: Q2 single = Q2_cum - Q1 (10-Q de-cumulation)
def test_q2_decumulation(src: SECEdgarSource) -> None:
    with patch.object(src, "_get", return_value=_FIXTURE_Q1_Q2):
        records = src.fetch_capex_quarterly(_CIK)

    q2_records = [r for r in records if "Q2" in r["fiscal_quarter"]]
    assert q2_records, "expected a Q2 record"
    q2 = q2_records[0]
    assert q2["capex_usd"] == pytest.approx(4.0e9), (
        f"Q2 single should be 4B (7B-3B), got {q2['capex_usd']}"
    )
    assert q2["filing_form"] == "10-Q"
    assert q2["fiscal_quarter"] == "2025Q2"


# TC-006-06: Q4 single = FY - Q3_cum (10-K; must not be FY directly)
def test_q4_decumulation_from_10k(src: SECEdgarSource) -> None:
    with patch.object(src, "_get", return_value=_FIXTURE_FULL_YEAR):
        records = src.fetch_capex_quarterly(_CIK)

    q4_records = [r for r in records if "Q4" in r["fiscal_quarter"]]
    assert q4_records, "expected a Q4 record"
    q4 = q4_records[0]
    assert q4["capex_usd"] == pytest.approx(3.5e9), (
        f"Q4 single should be 3.5B (14B-10.5B), got {q4['capex_usd']}"
    )
    assert q4["filing_form"] == "10-K"


# TC-006-11: _rotate_ua() must re-apply SEC-compliant UA, not a browser UA
def test_rotate_ua_preserves_sec_compliance(src: SECEdgarSource) -> None:
    src._rotate_ua()  # simulates base-class retry path
    ua = src._session.headers["User-Agent"]
    assert "my-invest-global ruoxu.wang@gmail.com" in ua, (
        f"UA after _rotate_ua() should remain SEC-compliant, got: {ua}"
    )


# TC-006-07: source_hash is a valid 64-char lowercase hex SHA-256
def test_source_hash_is_sha256(src: SECEdgarSource) -> None:
    with patch.object(src, "_get", return_value=_FIXTURE_Q1_ONLY):
        records = src.fetch_capex_quarterly(_CIK)

    assert records, "expected at least one record"
    source_hash = records[0]["source_hash"]
    assert len(source_hash) == 64
    assert source_hash.islower()
    assert all(c in "0123456789abcdef" for c in source_hash)

    # Determinism: same fixture → same hash
    with patch.object(src, "_get", return_value=_FIXTURE_Q1_ONLY):
        records2 = src.fetch_capex_quarterly(_CIK)
    assert records2[0]["source_hash"] == source_hash
