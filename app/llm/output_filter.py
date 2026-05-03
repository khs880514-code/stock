from __future__ import annotations

import re
from dataclasses import dataclass

from app.models import LlmAssist


ASSERTIVE_TERMS = ["무조건", "확정", "폭등", "상한가", "이번엔 다르다"]
TRADE_VERB_PATTERNS = [
    r"사세요",
    r"파세요",
    r"매수\s*하세요",
    r"매도\s*하세요",
    r"buy\s+it",
    r"sell\s+it",
]
NUMERIC_CONFIDENCE_PATTERNS = [
    r"confidence\s*[:=]\s*0\.\d+",
    r"확신도\s*[:=]?\s*\d+(\.\d+)?",
    r"신뢰도\s*[:=]?\s*\d+\s*/\s*10",
]
BANNED_ACTION_TOKENS = [
    "BUY" + "_NOW",
    "SELL" + "_NOW",
    "AUTO" + "_BUY",
    "AUTO" + "_SELL",
    "MARKET" + "_ORDER",
    "ALL" + "_IN",
]


@dataclass(frozen=True)
class FilterResult:
    ok: bool
    errors: list[str]


def validate_llm_assist(assist: LlmAssist) -> FilterResult:
    errors: list[str] = []
    text = "\n".join(
        assist.reason + assist.bear_case + assist.do_not_buy_if + [assist.next_check]
    )
    if any(term in text for term in ASSERTIVE_TERMS):
        errors.append("단정 표현 포함")
    if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in TRADE_VERB_PATTERNS):
        errors.append("매수/매도 지시 표현 포함")
    if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in NUMERIC_CONFIDENCE_PATTERNS):
        errors.append("숫자형 확신도 표현 포함")
    if any(token in text for token in BANNED_ACTION_TOKENS):
        errors.append("금지 액션 문자열 포함")
    if not assist.sources:
        errors.append("출처 링크 없음")
    return FilterResult(ok=not errors, errors=errors)


def sanitize_text_lines(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    for line in lines:
        if any(term in line for term in ASSERTIVE_TERMS):
            continue
        if any(re.search(pattern, line, flags=re.IGNORECASE) for pattern in TRADE_VERB_PATTERNS):
            continue
        if any(re.search(pattern, line, flags=re.IGNORECASE) for pattern in NUMERIC_CONFIDENCE_PATTERNS):
            continue
        cleaned.append(line)
    return cleaned

