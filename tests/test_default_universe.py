from __future__ import annotations

from datetime import date

from app.config import AppConfig
from app.data.default_universe import seed_user_default_universe
from app.data.fundamentals_store import FundamentalSnapshot, FundamentalsStore
from app.data.portfolio_store import PortfolioStore
from app.data.watchlist_store import WatchlistStore
from app.engines.stock_screener import screen
from app.models import Holding
from app.web_ui import handle_post, render_dashboard


def test_seed_user_default_universe_adds_holdings_watchlist_and_candidates(tmp_path):
    config = AppConfig(db_path=tmp_path / "seed.sqlite3")

    result = seed_user_default_universe(config, today=date(2026, 5, 5))

    assert result.cash_updated is True
    assert result.holdings_added == 5
    portfolio = PortfolioStore(config.db_path, config)
    holdings = {item.ticker: item for item in portfolio.load_holdings()}
    assert {"QQQ", "SMH", "AAPL", "AMD", "MVST"} <= set(holdings)
    assert portfolio.get_cash() == 29_000_000
    assert holdings["AAPL"].quantity == 11
    assert holdings["QQQ"].account_key == "ISA_KIWOOM"
    assert {"005930.KS", "000660.KS", "263750.KQ", "QQQ", "SMH", "AAPL", "AMD", "MVST"} <= {
        item.ticker for item in WatchlistStore(config.db_path).list_items()
    }
    candidates = screen(FundamentalsStore(config.db_path).list_all())
    assert len(candidates) >= 10
    assert sum(item.status == "TEST" for item in candidates) >= 10
    assert sum(item.status == "PASS" for item in candidates) == 0


def test_seed_user_default_universe_does_not_overwrite_existing_user_data(tmp_path):
    config = AppConfig(db_path=tmp_path / "seed-existing.sqlite3")
    portfolio = PortfolioStore(config.db_path, config)
    portfolio.set_cash(12_345_678)
    portfolio.save_holding(
        Holding(
            ticker="AAPL",
            account_key="GENERAL_TOSS",
            market="US",
            quantity=7,
            avg_price=123,
            current_price=150,
            currency="USD",
            asset_type="EQUITY",
            sector_tag="BIG_TECH",
        )
    )
    FundamentalsStore(config.db_path).upsert(
        FundamentalSnapshot(ticker="005930.KS", per=99.0, source="existing-user-data")
    )

    seed_user_default_universe(config, today=date(2026, 5, 5))

    saved_portfolio = PortfolioStore(config.db_path, config)
    assert saved_portfolio.get_cash() == 12_345_678
    assert saved_portfolio.load_holdings()[0].quantity == 7
    saved = FundamentalsStore(config.db_path).get("005930.KS")
    assert saved is not None
    assert saved.per == 99.0
    assert saved.source == "existing-user-data"


def test_seed_test_universe_web_flow(tmp_path):
    config = AppConfig(db_path=tmp_path / "seed-web.sqlite3")

    notice, _ = handle_post("/seed-test-universe", config, {})
    html = render_dashboard(config)

    assert "Default test universe seeded" in notice
    assert "Seed default test universe" in html
    assert "TEST" in html
    assert "263750.KQ" in html
    assert "QQQ" in html
