from datetime import date

from app.config import AppConfig
from app.data.fundamentals_store import FundamentalSnapshot, FundamentalsStore
from app.data.review_universe import ReviewUniverseResult, collect_review_universe
from app.web.fundamental_screener import handle_auto_candidates_post


def test_collect_review_universe_updates_requested_candidates(tmp_path, monkeypatch):
    config = AppConfig(db_path=tmp_path / "review-universe.sqlite3")
    updated: list[str] = []

    def fake_update(db_path, ticker, sector_tag, fx_usd_krw, today):
        updated.append(ticker)
        item = FundamentalSnapshot(ticker=ticker, sector_tag=sector_tag, per=12, pbr=1.5, source="yfinance:summary")
        FundamentalsStore(db_path).upsert(item)
        return item

    monkeypatch.setattr("app.data.review_universe.update_market_fundamentals", fake_update)
    monkeypatch.setattr("app.data.review_universe.GoogleNewsRssCollector.collect", lambda self, tickers: [])

    result = collect_review_universe(config, count=10, today=date(2026, 5, 6))

    assert result.requested == 10
    assert result.fundamentals_updated == 10
    assert len(updated) == 10
    assert FundamentalsStore(config.db_path).get("005930.KS") is not None


def test_auto_candidates_web_handler_reports_result(tmp_path, monkeypatch):
    config = AppConfig(db_path=tmp_path / "review-web.sqlite3")

    monkeypatch.setattr(
        "app.web.fundamental_screener.collect_review_universe",
        lambda config, count, today: ReviewUniverseResult(
            requested=count,
            fundamentals_updated=18,
            news_added=42,
            failed=["TSLA"],
        ),
    )

    notice = handle_auto_candidates_post(config, {"candidate_count": "20"})

    assert "오늘 후보 자동 수집 완료" in notice
    assert "시장정보 18개" in notice
    assert "뉴스 42개" in notice
    assert "TSLA" in notice
