from app.alerts.message_templates import format_decision_message
from app.models import Action, AlertDecision


def test_decision_message_uses_label_not_numeric_confidence():
    message = format_decision_message(
        "테스트",
        AlertDecision(ticker="AMD", action=Action.NO_TRADE, reason=["실적 전 변동성"]),
    )
    assert "0." not in message
    assert "confidence:" not in message.lower()

