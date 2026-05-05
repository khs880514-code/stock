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
DEFAULT_CASH_KRW = 29_000_000


@dataclass(frozen=True)
class SeedUniverseResult:
    accounts_added: int
    cash_updated: bool
    holdings_added: int
    watchlist_added: int
    fundamentals_added: int


def seed_user_default_universe(config: AppConfig, today: date | None = None) -> SeedUniverseResult:
    today = today or date.today()
    account_count = _seed_accounts(config)
    cash_updated = _seed_cash(config)
    holding_count = _seed_holdings(config)
    watch_count = _seed_watchlist(config)
    fundamental_count = _seed_fundamentals(config, today)
    return SeedUniverseResult(
        accounts_added=account_count,
        cash_updated=cash_updated,
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


def _seed_cash(config: AppConfig) -> bool:
    store = PortfolioStore(config.db_path, config)
    current_cash = store.get_cash()
    if current_cash not in {0, 30_000_000}:
        return False
    store.set_cash(DEFAULT_CASH_KRW)
    return current_cash != DEFAULT_CASH_KRW


def _seed_holdings(config: AppConfig) -> int:
    store = PortfolioStore(config.db_path, config)
    existing = {item.ticker: item for item in store.load_holdings()}
    added = 0
    for item in _default_holdings(config.fx_usd_krw):
        current = existing.get(item.ticker)
        if current is not None and not _is_placeholder_holding(current):
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


def _is_placeholder_holding(item: Holding) -> bool:
    return item.quantity == 0 and item.avg_price == 0


def _default_holdings(fx_usd_krw: float) -> list[Holding]:
    return [
        _holding("AAPL", "GENERAL_TOSS", 11, 2_187_547, 4_541_132, "EQUITY", "BIG_TECH", fx_usd_krw),
        _holding("AMD", "GENERAL_TOSS", 5, 651_802, 2_560_177, "EQUITY", "AI_SEMICONDUCTOR", fx_usd_krw),
        _holding("MVST", "GENERAL_TOSS", 110, 4_364_234, 314_060, "EQUITY", "SPECULATIVE_LOSS", fx_usd_krw),
        _holding("SMH", "ISA_KIWOOM", 1, 745_445, 770_819, "ETF", "AI_SEMICONDUCTOR", fx_usd_krw),
        _holding("QQQ", "ISA_KIWOOM", 2, 1_965_663, 2_020_842, "ETF", "CORE_ETF", fx_usd_krw),
    ]


def _holding(
    ticker: str,
    account_key: str,
    quantity: float,
    cost_total_krw: float,
    current_total_krw: float,
    asset_type: str,
    sector_tag: str,
    fx_usd_krw: float,
) -> Holding:
    return Holding(
        ticker=ticker,
        account_key=account_key,
        market="US",
        quantity=quantity,
        avg_price=round(cost_total_krw / quantity / fx_usd_krw, 6),
        current_price=round(current_total_krw / quantity / fx_usd_krw, 6),
        currency="USD",
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
        ("MVST", "US", "SPECULATIVE_LOSS", 4, "Existing high-loss position to keep visible in review."),
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
