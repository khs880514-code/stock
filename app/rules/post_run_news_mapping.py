from __future__ import annotations

from app.data.news_store import NewsHeadline


NEWS_CATEGORY_WEIGHTS = {
    "earnings_surprise": 0.04,
    "direct_government_policy": 0.03,
    "large_contract": 0.03,
    "deregulation": 0.02,
    "competitor_bad_news": 0.015,
    "analyst_target_upgrade": 0.02,
}


def classify_post_run_news(headlines: list[NewsHeadline]) -> list[str]:
    categories: set[str] = set()
    for item in headlines:
        text = item.title.lower()
        if any(keyword in text for keyword in ["earnings beat", "surprise profit", "실적 서프라이즈", "어닝 서프라이즈"]):
            categories.add("earnings_surprise")
        if any(keyword in text for keyword in ["government", "policy", "subsidy", "정부", "정책", "보조금"]):
            categories.add("direct_government_policy")
        if any(keyword in text for keyword in ["contract", "supply deal", "수주", "공급 계약", "계약"]):
            categories.add("large_contract")
        if any(keyword in text for keyword in ["deregulation", "규제 완화", "완화"]):
            categories.add("deregulation")
        if any(keyword in text for keyword in ["competitor", "rival", "경쟁사", "경쟁업체"]):
            categories.add("competitor_bad_news")
        if any(keyword in text for keyword in ["target price", "price target", "upgrade", "목표가", "상향"]):
            categories.add("analyst_target_upgrade")
    return sorted(categories)


def explained_news_return(categories: list[str]) -> float:
    return sum(NEWS_CATEGORY_WEIGHTS.get(category, 0.0) for category in set(categories))
