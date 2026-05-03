from datetime import timedelta

from app.data.macro_collector import MockMacroCollector
from app.engines.macro_event_explainer import (
    detect_macro_triggers,
    explain_macro_event,
    trigger_frequency_review_needed,
)


def test_fx_1500_triggers_macro_explainer(config, portfolio):
    macro = MockMacroCollector().collect(fx_usd_krw=1501)
    triggers = detect_macro_triggers(macro, config)
    assert any(trigger.trigger_type == "FX" for trigger in triggers)
    message = explain_macro_event(triggers[0], portfolio)
    assert "양방향" not in message
    assert "반대로" in message
    assert "출처:" in message


def test_weekly_trigger_frequency_review(config, now):
    macro = MockMacroCollector().collect(fx_usd_krw=1501)
    triggers = detect_macro_triggers(macro, config)
    repeated = []
    for idx in range(5):
        trigger = triggers[0].model_copy(update={"occurred_at": now - timedelta(days=idx)})
        repeated.append(trigger)
    assert trigger_frequency_review_needed(repeated, now, config)

