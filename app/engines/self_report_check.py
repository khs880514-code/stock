from __future__ import annotations

from app.models import BuyReviewRequest


FOMO_CUES = (
    ("놓치", "놓칠까"),
    ("후회", "후회"),
    ("지금 안", "지금 안 사면"),
    ("오늘", "오늘"),
    ("급등", "급등"),
    ("폭등", "폭등"),
    ("쏜다", "쏜다"),
    ("불타기", "불타기"),
    ("마지막 기회", "마지막 기회"),
    ("miss out", "miss out"),
    ("fomo", "FOMO"),
    ("moon", "moon"),
    ("soar", "soar"),
)

EXTERNAL_INFLUENCE_CUES = (
    ("친구", "친구"),
    ("지인", "지인"),
    ("유튜브", "유튜브"),
    ("youtube", "YouTube"),
    ("커뮤니티", "커뮤니티"),
    ("디시", "커뮤니티"),
    ("카톡", "카톡"),
    ("단톡", "단톡"),
    ("텔레그램", "텔레그램"),
    ("리딩방", "리딩방"),
    ("추천", "추천"),
    ("인플루언서", "인플루언서"),
    ("트위터", "트위터"),
    ("twitter", "Twitter"),
    ("x에서", "X"),
    ("레딧", "Reddit"),
    ("reddit", "Reddit"),
    ("애널리스트", "애널리스트"),
    ("목표가", "목표가"),
)


def evaluate_self_report_consistency(request: BuyReviewRequest) -> tuple[list[str], list[str]]:
    """Return blockers and support notes for suspicious self-report mismatches."""
    blockers: list[str] = []
    support_notes: list[str] = []
    text = request.reason_text.lower()

    fomo_matches = _find_matches(text, FOMO_CUES)
    if fomo_matches and request.fomo_score <= 3:
        blockers.append(
            "입력 점수-사유 불일치: FOMO 점수는 낮지만 사유에 "
            f"{_format_matches(fomo_matches)} 표현이 있어 24시간 대기"
        )
    elif len(fomo_matches) >= 2 and request.fomo_score <= 5:
        support_notes.append(
            "입력 점수-사유 불일치 가능: FOMO 점수보다 사유 문장의 긴급성이 높아 보임 "
            f"({_format_matches(fomo_matches)})"
        )

    external_matches = _find_matches(text, EXTERNAL_INFLUENCE_CUES)
    if len(external_matches) >= 2 and request.friend_influence_score <= 2:
        blockers.append(
            "입력 점수-사유 불일치: 외부 영향 점수는 낮지만 사유에 "
            f"{_format_matches(external_matches)} 표현이 있어 점수 재입력 후 재검토"
        )
    elif external_matches and request.friend_influence_score <= 4:
        support_notes.append(
            "입력 점수-사유 불일치 가능: 외부 영향 점수가 낮지만 외부 정보 흔적이 있음 "
            f"({_format_matches(external_matches)})"
        )

    return blockers, support_notes


def _find_matches(text: str, cues: tuple[tuple[str, str], ...]) -> list[str]:
    matches: list[str] = []
    seen: set[str] = set()
    for needle, label in cues:
        if needle in text and label not in seen:
            matches.append(label)
            seen.add(label)
    return matches


def _format_matches(matches: list[str]) -> str:
    return ", ".join(matches[:4])
