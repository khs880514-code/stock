from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(db_path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def init_db(db_path: Path | str) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        _ensure_column(conn, "alert_logs", "rule_id", "TEXT")
        _ensure_column(conn, "alert_logs", "severity", "TEXT")
        _ensure_column(conn, "earnings_calendar_history", "source_url", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "earnings_calendar_history", "note", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "external_research_notes", "counter_points", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "external_research_notes", "check_questions", "TEXT NOT NULL DEFAULT ''")


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
