from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from engine.schemas import (
    DailyNewsFile,
    DataConfidence,
    DataProvenance,
    KolDigestFile,
    ListingStatus,
)


def test_daily_news_schema_accepts_adr_002_example() -> None:
    payload = {
        "schema_version": "1.0",
        "date": "2026-05-13",
        "generated_at": "2026-05-13T06:30:00+08:00",
        "source_agents": ["eastmoney"],
        "items": [
            {
                "id": str(uuid4()),
                "title": "AI infrastructure chain sentiment improves",
                "summary": "Overnight US AI names traded higher.",
                "url": "https://example.com/news",
                "published_at": "2026-05-13T22:15:00-04:00",
                "source": "example",
                "tickers_mentioned": ["300308"],
                "sentiment": "positive",
                "category": "cn_ai_infra",
                "relevance_score": 0.95,
                "is_overnight_us": False,
            }
        ],
    }

    parsed = DailyNewsFile.model_validate(payload)

    assert parsed.schema_version == "1.0"
    assert parsed.items[0].tickers_mentioned == ["300308"]


def test_listing_status_enum_values() -> None:
    assert ListingStatus.TRADEABLE == "tradeable"
    assert ListingStatus.UNLISTED == "unlisted"
    assert ListingStatus.SUSPENDED == "suspended"


def test_data_provenance_defaults() -> None:
    prov = DataProvenance(source="中信证券")
    assert prov.confidence == DataConfidence.MEDIUM
    assert prov.as_of is None
    assert prov.fetched_at is None


def test_data_provenance_stale_confidence() -> None:
    prov = DataProvenance(
        source="华泰证券", as_of=date(2025, 1, 1), confidence=DataConfidence.STALE
    )
    assert prov.confidence == "stale"
    assert prov.as_of == date(2025, 1, 1)


def test_data_provenance_rejects_empty_source() -> None:
    with pytest.raises(ValidationError):
        DataProvenance(source="")


def test_kol_digest_file_accepts_valid_payload() -> None:
    payload = {
        "schema_version": "1.0",
        "date": "2026-05-13",
        "generated_at": "2026-05-13T08:00:00+08:00",
        "items": [
            {
                "author": "Trader韭",
                "platform": "微信公众号",
                "summary": "光模块板块本周走强，主要受益NVDA业绩超预期。",
                "tickers_mentioned": ["300308", "300502"],
                "sentiment": "positive",
                "published_at": "2026-05-13T10:00:00+08:00",
            }
        ],
    }

    parsed = KolDigestFile.model_validate(payload)

    assert parsed.date == date(2026, 5, 13)
    assert parsed.items[0].author == "Trader韭"
    assert parsed.items[0].sentiment == "positive"


def test_kol_digest_file_accepts_empty_items() -> None:
    payload = {
        "schema_version": "1.0",
        "date": "2026-05-13",
        "generated_at": "2026-05-13T08:00:00+08:00",
        "items": [],
    }
    parsed = KolDigestFile.model_validate(payload)
    assert parsed.items == []

