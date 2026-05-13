from uuid import uuid4

from engine.schemas import DailyNewsFile


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

