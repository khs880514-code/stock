from __future__ import annotations

from collections import Counter


NEWS_FLAG_RULES = (
    (
        "실적/가이던스",
        (
            "earnings",
            "guidance",
            "forecast",
            "outlook",
            "revenue",
            "profit",
            "실적",
            "가이던스",
            "전망",
        ),
    ),
    (
        "규제/소송",
        (
            "lawsuit",
            "probe",
            "investigation",
            "sec",
            "regulator",
            "antitrust",
            "ban",
            "소송",
            "조사",
            "규제",
            "제재",
        ),
    ),
    (
        "애널리스트/목표가",
        (
            "upgrade",
            "downgrade",
            "price target",
            "analyst",
            "rating",
            "목표가",
            "상향",
            "하향",
            "애널리스트",
        ),
    ),
    (
        "자금조달/희석",
        (
            "offering",
            "dilution",
            "convertible",
            "debt",
            "유상증자",
            "전환사채",
            "희석",
            "부채",
        ),
    ),
    (
        "모멘텀/과열",
        (
            "surge",
            "rally",
            "soars",
            "jumps",
            "record high",
            "급등",
            "폭등",
            "랠리",
            "신고가",
        ),
    ),
)


def classify_headline(title: str) -> list[str]:
    normalized = title.lower()
    flags: list[str] = []
    for label, keywords in NEWS_FLAG_RULES:
        if any(keyword in normalized for keyword in keywords):
            flags.append(label)
    return flags


def summarize_news_flags(headlines) -> list[str]:
    counts: Counter[str] = Counter()
    for headline in headlines:
        title = getattr(headline, "title", str(headline))
        counts.update(classify_headline(title))
    return [f"{label} {counts[label]}건" for label, _ in NEWS_FLAG_RULES if counts[label]]
