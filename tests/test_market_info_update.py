from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import AppConfig
from app.data.account_store import AccountStore, default_accounts
from app.data.earnings_calendar_store import EarningsCalendarStore, EarningsDate
from app.data.filings_collector import FilingItem, FilingStore
from app.data.news_store import NewsHeadline, NewsStore
from app.data.portfolio_store import PortfolioStore
from app.data.price_history import PriceHistoryStore
from app.data.research_notes_store import ResearchNote, ResearchNotesStore
from app.models import PriceHistoryBar, Source
from app.web_ui import _latest_prices, handle_post


def test_latest_price_panel_reads_cached_history(tmp_path):
    config = AppConfig(db_path=tmp_path / "info.sqlite3")
    store = PriceHistoryStore(config.db_path)
    store.upsert_many(
        [
            PriceHistoryBar(ticker="AAPL", date=date(2026, 1, 2), close=180, source="manual"),
            PriceHistoryBar(ticker="AAPL", date=date(2026, 1, 3), close=181, source="manual"),
        ]
    )
    items = _latest_prices(config, holdings=[], watch_items=[type("Watch", (), {"ticker": "AAPL"})()])
    assert items[0]["ticker"] == "AAPL"
    assert items[0]["close"] == 181


def test_news_store_upserts_and_lists(tmp_path):
    store = NewsStore(tmp_path / "info.sqlite3")
    store.upsert_many(
        [
            NewsHeadline(
                ticker="AMD",
                title="AMD headline",
                url="https://example.com/amd",
                source_name="Example",
                published_at="2026-01-01",
                collected_at="2026-01-02T00:00:00+09:00",
            )
        ]
    )
    latest = store.latest("AMD")
    assert len(latest) == 1
    assert latest[0].title == "AMD headline"


def test_buy_check_message_includes_cached_recent_context(tmp_path):
    config = AppConfig(db_path=tmp_path / "info.sqlite3")
    PortfolioStore(config.db_path, config).set_cash(20_000_000)
    account_store = AccountStore(config.db_path)
    for account in default_accounts():
        account_store.upsert(account)
    PriceHistoryStore(config.db_path).upsert_many(
        [PriceHistoryBar(ticker="MSFT", date=date(2026, 5, 1), close=410, source="manual")]
    )
    NewsStore(config.db_path).upsert_many(
        [
            NewsHeadline(
                ticker="MSFT",
                title="MSFT shares surge after analyst price target upgrade",
                url="https://example.com/msft",
                source_name="Example",
                published_at="2026-05-01",
                collected_at="2026-05-02T00:00:00+09:00",
            )
        ]
    )
    FilingStore(config.db_path).upsert_many(
        [
            FilingItem(
                ticker="MSFT",
                filing_type="8-K",
                title="Current report",
                source=Source(
                    title="SEC EDGAR 8-K",
                    url="https://www.sec.gov/Archives/edgar/data/789019/example/msft.htm",
                    published_at="2026-05-01",
                ),
                cik="0000789019",
                accession_number="0000789019-26-000001",
                filing_date="2026-05-01",
                primary_document="msft.htm",
                collected_at="2026-05-02T00:00:00+09:00",
            )
        ]
    )
    ResearchNotesStore(config.db_path).add(
        ResearchNote(
            tickers=["MSFT"],
            source_type="NOTEBOOKLM",
            source_name="김지윤의 지식플레이",
            source_url="https://example.com/research",
            reliability="HIGH",
            summary="거시 리스크 요약. 매수 결정은 별도 확인 필요.",
            counter_points="영상 요약이 과장됐을 수 있음",
            check_questions="원문 날짜와 종목 관련성이 맞나?",
        )
    )
    notice, message = handle_post(
        "/buy-check",
        config,
        {
            "ticker": "MSFT",
            "amount_krw": "1000000",
            "account_key": "ISA_KIWOOM",
            "reason": "분할 매수 후보 검토",
            "fomo": "3",
            "influence": "2",
            "price_type": "limit",
        },
    )
    assert notice == "매수 검토 완료"
    assert "[최근 정보]" in message
    assert "최근 가격" in message
    assert "뉴스 플래그" in message
    assert "애널리스트/목표가" in message
    assert "최근 SEC 공시" in message
    assert "8-K" in message
    assert "외부 리서치 노트" in message
    assert "김지윤의 지식플레이" in message
    assert "반대근거" in message
    assert "확인질문" in message
    assert "데이터 상태" in message
    assert "키움증권" in message
    assert "ISA_KIWOOM" in message


def test_buy_check_uses_stored_earnings_calendar(tmp_path):
    config = AppConfig(db_path=tmp_path / "info.sqlite3")
    PortfolioStore(config.db_path, config).set_cash(20_000_000)
    tomorrow = datetime.now(tz=ZoneInfo("Asia/Seoul")).date() + timedelta(days=1)
    EarningsCalendarStore(config.db_path).upsert(
        EarningsDate(
            ticker="NVDA",
            earnings_date=tomorrow,
            source="NVIDIA IR",
            source_url="https://investor.nvidia.com/",
            note="테스트 일정",
        )
    )
    notice, message = handle_post(
        "/buy-check",
        config,
        {
            "ticker": "NVDA",
            "amount_krw": "1000000",
            "reason": "실적 전 확인",
            "fomo": "3",
            "influence": "1",
            "price_type": "limit",
        },
    )
    assert notice == "매수 검토 완료"
    assert "NO_TRADE" in message
    assert "실적 발표" in message
