from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.config import AppConfig
from app.db.database import connect, init_db
from app.models import Holding, PortfolioSnapshot


KST = ZoneInfo("Asia/Seoul")


def holding_value_krw(holding: Holding, fx_usd_krw: float) -> float:
    multiplier = fx_usd_krw if holding.currency == "USD" else 1.0
    return holding.quantity * holding.current_price * multiplier


class PortfolioStore:
    def __init__(self, db_path: Path | str, config: AppConfig) -> None:
        self.db_path = Path(db_path)
        self.config = config
        init_db(self.db_path)

    def set_cash(self, cash_krw: int) -> None:
        now = datetime.now(tz=KST).isoformat()
        with connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO portfolio_meta (key, value, updated_at)
                VALUES ('cash_krw', ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
                """,
                (str(cash_krw), now),
            )

    def get_cash(self) -> int:
        with connect(self.db_path) as conn:
            row = conn.execute("SELECT value FROM portfolio_meta WHERE key = 'cash_krw'").fetchone()
        return int(row["value"]) if row else 0

    def save_holding(self, holding: Holding) -> None:
        now = datetime.now(tz=KST).isoformat()
        with connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO holdings (
                  ticker, account_key, market, quantity, avg_price, current_price, currency, asset_type,
                  sector_tag, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker) DO UPDATE SET
                  account_key=excluded.account_key,
                  market=excluded.market,
                  quantity=excluded.quantity,
                  avg_price=excluded.avg_price,
                  current_price=excluded.current_price,
                  currency=excluded.currency,
                  asset_type=excluded.asset_type,
                  sector_tag=excluded.sector_tag,
                  updated_at=excluded.updated_at
                """,
                (
                    holding.ticker,
                    holding.account_key,
                    holding.market,
                    holding.quantity,
                    holding.avg_price,
                    holding.current_price,
                    holding.currency,
                    holding.asset_type,
                    holding.sector_tag,
                    now,
                ),
            )

    def delete_holding(self, ticker: str) -> bool:
        with connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM holdings WHERE ticker = ?", (ticker.upper().strip(),))
            return cursor.rowcount > 0

    def load_holdings(self) -> list[Holding]:
        with connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT ticker, account_key, market, quantity, avg_price, current_price, currency, asset_type, sector_tag
                FROM holdings
                ORDER BY ticker
                """
            ).fetchall()
        return [Holding(**dict(row)) for row in rows]

    def snapshot(self) -> PortfolioSnapshot:
        holdings = self.load_holdings()
        cash = self.get_cash()
        holdings_value = sum(holding_value_krw(item, self.config.fx_usd_krw) for item in holdings)
        total_value = int(cash + holdings_value)
        risk_tags = _risk_tags(holdings, total_value, self.config.fx_usd_krw)
        return PortfolioSnapshot(
            cash_krw=cash,
            holdings=holdings,
            total_value_krw=total_value,
            risk_tags=risk_tags,
        )

    def save_snapshot(self, trade_id: int | None = None) -> int:
        holdings = self.load_holdings()
        if not holdings:
            return 0
        now = datetime.now(tz=KST).isoformat()
        with connect(self.db_path) as conn:
            conn.executemany(
                """
                INSERT INTO holdings_snapshot (
                  taken_at, trade_id, ticker, account_key, shares, avg_cost_usd, fx_usdkrw
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        now,
                        trade_id,
                        holding.ticker,
                        holding.account_key,
                        holding.quantity,
                        _avg_cost_usd(holding, self.config.fx_usd_krw),
                        self.config.fx_usd_krw,
                    )
                    for holding in holdings
                ],
            )
        return len(holdings)


def _risk_tags(holdings: list[Holding], total_value_krw: int, fx_usd_krw: float) -> list[str]:
    if total_value_krw <= 0:
        return []
    by_theme: dict[str, float] = {}
    for holding in holdings:
        theme = holding.sector_tag
        by_theme[theme] = by_theme.get(theme, 0.0) + holding_value_krw(holding, fx_usd_krw)
    tags: list[str] = []
    tech_value = sum(
        value
        for theme, value in by_theme.items()
        if theme in {"BIG_TECH", "SEMICONDUCTOR", "AI_SEMICONDUCTOR", "CORE_ETF"}
    )
    if tech_value / total_value_krw >= 0.45:
        tags.append("TECH_HEAVY")
    semicon_value = sum(
        value for theme, value in by_theme.items() if theme in {"SEMICONDUCTOR", "AI_SEMICONDUCTOR"}
    )
    if semicon_value / total_value_krw >= 0.25:
        tags.append("AI_SEMICONDUCTOR_EXPOSURE")
    return tags


def _avg_cost_usd(holding: Holding, fx_usd_krw: float) -> float:
    if holding.currency == "USD":
        return holding.avg_price
    return holding.avg_price / fx_usd_krw if fx_usd_krw else holding.avg_price


def seed_demo_portfolio(store: PortfolioStore) -> PortfolioSnapshot:
    store.set_cash(12_000_000)
    for holding in [
        Holding(
            ticker="QQQ",
            market="US",
            quantity=12,
            avg_price=430.0,
            current_price=659.6,
            currency="USD",
            asset_type="ETF",
            sector_tag="CORE_ETF",
        ),
        Holding(
            ticker="SMH",
            market="US",
            quantity=8,
            avg_price=185.0,
            current_price=247.0,
            currency="USD",
            asset_type="ETF",
            sector_tag="AI_SEMICONDUCTOR",
        ),
        Holding(
            ticker="AAPL",
            market="US",
            quantity=11,
            avg_price=135.0,
            current_price=280.0,
            currency="USD",
            asset_type="EQUITY",
            sector_tag="BIG_TECH",
        ),
        Holding(
            ticker="AMD",
            market="US",
            quantity=18,
            avg_price=105.0,
            current_price=164.0,
            currency="USD",
            asset_type="EQUITY",
            sector_tag="AI_SEMICONDUCTOR",
        ),
        Holding(
            ticker="MVST",
            market="US",
            quantity=400,
            avg_price=10.0,
            current_price=0.52,
            currency="USD",
            asset_type="EQUITY",
            sector_tag="SPECULATIVE_LOSS",
        ),
    ]:
        store.save_holding(holding)
    return store.snapshot()
