from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.db.database import connect, init_db
from app.models import AlertDecision, BuyReviewRequest


@dataclass(frozen=True)
class BuyCheckLogEntry:
    id: int
    decision_at: datetime
    ticker: str
    action: str
    max_amount_krw: int
    price_at_decision: float | None
    reason_text: str
    fomo_score: int
    friend_influence_score: int


class BuyCheckLogStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        init_db(self.db_path)

    def add(
        self,
        *,
        decision_at: datetime,
        request: BuyReviewRequest,
        decision: AlertDecision,
        price_at_decision: float | None,
    ) -> int:
        with connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO buy_check_log (
                  decision_at, ticker, action, max_amount_krw, price_at_decision,
                  reason_text, fomo_score, friend_influence_score
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision_at.isoformat(),
                    request.ticker,
                    decision.action.value,
                    decision.max_amount_krw,
                    price_at_decision,
                    request.reason_text,
                    request.fomo_score,
                    request.friend_influence_score,
                ),
            )
            return int(cursor.lastrowid)

    def recent_for_ticker(self, ticker: str, since: datetime) -> list[BuyCheckLogEntry]:
        with connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, decision_at, ticker, action, max_amount_krw, price_at_decision,
                       reason_text, fomo_score, friend_influence_score
                FROM buy_check_log
                WHERE ticker = ? AND decision_at >= ?
                ORDER BY decision_at DESC
                """,
                (ticker.upper().strip(), since.isoformat()),
            ).fetchall()
        return [_row_to_entry(row) for row in rows]


def _row_to_entry(row) -> BuyCheckLogEntry:
    data = dict(row)
    data["decision_at"] = datetime.fromisoformat(data["decision_at"])
    return BuyCheckLogEntry(**data)
