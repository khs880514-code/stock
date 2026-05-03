from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from app.db.database import connect, init_db
from app.models import Event, Source


KST = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class EarningsDate:
    ticker: str
    earnings_date: date
    source: str
    source_url: str = ""
    note: str = ""
    recorded_at: str = ""


class EarningsCalendarStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        init_db(self.db_path)

    def upsert(self, item: EarningsDate) -> None:
        recorded_at = item.recorded_at or datetime.now(tz=KST).isoformat()
        with connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO earnings_calendar_history (
                  ticker, earnings_date, source, source_url, note, recorded_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker, earnings_date, source) DO UPDATE SET
                  source_url=excluded.source_url,
                  note=excluded.note,
                  recorded_at=excluded.recorded_at
                """,
                (
                    item.ticker.upper(),
                    item.earnings_date.isoformat(),
                    item.source,
                    item.source_url,
                    item.note,
                    recorded_at,
                ),
            )

    def upcoming(self, tickers: list[str], since: date, days: int = 60) -> list[EarningsDate]:
        normalized = [ticker.upper() for ticker in tickers if ticker.strip()]
        if not normalized:
            return []
        placeholders = ",".join("?" for _ in normalized)
        until = since + timedelta(days=days)
        with connect(self.db_path) as conn:
            rows = conn.execute(
                f"""
                SELECT ticker, earnings_date, source, source_url, note, recorded_at
                FROM earnings_calendar_history
                WHERE ticker IN ({placeholders})
                  AND earnings_date BETWEEN ? AND ?
                ORDER BY earnings_date ASC, ticker ASC
                """,
                (*normalized, since.isoformat(), until.isoformat()),
            ).fetchall()
        return [_row_to_item(row) for row in rows]

    def upcoming_events(self, tickers: list[str], since: datetime, days: int = 14) -> list[Event]:
        items = self.upcoming(tickers, since.date(), days=days)
        events: list[Event] = []
        for item in items:
            event_time = datetime.combine(item.earnings_date, time(23, 59), tzinfo=KST)
            events.append(
                Event(
                    ticker=item.ticker,
                    event_type="EARNINGS",
                    event_time=event_time,
                    importance="HIGH",
                    source=Source(
                        title=item.source,
                        url=item.source_url,
                        published_at=item.recorded_at[:10] if item.recorded_at else "",
                    ),
                )
            )
        return events


def _row_to_item(row) -> EarningsDate:
    return EarningsDate(
        ticker=row["ticker"],
        earnings_date=date.fromisoformat(row["earnings_date"]),
        source=row["source"],
        source_url=row["source_url"] or "",
        note=row["note"] or "",
        recorded_at=row["recorded_at"] or "",
    )
