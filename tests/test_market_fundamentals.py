from __future__ import annotations

from datetime import date, timedelta

from app.config import AppConfig
from app.data.fundamentals_store import FundamentalSnapshot, FundamentalsStore
from app.data.market_fundamentals import update_market_fundamentals
from app.data.price_history import PriceHistoryStore
from app.models import PriceHistoryBar
from app.web_ui import handle_post


class FakeMarketClient:
    def summary(self, ticker: str) -> dict:
        assert ticker == "005930.KS"
        return {
            "longName": "Samsung Electronics Co., Ltd.",
            "financialCurrency": "KRW",
            "marketCap": 480_000_000_000_000,
            "trailingPE": 18.5,
            "forwardPE": 14.2,
            "priceToBook": 1.7,
            "priceToSalesTrailing12Months": 1.9,
            "enterpriseToEbitda": 7.1,
            "dividendYield": 0.021,
            "returnOnEquity": 0.118,
            "returnOnAssets": 0.071,
            "operatingMargins": 0.13,
            "profitMargins": 0.1,
            "revenueGrowth": 0.08,
            "earningsGrowth": 0.12,
            "debtToEquity": 32.5,
            "currentRatio": 2.1,
            "freeCashflow": 19_200_000_000_000,
        }


def test_market_fundamentals_merge_yfinance_summary_and_momentum(tmp_path):
    db_path = tmp_path / "market.sqlite3"
    store = FundamentalsStore(db_path)
    store.upsert(
        FundamentalSnapshot(
            ticker="005930.KS",
            market="KR",
            company_name="Samsung",
            sector_tag="AI_SEMICONDUCTOR",
            operating_income_growth_pct=46.0,
            source="opendart:fnlttSinglAcnt:2025:11011",
            notes="OpenDART note",
        )
    )
    _seed_prices(db_path, "005930.KS", date(2026, 5, 5))

    snapshot = update_market_fundamentals(
        db_path,
        "005930.KS",
        sector_tag="AI_SEMICONDUCTOR",
        today=date(2026, 5, 5),
        client=FakeMarketClient(),
        refresh_prices=False,
    )

    assert snapshot.market_cap_krw == 480_000_000_000_000
    assert snapshot.per == 18.5
    assert snapshot.forward_per == 14.2
    assert snapshot.pbr == 1.7
    assert snapshot.dividend_yield_pct == 2.1
    assert snapshot.roe_pct == 11.8
    assert snapshot.operating_margin_pct == 13.0
    assert snapshot.fcf_yield_pct == 4.0
    assert snapshot.price_momentum_3m_pct == 20.0
    assert snapshot.price_momentum_12m_pct == 50.0
    assert snapshot.operating_income_growth_pct == 46.0
    assert "opendart" in snapshot.source
    assert "yfinance:summary" in snapshot.source


def test_web_market_fundamental_post_uses_fetcher(tmp_path, monkeypatch):
    config = AppConfig(db_path=tmp_path / "web-market.sqlite3")

    def fake_update(db_path, ticker, sector_tag, fx_usd_krw, today):
        item = FundamentalSnapshot(
            ticker=ticker,
            market="KR",
            company_name="Fake Market Corp",
            sector_tag=sector_tag,
            per=10.0,
            source="yfinance:summary",
        )
        FundamentalsStore(db_path).upsert(item)
        return item

    monkeypatch.setattr("app.web.fundamental_screener.update_market_fundamentals", fake_update)
    notice, _ = handle_post(
        "/market-fundamental",
        config,
        {"ticker": "005930.KS", "sector_tag": "AI_SEMICONDUCTOR"},
    )

    assert "Market summary" in notice
    assert FundamentalsStore(config.db_path).get("005930.KS").per == 10.0


def test_market_summary_does_not_overwrite_manual_values(tmp_path):
    db_path = tmp_path / "market-manual.sqlite3"
    FundamentalsStore(db_path).upsert(
        FundamentalSnapshot(
            ticker="005930.KS",
            per=12.0,
            forward_per=11.0,
            source="manual",
        )
    )

    snapshot = update_market_fundamentals(
        db_path,
        "005930.KS",
        today=date(2026, 5, 5),
        client=FakeMarketClient(),
        refresh_prices=False,
    )

    assert snapshot.per == 12.0
    assert snapshot.forward_per == 11.0
    assert snapshot.pbr == 1.7


def _seed_prices(db_path, ticker: str, today: date) -> None:
    PriceHistoryStore(db_path).upsert_many(
        [
            PriceHistoryBar(ticker=ticker, date=today - timedelta(days=365), close=100, source="test"),
            PriceHistoryBar(ticker=ticker, date=today - timedelta(days=90), close=125, source="test"),
            PriceHistoryBar(ticker=ticker, date=today, close=150, source="test"),
        ]
    )
