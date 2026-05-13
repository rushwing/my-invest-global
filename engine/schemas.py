"""Pydantic models for the ADR-002 file contracts."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

SchemaVersion = Literal["1.0"]


class Sentiment(StrEnum):
    """Normalized sentiment labels accepted from agent files."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class NewsCategory(StrEnum):
    """ADR-002 daily news category enum."""

    US_AI_INFRA = "us_ai_infra"
    CN_AI_INFRA = "cn_ai_infra"
    CN_POLICY = "cn_policy"
    MACRO = "macro"
    SECTOR_OTHER = "sector_other"


class HoldingCategory(StrEnum):
    """Portfolio bucket enum from ADR-002/ADR-003."""

    WHITE_HORSE = "白马股"
    ELASTIC = "弹性股"


class DailyNewsItem(BaseModel):
    """One normalized news item produced by an external data agent."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    url: HttpUrl
    published_at: datetime
    source: str = Field(min_length=1)
    tickers_mentioned: list[str] = Field(default_factory=list)
    sentiment: Sentiment
    category: NewsCategory
    relevance_score: float = Field(ge=0, le=1)
    is_overnight_us: bool = False


class DailyNewsFile(BaseModel):
    """daily_news_{YYYYMMDD}.json."""

    model_config = ConfigDict(extra="forbid")

    schema_version: SchemaVersion
    date: date
    generated_at: datetime
    source_agents: list[str] = Field(min_length=1)
    items: list[DailyNewsItem] = Field(default_factory=list)


class IndustryReport(BaseModel):
    """One sell-side or industry report summary."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    source: str = Field(min_length=1)
    key_points: list[str] = Field(default_factory=list)
    affected_tickers: list[str] = Field(default_factory=list)
    sentiment: Sentiment


class KolDigest(BaseModel):
    """One KOL digest entry from ADR-002 weekly report files."""

    model_config = ConfigDict(extra="forbid")

    author: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    tickers_mentioned: list[str] = Field(default_factory=list)
    sentiment: Sentiment
    published_at: datetime


class WeeklyReportFile(BaseModel):
    """weekly_report_{YYYYWW}.json."""

    model_config = ConfigDict(extra="forbid")

    schema_version: SchemaVersion
    week: str = Field(pattern=r"^\d{6}$")
    date_range: tuple[date, date]
    generated_at: datetime
    industry_reports: list[IndustryReport] = Field(default_factory=list)
    kol_digests: list[KolDigest] = Field(default_factory=list)

    @field_validator("date_range")
    @classmethod
    def validate_date_range(cls, value: tuple[date, date]) -> tuple[date, date]:
        if value[0] > value[1]:
            msg = "date_range start must be on or before end"
            raise ValueError(msg)
        return value


class HoldingRow(BaseModel):
    """One row from holdings_{YYYYMMDD}.csv."""

    model_config = ConfigDict(extra="forbid")

    schema_version: SchemaVersion
    date: date
    code: str = Field(pattern=r"^\d{6}$")
    name: str = Field(min_length=1)
    cost_price: float = Field(ge=0)
    current_price: float = Field(ge=0)
    quantity: int = Field(ge=0)
    market_value: float = Field(ge=0)
    pnl_pct: str
    pnl_amount: float
    category: HoldingCategory
    sector: str = Field(min_length=1)
    notes: str = ""


class PortfolioSummary(BaseModel):
    """Summary section in processed/signals_{YYYYMMDD}.json."""

    model_config = ConfigDict(extra="forbid")

    total_market_value: float = Field(ge=0)
    white_horse_ratio: float = Field(ge=0, le=1)
    elastic_ratio: float = Field(ge=0, le=1)
    target_white_horse: float = Field(ge=0, le=1)
    target_elastic: float = Field(ge=0, le=1)
    rebalance_needed: bool


class StockSignal(BaseModel):
    """One stock signal emitted by the analysis engine."""

    model_config = ConfigDict(extra="allow")

    code: str = Field(pattern=r"^\d{6}$")
    name: str = Field(min_length=1)
    category: HoldingCategory
    technical_score: float = Field(ge=0, le=100)
    fundamental_score: float = Field(ge=0, le=100)
    sentiment_score: float = Field(ge=0, le=100)
    composite_score: float = Field(ge=0, le=100)
    action: str = Field(min_length=1)
    action_code: Literal[
        "strong_add",
        "hold_add",
        "hold",
        "reduce",
        "stop_loss",
        "take_profit_alert",
    ]
    signals: dict[str, object] = Field(default_factory=dict)


class SignalsFile(BaseModel):
    """processed/signals_{YYYYMMDD}.json."""

    model_config = ConfigDict(extra="forbid")

    schema_version: SchemaVersion
    date: date
    generated_at: datetime
    portfolio_summary: PortfolioSummary
    stock_signals: list[StockSignal] = Field(default_factory=list)

