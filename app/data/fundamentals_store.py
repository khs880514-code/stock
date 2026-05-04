from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.db.database import connect, init_db


KST = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class FundamentalSnapshot:
    ticker: str
    market: str = "KR"
    company_name: str = ""
    sector_tag: str = "UNKNOWN"
    as_of_date: date | None = None
    currency: str = "KRW"
    market_cap_krw: float | None = None
    per: float | None = None
    forward_per: float | None = None
    pbr: float | None = None
    psr: float | None = None
    ev_ebitda: float | None = None
    dividend_yield_pct: float | None = None
    roe_pct: float | None = None
    roa_pct: float | None = None
    roic_pct: float | None = None
    operating_margin_pct: float | None = None
    net_margin_pct: float | None = None
    revenue_growth_pct: float | None = None
    eps_growth_pct: float | None = None
    operating_income_growth_pct: float | None = None
    debt_to_equity_pct: float | None = None
    current_ratio: float | None = None
    interest_coverage: float | None = None
    fcf_yield_pct: float | None = None
    price_momentum_3m_pct: float | None = None
    price_momentum_12m_pct: float | None = None
    notes: str = ""
    source: str = "manual"
    updated_at: str = ""


class FundamentalsStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        init_db(self.db_path)

    def upsert(self, item: FundamentalSnapshot) -> None:
        now = item.updated_at or datetime.now(tz=KST).isoformat()
        as_of = item.as_of_date or datetime.now(tz=KST).date()
        with connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO stock_fundamentals (
                  ticker, market, company_name, sector_tag, as_of_date, currency,
                  market_cap_krw, per, forward_per, pbr, psr, ev_ebitda,
                  dividend_yield_pct, roe_pct, roa_pct, roic_pct,
                  operating_margin_pct, net_margin_pct, revenue_growth_pct,
                  eps_growth_pct, operating_income_growth_pct, debt_to_equity_pct,
                  current_ratio, interest_coverage, fcf_yield_pct,
                  price_momentum_3m_pct, price_momentum_12m_pct,
                  notes, source, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker) DO UPDATE SET
                  market=excluded.market,
                  company_name=excluded.company_name,
                  sector_tag=excluded.sector_tag,
                  as_of_date=excluded.as_of_date,
                  currency=excluded.currency,
                  market_cap_krw=excluded.market_cap_krw,
                  per=excluded.per,
                  forward_per=excluded.forward_per,
                  pbr=excluded.pbr,
                  psr=excluded.psr,
                  ev_ebitda=excluded.ev_ebitda,
                  dividend_yield_pct=excluded.dividend_yield_pct,
                  roe_pct=excluded.roe_pct,
                  roa_pct=excluded.roa_pct,
                  roic_pct=excluded.roic_pct,
                  operating_margin_pct=excluded.operating_margin_pct,
                  net_margin_pct=excluded.net_margin_pct,
                  revenue_growth_pct=excluded.revenue_growth_pct,
                  eps_growth_pct=excluded.eps_growth_pct,
                  operating_income_growth_pct=excluded.operating_income_growth_pct,
                  debt_to_equity_pct=excluded.debt_to_equity_pct,
                  current_ratio=excluded.current_ratio,
                  interest_coverage=excluded.interest_coverage,
                  fcf_yield_pct=excluded.fcf_yield_pct,
                  price_momentum_3m_pct=excluded.price_momentum_3m_pct,
                  price_momentum_12m_pct=excluded.price_momentum_12m_pct,
                  notes=excluded.notes,
                  source=excluded.source,
                  updated_at=excluded.updated_at
                """,
                _params(item, as_of, now),
            )

    def get(self, ticker: str) -> FundamentalSnapshot | None:
        with connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM stock_fundamentals WHERE ticker = ?",
                (ticker.upper().strip(),),
            ).fetchone()
        return _row_to_snapshot(row) if row else None

    def list_all(self) -> list[FundamentalSnapshot]:
        with connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT * FROM stock_fundamentals
                ORDER BY market ASC, sector_tag ASC, ticker ASC
                """
            ).fetchall()
        return [_row_to_snapshot(row) for row in rows]


def _params(item: FundamentalSnapshot, as_of: date, updated_at: str) -> tuple:
    return (
        item.ticker.upper().strip(),
        item.market.upper().strip(),
        item.company_name.strip(),
        item.sector_tag.upper().strip(),
        as_of.isoformat(),
        item.currency.upper().strip(),
        item.market_cap_krw,
        item.per,
        item.forward_per,
        item.pbr,
        item.psr,
        item.ev_ebitda,
        item.dividend_yield_pct,
        item.roe_pct,
        item.roa_pct,
        item.roic_pct,
        item.operating_margin_pct,
        item.net_margin_pct,
        item.revenue_growth_pct,
        item.eps_growth_pct,
        item.operating_income_growth_pct,
        item.debt_to_equity_pct,
        item.current_ratio,
        item.interest_coverage,
        item.fcf_yield_pct,
        item.price_momentum_3m_pct,
        item.price_momentum_12m_pct,
        item.notes.strip(),
        item.source.strip() or "manual",
        updated_at,
    )


def _row_to_snapshot(row) -> FundamentalSnapshot:
    data = dict(row)
    data["as_of_date"] = date.fromisoformat(data["as_of_date"]) if data["as_of_date"] else None
    return FundamentalSnapshot(**data)
