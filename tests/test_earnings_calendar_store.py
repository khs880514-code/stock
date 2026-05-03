from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.data.earnings_calendar_store import EarningsCalendarStore, EarningsDate


def test_earnings_store_returns_upcoming_events(tmp_path):
    store = EarningsCalendarStore(tmp_path / "earnings.sqlite3")
    store.upsert(
        EarningsDate(
            ticker="AMD",
            earnings_date=date(2026, 5, 4),
            source="AMD IR",
            source_url="https://ir.amd.com/",
            note="장후 예정",
        )
    )
    events = store.upcoming_events(
        ["AMD"],
        datetime(2026, 5, 3, 9, 0, tzinfo=ZoneInfo("Asia/Seoul")),
        days=7,
    )
    assert len(events) == 1
    assert events[0].ticker == "AMD"
    assert events[0].event_type == "EARNINGS"
    assert events[0].source.title == "AMD IR"
