from __future__ import annotations

from app.engines.stock_screener import ScreenerCandidate


def explain_candidate(item: ScreenerCandidate, context: dict[str, int]) -> tuple[str, str]:
    """Return beginner-friendly why/next-step text without changing the score."""
    if item.status == "TEST":
        return "화면 검증용 샘플입니다. 실제 검토 후보와 분리해서 보세요.", "실제 후보 판단에는 사용하지 않습니다."
    if item.status == "REJECT":
        caution = item.cautions[0] if item.cautions else "보수 기준을 통과하지 못했습니다."
        return f"{caution} 때문에 지금은 우선순위가 낮습니다.", _next_step(item, context)
    if item.status == "WATCH":
        if item.missing_metrics:
            return "좋아 보이는 부분은 있지만 핵심 정보가 부족합니다.", _next_step(item, context)
        return "조건 일부는 괜찮지만 강한 우위까지는 아직 부족합니다.", _next_step(item, context)

    strengths = _strength_groups(item.reasons)
    if strengths:
        why = f"{', '.join(strengths[:2])}가 기준 안쪽이라 검토 후보입니다."
    else:
        why = "보수 기준을 통과해 검토 후보입니다."
    return why, _next_step(item, context)


def review_questions(item: ScreenerCandidate, context: dict[str, int]) -> list[str]:
    questions: list[str] = []
    why, next_step = explain_candidate(item, context)
    questions.append(why)
    if next_step:
        questions.append(next_step)
    if item.cautions and item.status != "REJECT":
        questions.append(f"주의 사유 확인: {item.cautions[0]}")
    if item.missing_metrics:
        questions.append(f"부족 지표 보강: {', '.join(item.missing_metrics[:4])}")
    if context.get("news", 0) == 0:
        questions.append("최근 뉴스 업데이트 후 실적/규제/수주/경쟁사 이슈 확인")
    if context.get("filings", 0) == 0:
        questions.append("최근 공시 또는 사업보고서 확인")
    if context.get("research", 0) == 0:
        questions.append("외부 리서치/NotebookLM 요약 또는 반대 근거 메모 추가")
    return questions[:5]


def _next_step(item: ScreenerCandidate, context: dict[str, int]) -> str:
    if item.status == "TEST":
        return "실제 후보 판단에는 사용하지 않습니다."
    if item.missing_metrics:
        return f"다음 행동: {', '.join(item.missing_metrics[:3])}를 먼저 보강하세요."
    if context.get("news", 0) == 0:
        return "다음 행동: 뉴스 업데이트 후 악재/호재를 확인하세요."
    if context.get("research", 0) == 0:
        return "다음 행동: 외부 리서치나 반대 근거를 1개 이상 붙이세요."
    if item.status == "PASS":
        return "다음 행동: 4 매수 전 점검에서 FOMO와 외부영향을 다시 확인하세요."
    return "다음 행동: 관심종목으로 두고 정보가 더 쌓이면 다시 비교하세요."


def _strength_groups(reasons: list[str]) -> list[str]:
    groups: list[str] = []
    for reason in reasons:
        label = _reason_group(reason)
        if label and label not in groups:
            groups.append(label)
    return groups


def _reason_group(reason: str) -> str:
    if reason.startswith(("PER ", "Forward PER ", "PBR ", "PSR ", "EV/EBITDA ")):
        return "가격 부담"
    if reason.startswith("Debt/Equity "):
        return "부채 부담"
    if reason.startswith(("ROE ", "ROIC ", "Operating margin ")):
        return "수익성"
    if reason.startswith(("Revenue growth ", "EPS growth ", "Operating income growth ")):
        return "성장성"
    if reason.startswith(("3M momentum ", "12M momentum ")):
        return "가격 흐름"
    if reason.startswith("FCF yield "):
        return "현금흐름"
    if reason.startswith("Market cap "):
        return "규모"
    return ""
