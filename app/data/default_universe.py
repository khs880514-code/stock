from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.config import AppConfig
from app.data.account_store import AccountStore, default_accounts
from app.data.fundamentals_store import FundamentalSnapshot, FundamentalsStore
from app.data.portfolio_store import PortfolioStore
from app.data.watchlist_store import WatchlistStore
from app.models import Holding


SEED_SOURCE = "seed:test-universe"
SEED_NOTE = "Synthetic test seed for screener verification; not a recommendation."


@dataclass(frozen=True)
class SeedUniverseResult:
    accounts_added: int
    holdings_added: int
    watchlist_added: int
    fundamentals_added: int


def seed_user_default_universe(config: AppConfig, today: date | None = None) -> SeedUniverseResult:
    today = today or date.today()
    account_count = _seed_accounts(config)
    holding_count = _seed_holdings(config)
    watch_count = _seed_watchlist(config)
    fundamental_count = _seed_fundamentals(config, today)
    return SeedUniverseResult(
        accounts_added=account_count,
        holdings_added=holding_count,
        watchlist_added=watch_count,
        fundamentals_added=fundamental_count,
    )


def _seed_accounts(config: AppConfig) -> int:
    store = AccountStore(config.db_path)
    added = 0
    for account in default_accounts():
        if store.get(account.account_key) is None:
            added += 1
        store.upsert(account)
    return added


def _seed_holdings(config: AppConfig) -> int:
    store = PortfolioStore(config.db_path, config)
    existing = {item.ticker for item in store.load_holdings()}
    added = 0
    for item in _default_holdings():
        if item.ticker in existing:
            continue
        store.save_holding(item)
        added += 1
    return added


def _seed_watchlist(config: AppConfig) -> int:
    store = WatchlistStore(config.db_path)
    added = 0
    for ticker, market, sector_tag, priority, reason in _default_watchlist():
        if store.get(ticker) is not None:
            continue
        store.add_or_update(ticker, market, reason, priority=priority, sector_tag=sector_tag)
        added += 1
    return added


def _seed_fundamentals(config: AppConfig, today: date) -> int:
    store = FundamentalsStore(config.db_path)
    added = 0
    for item in _default_fundamentals(today):
        if store.get(item.ticker) is not None:
            continue
        store.upsert(item)
        added += 1
    return added


def _default_holdings() -> list[Holding]:
    return [
        _holding("QQQ", "US", "USD", "ETF", "CORE_ETF"),
        _holding("SMH", "US", "USD", "ETF", "AI_SEMICONDUCTOR"),
        _holding("AAPL", "US", "USD", "EQUITY", "BIG_TECH"),
        _holding("AMD", "US", "USD", "EQUITY", "AI_SEMICONDUCTOR"),
    ]


def _holding(ticker: str, market: str, currency: str, asset_type: str, sector_tag: str) -> Holding:
    return Holding(
        ticker=ticker,
        account_key="GENERAL_TOSS",
        market=market,
        quantity=0.0,
        avg_price=0.0,
        current_price=0.0,
        currency=currency,
        asset_type=asset_type,
        sector_tag=sector_tag,
    )


def _default_watchlist() -> list[tuple[str, str, str, int, str]]:
    return [
        ("005930.KS", "KR", "AI_SEMICONDUCTOR", 1, "Default Korean candidate: Samsung Electronics."),
        ("000660.KS", "KR", "AI_SEMICONDUCTOR", 1, "Default Korean candidate: SK Hynix."),
        ("263750.KQ", "KR", "GAME_CONTENT", 2, "Default Korean candidate: Pearl Abyss."),
        ("QQQ", "US", "CORE_ETF", 2, "User default holding placeholder."),
        ("SMH", "US", "AI_SEMICONDUCTOR", 2, "User default holding placeholder."),
        ("AAPL", "US", "BIG_TECH", 2, "User default holding placeholder."),
        ("AMD", "US", "AI_SEMICONDUCTOR", 2, "User default holding placeholder."),
    ]


def _default_fundamentals(today: date) -> list[FundamentalSnapshot]:
    rows = [
        ("005930.KS", "KR", "Samsung Electronics", "AI_SEMICONDUCTOR", 14.0, 11.5, 1.4, 13.0, 12.0, 9.0, 30.0),
        ("000660.KS", "KR", "SK Hynix", "AI_SEMICONDUCTOR", 16.0, 9.0, 2.2, 18.0, 27.0, 18.0, 45.0),
        ("263750.KQ", "KR", "Pearl Abyss", "GAME_CONTENT", 21.0, 18.0, 2.8, 10.0, 12.0, 8.0, 20.0),
        ("AAPL", "US", "Apple", "BIG_TECH", 22.0, 19.0, 3.5, 32.0, 29.0, 6.0, 55.0),
        ("MSFT", "US", "Microsoft", "BIG_TECH", 24.0, 22.0, 3.8, 35.0, 41.0, 12.0, 65.0),
        ("NVDA", "US", "NVIDIA", "AI_SEMICONDUCTOR", 24.0, 21.0, 3.9, 42.0, 54.0, 35.0, 40.0),
        ("AMD", "US", "AMD", "AI_SEMICONDUCTOR", 23.0, 18.0, 3.2, 16.0, 18.0, 14.0, 35.0),
        ("GOOGL", "US", "Alphabet", "BIG_TECH", 20.0, 18.0, 3.0, 25.0, 31.0, 11.0, 10.0),
        ("ASML", "US", "ASML Holding", "SEMICONDUCTOR_EQUIPMENT", 24.0, 21.0, 3.7, 28.0, 30.0, 10.0, 30.0),
        ("TSM", "US", "Taiwan Semiconductor", "AI_SEMICONDUCTOR", 18.0, 15.0, 2.6, 26.0, 44.0, 16.0, 25.0),
    ]
    return [
        FundamentalSnapshot(
            ticker=ticker,
            market=market,
            company_name=name,
            sector_tag=sector_tag,
            as_of_date=today,
            currency="KRW" if market == "KR" else "USD",
            per=per,
            forward_per=forward_per,
            pbr=pbr,
            roe_pct=roe,
            operating_margin_pct=operating_margin,
            revenue_growth_pct=revenue_growth,
            debt_to_equity_pct=debt_to_equity,
            source=SEED_SOURCE,
            notes=SEED_NOTE,
        )
        for (
            ticker,
            market,
            name,
            sector_tag,
            per,
            forward_per,
            pbr,
            roe,
            operating_margin,
            revenue_growth,
            debt_to_equity,
        ) in rows
    ]
