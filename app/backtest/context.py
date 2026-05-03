from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from app.config import AppConfig
from app.data.price_history import PriceHistoryStore
from app.db.database import connect, init_db
from app.models import Holding, PortfolioSnapshot, PriceHistoryBar


@dataclass(frozen=True)
class BacktestTrade:
    trade_id: int
    decision_at: datetime
    ticker: str
    amount_krw: int
    reason: str
    fomo: int
    influence: int


@dataclass(frozen=True)
class BacktestContext:
    portfolio_at_t: PortfolioSnapshot
    price_window: list[PriceHistoryBar]
    rule_price_history: list[PriceHistoryBar]
    earnings_dates: list[date]
    fx_usdkrw_at_t: float
    completeness: str


def build_context(
    db_path: Path | str,
    trade: BacktestTrade,
    mode: str,
    config: AppConfig,
    price_store: PriceHistoryStore | None = None,
) -> BacktestContext | None:
    init_db(db_path)
    price_store = price_store or PriceHistoryStore(db_path)
    portfolio = _load_portfolio_snapshot(db_path, trade, config)
    earnings_dates = _load_earnings_dates(db_path, trade.ticker, trade.decision_at.date())
    start = trade.decision_at.date() - timedelta(days=45)
    end = trade.decision_at.date() + timedelta(days=130)
    price_window = price_store.get_window(trade.ticker, start, end)
    fx = _snapshot_fx(db_path, trade, config)

    if mode == "strict":
        if portfolio is None or not price_window or not earnings_dates or fx is None:
            return None
        completeness = "full"
    elif mode == "reconstruct":
        completeness = "reconstructed"
        if portfolio is None:
            portfolio = PortfolioSnapshot(cash_krw=0, holdings=[], total_value_krw=0)
        if not price_window:
            try:
                price_window = price_store.fetch_yfinance_into_cache(trade.ticker, start, end)
            except RuntimeError:
                return None
        if fx is None:
            fx = config.fx_usd_krw
    else:
        raise ValueError("mode must be strict or reconstruct")

    rule_price_history = [bar for bar in price_window if bar.date <= trade.decision_at.date()]
    if any(bar.date > trade.decision_at.date() for bar in rule_price_history):
        raise AssertionError("lookahead price leaked into rule context")
    return BacktestContext(
        portfolio_at_t=portfolio,
        price_window=price_window,
        rule_price_history=rule_price_history,
        earnings_dates=earnings_dates,
        fx_usdkrw_at_t=fx or config.fx_usd_krw,
        completeness=completeness,
    )


def _load_portfolio_snapshot(
    db_path: Path | str, trade: BacktestTrade, config: AppConfig
) -> PortfolioSnapshot | None:
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM holdings_snapshot
            WHERE taken_at <= ?
            ORDER BY CASE WHEN trade_id = ? THEN 0 ELSE 1 END, taken_at DESC, snapshot_id DESC
            """,
            (trade.decision_at.isoformat(), trade.trade_id),
        ).fetchall()
    if not rows:
        return None
    taken_at = rows[0]["taken_at"]
    same_snapshot = [row for row in rows if row["taken_at"] == taken_at]
    holdings: list[Holding] = []
    total_value = 0.0
    for row in same_snapshot:
        current_price = _price_at_or_cost(db_path, row["ticker"], trade.decision_at.date(), row["avg_cost_usd"])
        holdings.append(
            Holding(
                ticker=row["ticker"],
                market="US",
                quantity=row["shares"],
                avg_price=row["avg_cost_usd"],
                current_price=current_price,
                currency="USD",
                asset_type="EQUITY",
                sector_tag="UNKNOWN",
            )
        )
        total_value += row["shares"] * current_price * row["fx_usdkrw"]
    assumed_cash = config.min_cash_krw + trade.amount_krw
    return PortfolioSnapshot(
        cash_krw=assumed_cash,
        holdings=holdings,
        total_value_krw=int(total_value + assumed_cash),
    )


def _snapshot_fx(db_path: Path | str, trade: BacktestTrade, config: AppConfig) -> float | None:
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT fx_usdkrw FROM holdings_snapshot
            WHERE taken_at <= ?
            ORDER BY CASE WHEN trade_id = ? THEN 0 ELSE 1 END, taken_at DESC, snapshot_id DESC
            LIMIT 1
            """,
            (trade.decision_at.isoformat(), trade.trade_id),
        ).fetchone()
    return float(row["fx_usdkrw"]) if row else None


def _load_earnings_dates(db_path: Path | str, ticker: str, trade_date: date) -> list[date]:
    start = trade_date - timedelta(days=30)
    end = trade_date + timedelta(days=30)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT earnings_date FROM earnings_calendar_history
            WHERE ticker = ? AND earnings_date BETWEEN ? AND ?
            ORDER BY earnings_date ASC
            """,
            (ticker.upper(), start.isoformat(), end.isoformat()),
        ).fetchall()
    return [datetime.strptime(row["earnings_date"], "%Y-%m-%d").date() for row in rows]


def _price_at_or_cost(db_path: Path | str, ticker: str, on_date: date, fallback: float) -> float:
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT close FROM price_history
            WHERE ticker = ? AND date <= ?
            ORDER BY date DESC
            LIMIT 1
            """,
            (ticker.upper(), on_date.isoformat()),
        ).fetchone()
    return float(row["close"]) if row else float(fallback)
