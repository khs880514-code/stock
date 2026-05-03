from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.db.database import connect, init_db
from app.models import CollectionLog


class CollectionLogger:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        init_db(self.db_path)

    def log(self, source_name: str, ok: bool, message: str = "") -> None:
        item = CollectionLog(
            source_name=source_name,
            collected_at=datetime.now().astimezone(),
            ok=ok,
            message=message,
        )
        with connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO collection_logs (source_name, collected_at, ok, message)
                VALUES (?, ?, ?, ?)
                """,
                (item.source_name, item.collected_at.isoformat(), int(item.ok), item.message),
            )


def run_mock_collection(db_path: Path | str) -> list[str]:
    logger = CollectionLogger(db_path)
    collected = [
        "mock_price_provider",
        "mock_macro_collector",
        "mock_event_calendar",
        "mock_news_collector",
        "mock_filings_collector",
    ]
    for source in collected:
        logger.log(source, True, "mock collection completed")
    return collected

