from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.models import Event


class EventCalendar(Protocol):
    def upcoming_events(self, tickers: list[str], since: datetime, days: int = 14) -> list[Event]:
        ...

