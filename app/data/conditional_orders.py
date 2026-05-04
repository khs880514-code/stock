from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.db.database import connect, init_db
from app.models import ConditionalDecision


class ConditionalDecisionStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        init_db(self.db_path)

    def add(self, decision: ConditionalDecision) -> int:
        with connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO conditional_decisions (
                  created_at, ticker, condition_text, planned_action,
                  expires_at, status, note
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.created_at.isoformat(),
                    decision.ticker,
                    decision.condition_text,
                    decision.planned_action,
                    decision.expires_at.isoformat() if decision.expires_at else None,
                    decision.status,
                    decision.note,
                ),
            )
            return int(cursor.lastrowid)

    def list_active(self, ticker: str | None = None, now: datetime | None = None) -> list[ConditionalDecision]:
        params: list[str] = ["ACTIVE"]
        where = "WHERE status = ?"
        if ticker:
            where += " AND ticker = ?"
            params.append(ticker.upper().strip())
        if now is not None:
            where += " AND (expires_at IS NULL OR expires_at >= ?)"
            params.append(now.isoformat())
        with connect(self.db_path) as conn:
            rows = conn.execute(
                f"""
                SELECT id, created_at, ticker, condition_text, planned_action,
                       expires_at, status, note
                FROM conditional_decisions
                {where}
                ORDER BY created_at DESC
                """,
                tuple(params),
            ).fetchall()
        return [_row_to_decision(row) for row in rows]

    def update_status(self, decision_id: int, status: str) -> bool:
        with connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE conditional_decisions SET status = ? WHERE id = ?",
                (status.upper(), decision_id),
            )
            return cursor.rowcount > 0


def _row_to_decision(row) -> ConditionalDecision:
    data = dict(row)
    data["created_at"] = datetime.fromisoformat(data["created_at"])
    data["expires_at"] = datetime.fromisoformat(data["expires_at"]) if data["expires_at"] else None
    return ConditionalDecision(**data)
