from __future__ import annotations

from datetime import datetime, timedelta

from app.models import Event, Source


class MockEventCalendar:
    def upcoming_events(self, tickers: list[str], since: datetime, days: int = 14) -> list[Event]:
        normalized = {ticker.upper() for ticker in tickers}
        events: list[Event] = []
        if "AMD" in normalized:
            events.append(
                Event(
                    ticker="AMD",
                    event_type="EARNINGS",
                    event_time=since + timedelta(hours=24),
                    importance="HIGH",
                    source=Source(
                        title="AMD investor relations calendar",
                        url="https://ir.amd.com/",
                        published_at=since.date().isoformat(),
                    ),
                )
            )
        if "AAPL" in normalized:
            events.append(
                Event(
                    ticker="AAPL",
                    event_type="EARNINGS",
                    event_time=since + timedelta(days=9),
                    importance="HIGH",
                    source=Source(
                        title="Apple investor relations",
                        url="https://investor.apple.com/",
                        published_at=since.date().isoformat(),
                    ),
                )
            )
        return [event for event in events if event.event_time <= since + timedelta(days=days)]

