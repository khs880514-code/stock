import os
from datetime import date

from app.config import load_env_file
from app.data.data_status import build_api_readiness_status, build_ticker_data_status
from app.data.earnings_calendar_store import EarningsCalendarStore, EarningsDate
from app.data.filings_collector import FilingItem, FilingStore
from app.data.news_store import NewsHeadline, NewsStore
from app.data.price_history import PriceHistoryStore
from app.data.research_notes_store import ResearchNote, ResearchNotesStore
from app.models import PriceHistoryBar, Source


def test_ticker_data_status_summarizes_local_sources(tmp_path):
    db_path = tmp_path / "status.sqlite3"
    PriceHistoryStore(db_path).upsert_many(
        [PriceHistoryBar(ticker="AMD", date=date(2026, 5, 1), close=100, source="manual")]
    )
    NewsStore(db_path).upsert_many(
        [
            NewsHeadline(
                ticker="AMD",
                title="AMD headline",
                url="https://example.com/news",
                source_name="Example",
                published_at="2026-05-01",
                collected_at="2026-05-02T00:00:00+09:00",
            )
        ]
    )
    FilingStore(db_path).upsert_many(
        [
            FilingItem(
                ticker="AMD",
                filing_type="8-K",
                title="Current report",
                source=Source(title="SEC EDGAR 8-K", url="https://example.com/filing"),
                cik="0000002488",
                accession_number="0000002488-26-000001",
                filing_date="2026-05-01",
                collected_at="2026-05-02T00:00:00+09:00",
            )
        ]
    )
    EarningsCalendarStore(db_path).upsert(
        EarningsDate(ticker="AMD", earnings_date=date(2026, 5, 5), source="AMD IR")
    )
    ResearchNotesStore(db_path).add(
        ResearchNote(
            tickers=["AMD"],
            source_type="NOTEBOOKLM",
            source_name="김지윤의 지식플레이",
            source_url="https://example.com",
            reliability="HIGH",
            summary="요약",
        )
    )
    status = build_ticker_data_status(db_path, ["AMD"], today=date(2026, 5, 3))[0]
    assert status.latest_price_date == "2026-05-01"
    assert status.latest_news_at == "2026-05-02"
    assert status.latest_filing_date == "2026-05-01"
    assert status.next_earnings_date == "2026-05-05"
    assert status.research_note_count == 1
    assert status.freshness_label == "좋음"


def test_api_readiness_marks_unset_keys_as_tomorrow(monkeypatch):
    monkeypatch.delenv("SEF_ALPHA_VANTAGE_API_KEY", raising=False)
    statuses = {item.name: item.status for item in build_api_readiness_status()}
    assert statuses["실적 캘린더"] == "내일 연결"


def test_load_env_file_sets_sef_keys(tmp_path, monkeypatch):
    monkeypatch.delenv("SEF_DART_API_KEY", raising=False)
    monkeypatch.delenv("SEF_SEC_USER_AGENT", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text(
        "SEF_DART_API_KEY=test-dart\nSEF_SEC_USER_AGENT=StockExpertFriend/1.0 test@example.com\n",
        encoding="utf-8",
    )

    load_env_file(env_path)

    assert os.environ["SEF_DART_API_KEY"] == "test-dart"
    assert os.environ["SEF_SEC_USER_AGENT"] == "StockExpertFriend/1.0 test@example.com"
