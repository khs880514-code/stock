from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import os
from pathlib import Path

from app.data.earnings_calendar_store import EarningsCalendarStore
from app.data.filings_collector import FilingStore
from app.data.news_store import NewsStore
from app.data.price_history import PriceHistoryStore
from app.data.research_notes_store import ResearchNotesStore


@dataclass(frozen=True)
class TickerDataStatus:
    ticker: str
    latest_price_date: str
    latest_news_at: str
    latest_filing_date: str
    next_earnings_date: str
    research_note_count: int
    freshness_label: str


@dataclass(frozen=True)
class ApiReadinessStatus:
    name: str
    status: str
    next_step: str


def build_ticker_data_status(db_path: Path | str, tickers: list[str], today: date) -> list[TickerDataStatus]:
    price_store = PriceHistoryStore(db_path)
    news_store = NewsStore(db_path)
    filing_store = FilingStore(db_path)
    earnings_store = EarningsCalendarStore(db_path)
    research_store = ResearchNotesStore(db_path)
    statuses: list[TickerDataStatus] = []
    for ticker in sorted({ticker.upper() for ticker in tickers if ticker.strip()}):
        latest_price = price_store.latest_bar(ticker)
        latest_news = news_store.latest(ticker, limit=1)
        latest_filing = filing_store.latest(ticker, limit=1)
        upcoming_earnings = earnings_store.upcoming([ticker], today, days=90)
        research_notes = research_store.latest(ticker, limit=20)
        statuses.append(
            TickerDataStatus(
                ticker=ticker,
                latest_price_date=latest_price.date.isoformat() if latest_price else "",
                latest_news_at=_short_datetime(latest_news[0].collected_at) if latest_news else "",
                latest_filing_date=latest_filing[0].filing_date if latest_filing else "",
                next_earnings_date=upcoming_earnings[0].earnings_date.isoformat() if upcoming_earnings else "",
                research_note_count=len(research_notes),
                freshness_label=_freshness_label(
                    today=today,
                    latest_price_date=latest_price.date if latest_price else None,
                    has_earnings=bool(upcoming_earnings),
                    has_news=bool(latest_news),
                    has_filing=bool(latest_filing),
                ),
            )
        )
    return statuses


def build_api_readiness_status() -> list[ApiReadinessStatus]:
    return [
        ApiReadinessStatus("가격/시장요약", "연결됨", "yfinance/Yahoo chart와 market summary로 가격, PER/PBR, 시총, 모멘텀 보강"),
        ApiReadinessStatus("뉴스", "부분 연결", "현재 Google News RSS 사용. 내일 별도 뉴스 API가 있으면 추가 가능"),
        ApiReadinessStatus("SEC 공시", _env_status("SEF_SEC_USER_AGENT"), "연락 가능한 User-Agent 설정 후 라이브 수집 사용"),
        ApiReadinessStatus("실적 캘린더", _env_status("SEF_ALPHA_VANTAGE_API_KEY"), "API key가 있으면 자동 실적 일정 수집기 연결"),
        ApiReadinessStatus("거시지표", _env_status("SEF_FRED_API_KEY"), "FRED/ECOS 키 확인 후 매크로 수집기 연결"),
        ApiReadinessStatus("국내 공시", _env_status("SEF_DART_API_KEY"), "OpenDART 단일회사 주요계정 수집기 연결됨"),
        ApiReadinessStatus("브로커 동기화", "N/A", "자동 동기화 사용 안 함. 토스/키움 포트폴리오는 수동 입력 유지"),
    ]


def _env_status(name: str) -> str:
    return "준비됨" if os.getenv(name) else "내일 연결"


def _short_datetime(value: str) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value).strftime("%Y-%m-%d")
    except ValueError:
        return value[:10]


def _freshness_label(
    today: date,
    latest_price_date: date | None,
    has_earnings: bool,
    has_news: bool,
    has_filing: bool,
) -> str:
    missing = [not latest_price_date, not has_news, not has_filing, not has_earnings]
    if all(missing):
        return "비어 있음"
    if latest_price_date and (today - latest_price_date).days <= 7 and has_news and has_filing and has_earnings:
        return "좋음"
    if latest_price_date and (today - latest_price_date).days <= 14:
        return "보통"
    return "보강 필요"
