from __future__ import annotations

from app.engines.stock_screener import ScreenerCandidate
from app.web.candidate_explainer import explain_candidate, review_questions


def test_explain_pass_candidate_in_beginner_language():
    item = ScreenerCandidate(
        ticker="PASS",
        company_name="Pass Corp",
        market="US",
        sector_tag="AI",
        status="PASS",
        score=6,
        data_points=6,
        reasons=["PER 18 <= 25", "ROE 15 >= 8", "3M momentum 4 >= 0"],
    )

    why, next_step = explain_candidate(item, {"news": 3, "filings": 1, "research": 1})

    assert "검토 후보" in why
    assert "가격 부담" in why
    assert "수익성" in why
    assert "4 매수 전 점검" in next_step


def test_review_questions_start_with_summary_and_missing_action():
    item = ScreenerCandidate(
        ticker="WATCH",
        company_name="Watch Corp",
        market="KR",
        sector_tag="AI",
        status="WATCH",
        score=2,
        data_points=2,
        missing_metrics=["Forward PER", "PBR", "ROE"],
    )

    questions = review_questions(item, {"news": 0, "filings": 0, "research": 0})

    assert questions[0] == "좋아 보이는 부분은 있지만 핵심 정보가 부족합니다."
    assert "Forward PER" in questions[1]
    assert any("뉴스 업데이트" in question for question in questions)
