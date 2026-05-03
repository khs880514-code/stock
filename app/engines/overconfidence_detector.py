from __future__ import annotations

from dataclasses import dataclass


HIGH_PATTERNS = [
    "무조건",
    "확정",
    "폭등",
    "상한가",
    "이번엔 다르다",
    "몰빵",
    "인생역전",
]

MEDIUM_PATTERNS = [
    "안 오를 수 없다",
    "놓치면",
    "이미 늦었다",
    "급등",
    "대박",
]


@dataclass(frozen=True)
class OverconfidenceResult:
    level: str
    matches: list[str]


def detect_overconfidence(text: str) -> OverconfidenceResult:
    normalized = text.strip().lower()
    high = [pattern for pattern in HIGH_PATTERNS if pattern.lower() in normalized]
    if high:
        return OverconfidenceResult(level="HIGH", matches=high)
    medium = [pattern for pattern in MEDIUM_PATTERNS if pattern.lower() in normalized]
    if medium:
        return OverconfidenceResult(level="MEDIUM", matches=medium)
    return OverconfidenceResult(level="LOW", matches=[])

