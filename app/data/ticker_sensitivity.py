from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.db.database import connect, init_db
from app.models import TickerSensitivitySnapshot


KST = ZoneInfo("Asia/Seoul")


DEFAULT_SECTOR_PROXY = {
    "AI_SEMICONDUCTOR": "SMH",
    "SEMICONDUCTOR": "SMH",
    "MEMORY": "SMH",
    "BIG_TECH": "QQQ",
    "BATTERY": "LIT",
    "BIO": "IBB",
    "GAME": "HERO",
}


ESTIMATED_KR_SEMICONDUCTOR_SENSITIVITY = {
    "005930.KS": TickerSensitivitySnapshot(
        ticker="005930.KS",
        market="KR",
        sector_tag="AI_SEMICONDUCTOR",
        us_sector_proxy_symbol="SMH",
        foreign_ownership_pct=55.0,
        us_sector_corr_60d=0.65,
        beta_to_kospi_60d=1.0,
        manual_override=True,
    ),
    "000660.KS": TickerSensitivitySnapshot(
        ticker="000660.KS",
        market="KR",
        sector_tag="AI_SEMICONDUCTOR",
        us_sector_proxy_symbol="SMH",
        foreign_ownership_pct=53.0,
        us_sector_corr_60d=0.78,
        beta_to_kospi_60d=1.2,
        manual_override=True,
    ),
}


@dataclass(frozen=True)
class ForeignOwnershipPoint:
    ticker: str
    observed_at: date
    foreign_ownership_pct: float
    source: str = "manual"


class TickerSensitivityStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        init_db(self.db_path)

    def get(self, ticker: str) -> TickerSensitivitySnapshot | None:
        with connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT ticker, market, sector_tag, us_sector_proxy_symbol,
                       foreign_ownership_pct, foreign_ownership_taken_at,
                       us_sector_corr_60d, us_market_corr_60d, fx_corr_60d,
                       beta_to_kospi_60d, corr_taken_at, manual_override
                FROM ticker_sensitivity
                WHERE ticker = ?
                """,
                (ticker.upper().strip(),),
            ).fetchone()
        return _row_to_snapshot(row) if row else None

    def list_all(self) -> list[TickerSensitivitySnapshot]:
        with connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT ticker, market, sector_tag, us_sector_proxy_symbol,
                       foreign_ownership_pct, foreign_ownership_taken_at,
                       us_sector_corr_60d, us_market_corr_60d, fx_corr_60d,
                       beta_to_kospi_60d, corr_taken_at, manual_override
                FROM ticker_sensitivity
                ORDER BY ticker ASC
                """
            ).fetchall()
        return [_row_to_snapshot(row) for row in rows]

    def upsert(self, snapshot: TickerSensitivitySnapshot) -> None:
        proxy = snapshot.us_sector_proxy_symbol or DEFAULT_SECTOR_PROXY.get(snapshot.sector_tag.upper())
        now = datetime.now(tz=KST).isoformat()
        with connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO ticker_sensitivity (
                  ticker, market, sector_tag, us_sector_proxy_symbol,
                  foreign_ownership_pct, foreign_ownership_taken_at,
                  us_sector_corr_60d, us_market_corr_60d, fx_corr_60d,
                  beta_to_kospi_60d, corr_taken_at, manual_override, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker) DO UPDATE SET
                  market=excluded.market,
                  sector_tag=excluded.sector_tag,
                  us_sector_proxy_symbol=excluded.us_sector_proxy_symbol,
                  foreign_ownership_pct=excluded.foreign_ownership_pct,
                  foreign_ownership_taken_at=excluded.foreign_ownership_taken_at,
                  us_sector_corr_60d=excluded.us_sector_corr_60d,
                  us_market_corr_60d=excluded.us_market_corr_60d,
                  fx_corr_60d=excluded.fx_corr_60d,
                  beta_to_kospi_60d=excluded.beta_to_kospi_60d,
                  corr_taken_at=excluded.corr_taken_at,
                  manual_override=excluded.manual_override,
                  updated_at=excluded.updated_at
                """,
                (
                    snapshot.ticker,
                    snapshot.market,
                    snapshot.sector_tag.upper(),
                    proxy,
                    snapshot.foreign_ownership_pct,
                    _date_or_none(snapshot.foreign_ownership_taken_at),
                    snapshot.us_sector_corr_60d,
                    snapshot.us_market_corr_60d,
                    snapshot.fx_corr_60d,
                    snapshot.beta_to_kospi_60d,
                    _date_or_none(snapshot.corr_taken_at),
                    1 if snapshot.manual_override else 0,
                    now,
                ),
            )

    def set_foreign_ownership(
        self,
        ticker: str,
        foreign_ownership_pct: float,
        observed_at: date,
        source: str = "manual",
    ) -> None:
        normalized = ticker.upper().strip()
        existing = self.get(normalized) or TickerSensitivitySnapshot(ticker=normalized)
        self.upsert(
            existing.model_copy(
                update={
                    "foreign_ownership_pct": foreign_ownership_pct,
                    "foreign_ownership_taken_at": observed_at,
                }
            )
        )
        with connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO foreign_ownership_history (
                  ticker, observed_at, foreign_ownership_pct, source
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(ticker, observed_at, source) DO UPDATE SET
                  foreign_ownership_pct=excluded.foreign_ownership_pct
                """,
                (normalized, observed_at.isoformat(), foreign_ownership_pct, source),
            )

    def seed_kr_semiconductor_estimates(self) -> int:
        count = 0
        for snapshot in ESTIMATED_KR_SEMICONDUCTOR_SENSITIVITY.values():
            self.upsert(
                snapshot.model_copy(
                    update={
                        "foreign_ownership_taken_at": None,
                        "corr_taken_at": None,
                        "manual_override": False,
                    }
                )
            )
            count += 1
        return count


def is_foreign_stale(snapshot: TickerSensitivitySnapshot, today: date, max_age_days: int = 3) -> bool:
    if snapshot.foreign_ownership_pct is not None and snapshot.foreign_ownership_taken_at is None:
        return True
    if snapshot.foreign_ownership_taken_at is None:
        return False
    return (today - snapshot.foreign_ownership_taken_at).days > max_age_days


def is_corr_stale(snapshot: TickerSensitivitySnapshot, today: date, max_age_days: int = 10) -> bool:
    if snapshot.us_sector_corr_60d is not None and snapshot.corr_taken_at is None:
        return True
    if snapshot.corr_taken_at is None:
        return False
    return (today - snapshot.corr_taken_at).days > max_age_days


def _row_to_snapshot(row) -> TickerSensitivitySnapshot:
    data = dict(row)
    data["manual_override"] = bool(data["manual_override"])
    data["foreign_ownership_taken_at"] = _parse_date(data.get("foreign_ownership_taken_at"))
    data["corr_taken_at"] = _parse_date(data.get("corr_taken_at"))
    return TickerSensitivitySnapshot(**data)


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _date_or_none(value: date | None) -> str | None:
    return value.isoformat() if value else None
