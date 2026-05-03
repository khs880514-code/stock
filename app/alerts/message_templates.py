from __future__ import annotations

from app.models import AlertDecision


def format_decision_message(title: str, decision: AlertDecision) -> str:
    lines = [
        f"[{title}]",
        "",
        f"판단(룰엔진): {decision.action.value}",
        f"최대 검토 금액: {decision.max_amount_krw:,}원",
        "이유:",
    ]
    lines.extend(f"- {reason}" for reason in decision.reason)
    if decision.bear_case:
        lines.extend(["", "반대 시나리오:"])
        lines.extend(f"- {item}" for item in decision.bear_case[:3])
    if decision.do_not_buy_if:
        lines.extend(["", "중단 조건:"])
        lines.extend(f"- {item}" for item in decision.do_not_buy_if[:3])
    if decision.sources:
        lines.extend(["", "출처:"])
        lines.extend(f"- {source.title}: {source.url}" for source in decision.sources[:3])
    lines.extend(["", f"다음 체크: {decision.next_check}"])
    return "\n".join(lines)


def compact_message(message: str, limit: int = 1500) -> str:
    if len(message) <= limit:
        return message
    return message[: limit - 20].rstrip() + "\n...(축약)"

