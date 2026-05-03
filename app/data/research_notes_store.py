from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from app.db.database import connect, init_db


KST = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class ResearchNote:
    tickers: list[str]
    source_type: str
    source_name: str
    source_url: str
    reliability: str
    summary: str
    counter_points: str = ""
    check_questions: str = ""
    created_at: str = ""
    id: int | None = None


class ResearchNotesStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        init_db(self.db_path)

    def add(self, note: ResearchNote) -> int:
        tickers = ",".join(sorted({ticker.upper().strip() for ticker in note.tickers if ticker.strip()}))
        created_at = note.created_at or datetime.now(tz=KST).isoformat()
        with connect(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO external_research_notes (
                  created_at, tickers, source_type, source_name, source_url, reliability,
                  summary, counter_points, check_questions
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    created_at,
                    tickers,
                    note.source_type.upper(),
                    note.source_name,
                    note.source_url,
                    note.reliability.upper(),
                    note.summary,
                    note.counter_points,
                    note.check_questions,
                ),
            )
            return int(cur.lastrowid)

    def latest(self, ticker: str | None = None, limit: int = 10) -> list[ResearchNote]:
        with connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, created_at, tickers, source_type, source_name, source_url,
                       reliability, summary, counter_points, check_questions
                FROM external_research_notes
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (max(limit * 4, limit),),
            ).fetchall()
        notes = [_row_to_note(row) for row in rows]
        if ticker:
            normalized = ticker.upper()
            notes = [note for note in notes if normalized in note.tickers]
        return notes[:limit]


def _row_to_note(row) -> ResearchNote:
    return ResearchNote(
        id=row["id"],
        created_at=row["created_at"],
        tickers=[ticker for ticker in row["tickers"].split(",") if ticker],
        source_type=row["source_type"],
        source_name=row["source_name"],
        source_url=row["source_url"],
        reliability=row["reliability"],
        summary=row["summary"],
        counter_points=row["counter_points"] or "",
        check_questions=row["check_questions"] or "",
    )
