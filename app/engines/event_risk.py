from __future__ import annotations

from datetime import datetime, timedelta

from app.models import Event


def events_within_window(events: list[Event], ticker: str, now: datetime, days: int) -> list[Event]:
    normalized = ticker.upper()
    end = now + timedelta(days=days)
    return [
        event
        for event in events
        if event.ticker == normalized and now <= event.event_time <= end and event.importance == "HIGH"
    ]


def has_earnings_risk(events: list[Event], ticker: str, now: datetime, days: int) -> bool:
    return any(event.event_type == "EARNINGS" for event in events_within_window(events, ticker, now, days))

