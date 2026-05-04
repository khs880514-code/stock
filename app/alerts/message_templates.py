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
    if decision.ticker_sensitivity_used:
        sensitivity = decision.ticker_sensitivity_used
        lines.extend(
            [
                "",
                "종목 민감도:",
                (
                    f"- 섹터 {sensitivity.sector_tag}, 미국 프록시 {sensitivity.us_sector_proxy_symbol or '-'}, "
                    f"외국인 지분 {sensitivity.foreign_ownership_pct if sensitivity.foreign_ownership_pct is not None else '-'}%, "
                    f"섹터 상관 {sensitivity.us_sector_corr_60d if sensitivity.us_sector_corr_60d is not None else '-'}"
                ),
            ]
        )
    if decision.holiday_gap_signal and decision.holiday_gap_signal.explanation:
        lines.extend(["", "연휴 갭 신호:", f"- {decision.holiday_gap_signal.explanation}"])
    if decision.relative_weakness_signal and decision.relative_weakness_signal.explanation:
        lines.extend(["", "상대 약세 신호:", f"- {decision.relative_weakness_signal.explanation}"])
    if decision.post_run_decomposition and decision.post_run_decomposition.explanation:
        lines.extend(["", "급등 분해:", f"- {decision.post_run_decomposition.explanation}"])
    if decision.regret_pattern and decision.regret_pattern.explanation:
        lines.extend(["", "후회 추격 감지:", f"- {decision.regret_pattern.explanation}"])
    if decision.blackout_suggested:
        lines.extend(
            [
                "",
                "관찰 블랙아웃 제안:",
                f"- {decision.blackout_suggested.do_not_watch_until}까지 가격 확인을 줄이고 조건만 다시 확인",
            ]
        )
    if decision.sources:
        lines.extend(["", "출처:"])
        lines.extend(f"- {source.title}: {source.url}" for source in decision.sources[:3])
    lines.extend(["", f"다음 체크: {decision.next_check}"])
    return "\n".join(lines)


def compact_message(message: str, limit: int = 1500) -> str:
    if len(message) <= limit:
        return message
    return message[: limit - 20].rstrip() + "\n...(축약)"
