from datetime import timedelta

from app.engines.event_risk import has_earnings_risk
from app.models import Event


def test_amd_earnings_within_24h_is_risk(now):
    events = [
        Event(
            ticker="AMD",
            event_type="EARNINGS",
            event_time=now + timedelta(hours=24),
            importance="HIGH",
        )
    ]
    assert has_earnings_risk(events, "AMD", now, days=7)

