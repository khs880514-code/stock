from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


class Action(str, Enum):
    NO_TRADE = "NO_TRADE"
    HOLD = "HOLD"
    WATCH = "WATCH"
    SMALL_BUY_CANDIDATE = "SMALL_BUY_CANDIDATE"
    TRIM_CONSIDER = "TRIM_CONSIDER"
    SELL_CONSIDER = "SELL_CONSIDER"


class MistakeType(str, Enum):
    NONE = "NONE"
    FOMO_BUY = "FOMO_BUY"
    EARNINGS_CHASE = "EARNINGS_CHASE"
    OVERCONCENTRATION = "OVERCONCENTRATION"
    LOSS_AVERAGING = "LOSS_AVERAGING"
    MISSED_RISK = "MISSED_RISK"
    GOOD_NO_TRADE = "GOOD_NO_TRADE"


class DataQualityLabel(str, Enum):
    NOT_USED = "NOT_USED"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ConfidenceLabel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Source(BaseModel):
    title: str
    url: HttpUrl | str
    published_at: str = ""


class Holding(BaseModel):
    ticker: str
    market: Literal["US", "KR"] = "US"
    quantity: float
    avg_price: float
    current_price: float
    currency: Literal["USD", "KRW"] = "USD"
    asset_type: str = "EQUITY"
    sector_tag: str = "UNKNOWN"

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.upper().strip()


class PortfolioSnapshot(BaseModel):
    cash_krw: int
    holdings: list[Holding] = Field(default_factory=list)
    total_value_krw: int
    risk_tags: list[str] = Field(default_factory=list)


class PriceSnapshot(BaseModel):
    ticker: str
    current_price: float
    previous_close: float
    change_pct: float
    volume: int
    volume_avg_30d: int
    volume_ratio: float
    currency: Literal["USD", "KRW"] = "USD"
    timestamp: datetime

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.upper().strip()


class Event(BaseModel):
    ticker: str
    event_type: str
    event_time: datetime
    importance: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    source: Source | None = None

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.upper().strip()


class MacroIndicator(BaseModel):
    name: str
    value: float
    unit: str = ""
    previous_value: float | None = None
    change_pct: float | None = None
    moving_average_30d: float | None = None
    source: Source | None = None


class MacroSnapshot(BaseModel):
    timestamp: datetime
    indicators: dict[str, MacroIndicator]

    def get(self, key: str) -> MacroIndicator | None:
        return self.indicators.get(key)


class DataQuality(BaseModel):
    price_data: DataQualityLabel = DataQualityLabel.MEDIUM
    portfolio_data: DataQualityLabel = DataQualityLabel.MEDIUM
    event_data: DataQualityLabel = DataQualityLabel.MEDIUM
    news_context: DataQualityLabel = DataQualityLabel.NOT_USED
    sentiment_data: DataQualityLabel = DataQualityLabel.NOT_USED


class LlmAssist(BaseModel):
    ticker: str = ""
    reason: list[str] = Field(default_factory=list)
    bear_case: list[str] = Field(default_factory=list)
    do_not_buy_if: list[str] = Field(default_factory=list)
    next_check: str = ""
    confidence_label: ConfidenceLabel = ConfidenceLabel.MEDIUM
    data_quality: DataQuality = Field(default_factory=DataQuality)
    sources: list[Source] = Field(default_factory=list)


class AlertDecision(BaseModel):
    ticker: str
    action: Action
    max_amount_krw: int = 0
    reason: list[str] = Field(default_factory=list)
    bear_case: list[str] = Field(default_factory=list)
    do_not_buy_if: list[str] = Field(default_factory=list)
    next_check: str = ""
    confidence_label: ConfidenceLabel = ConfidenceLabel.MEDIUM
    data_quality: DataQuality = Field(default_factory=DataQuality)
    requires_user_decision: bool = True
    rule_engine_decision: bool = True
    llm_assisted_fields: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    post_drop_context: PostDropContext | None = None


class BuyReviewRequest(BaseModel):
    ticker: str
    market: Literal["US", "KR"] = "US"
    desired_amount_krw: int
    reason_text: str
    fomo_score: int = Field(ge=0, le=10)
    friend_influence_score: int = Field(ge=0, le=10)
    price_type: str = "limit"

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.upper().strip()


class TradeEntry(BaseModel):
    id: int | None = None
    timestamp: datetime
    ticker: str
    action: str
    quantity: float
    avg_price: float
    reason_text: str
    fomo_score: int = Field(ge=0, le=10)
    friend_influence_score: int = Field(ge=0, le=10)
    price_at_entry: float
    price_1d: float | None = None
    price_1w: float | None = None
    price_1m: float | None = None
    outcome_note: str = ""
    mistake_type: MistakeType = MistakeType.NONE

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.upper().strip()


class CollectionLog(BaseModel):
    source_name: str
    collected_at: datetime
    ok: bool
    message: str = ""


class MacroTrigger(BaseModel):
    trigger_type: str
    title: str
    observed_value: float
    reason: str
    source: Source | None = None
    occurred_at: datetime


class PriceHistoryBar(BaseModel):
    ticker: str
    date: date
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float
    volume: int | None = None
    source: str = "manual"

    @field_validator("ticker")
    @classmethod
    def normalize_history_ticker(cls, value: str) -> str:
        return value.upper().strip()


class PostDropContext(BaseModel):
    triggered: bool
    drop_pct: float | None = None
    drop_start_date: date | None = None
    drop_end_date: date | None = None
    is_earnings_linked: bool = False
    earnings_date: date | None = None
    severity: Literal["medium", "high"] | None = None
    bypass_reason: str | None = None
    action: Literal["block", "warn", "pass"] = "pass"
    cap_ratio: float | None = None
    explanation: str | None = None
