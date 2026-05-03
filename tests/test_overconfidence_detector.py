from app.engines.overconfidence_detector import detect_overconfidence


def test_overconfidence_high_for_assertive_earnings_text():
    result = detect_overconfidence("메타 실적날 무조건 폭등한다")
    assert result.level == "HIGH"
    assert "무조건" in result.matches

