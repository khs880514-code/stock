from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from app.db.database import connect, init_db
from app.models import AlertDecision, TradeEntry


class TradeJournal:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        init_db(self.db_path)

    def add_trade(self, entry: TradeEntry) -> int:
        with connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO trades (
                  timestamp, ticker, account_key, action, quantity, avg_price, reason_text,
                  fomo_score, friend_influence_score, price_at_entry,
                  price_1d, price_1w, price_1m, outcome_note, mistake_type
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.timestamp.isoformat(),
                    entry.ticker,
                    entry.account_key,
                    entry.action.upper(),
                    entry.quantity,
                    entry.avg_price,
                    entry.reason_text,
                    entry.fomo_score,
                    entry.friend_influence_score,
                    entry.price_at_entry,
                    entry.price_1d,
                    entry.price_1w,
                    entry.price_1m,
                    entry.outcome_note,
                    entry.mistake_type.value,
                ),
            )
            return int(cursor.lastrowid)

    def recent_trades(self, since: datetime | None = None) -> list[TradeEntry]:
        query = "SELECT * FROM trades"
        params: tuple[str, ...] = ()
        if since is not None:
            query += " WHERE timestamp >= ?"
            params = (since.isoformat(),)
        query += " ORDER BY timestamp DESC"
        with connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
        return [_row_to_trade(row) for row in rows]

    def one_week_reviews(self, now: datetime) -> list[TradeEntry]:
        start = now - timedelta(days=8)
        end = now - timedelta(days=6)
        with connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT * FROM trades
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp DESC
                """,
                (start.isoformat(), end.isoformat()),
            ).fetchall()
        return [_row_to_trade(row) for row in rows]

    def update_reflection_price(self, trade_id: int, field: str, price: float) -> None:
        if field not in {"price_1d", "price_1w", "price_1m"}:
            raise ValueError("Unsupported reflection field.")
        with connect(self.db_path) as conn:
            conn.execute(f"UPDATE trades SET {field} = ? WHERE id = ?", (price, trade_id))

    def log_alert(
        self,
        alert_type: str,
        message: str,
        decision: AlertDecision | None = None,
        rule_id: str | None = None,
        severity: str | None = None,
    ) -> int:
        ticker = decision.ticker if decision else None
        action = decision.action.value if decision else None
        if decision and decision.post_drop_context and decision.post_drop_context.triggered:
            rule_id = rule_id or "post_drop_chase"
            severity = severity or decision.post_drop_context.severity
        if decision and decision.holiday_gap_signal and decision.holiday_gap_signal.triggered:
            rule_id = rule_id or "holiday_gap_setup"
            severity = severity or decision.holiday_gap_signal.severity
        if decision and decision.post_run_decomposition and decision.post_run_decomposition.triggered:
            rule_id = rule_id or "post_run_decomposition"
            severity = severity or decision.post_run_decomposition.severity
        if decision and decision.regret_pattern and decision.regret_pattern.triggered:
            rule_id = rule_id or "decision_protection"
            severity = severity or "high"
        with connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO alert_logs (created_at, alert_type, ticker, action, rule_id, severity, message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (datetime.now().isoformat(), alert_type, ticker, action, rule_id, severity, message),
            )
            return int(cursor.lastrowid)


def _row_to_trade(row) -> TradeEntry:
    data = dict(row)
    data["timestamp"] = datetime.fromisoformat(data["timestamp"])
    return TradeEntry(**data)
