from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.db.database import connect, init_db


KST = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class WatchlistItem:
    ticker: str
    market: str
    reason: str
    priority: int
    sector_tag: str
    created_at: str
    updated_at: str


class WatchlistStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        init_db(self.db_path)

    def add_or_update(
        self,
        ticker: str,
        market: str,
        reason: str,
        priority: int = 3,
        sector_tag: str = "UNKNOWN",
    ) -> None:
        now = datetime.now(tz=KST).isoformat()
        with connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO watchlist (
                  ticker, market, reason, priority, sector_tag, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker) DO UPDATE SET
                  market=excluded.market,
                  reason=excluded.reason,
                  priority=excluded.priority,
                  sector_tag=excluded.sector_tag,
                  updated_at=excluded.updated_at
                """,
                (
                    ticker.upper().strip(),
                    market.upper().strip(),
                    reason.strip(),
                    priority,
                    sector_tag.upper().strip(),
                    now,
                    now,
                ),
            )

    def remove(self, ticker: str) -> bool:
        with connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker.upper().strip(),))
            return cursor.rowcount > 0

    def list_items(self) -> list[WatchlistItem]:
        with connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT ticker, market, reason, priority, sector_tag, created_at, updated_at
                FROM watchlist
                ORDER BY priority ASC, ticker ASC
                """
            ).fetchall()
        return [WatchlistItem(**dict(row)) for row in rows]
