from app.engines.news_flags import classify_headline, summarize_news_flags


def test_classify_headline_flags_common_risk_contexts():
    flags = classify_headline("AMD shares surge after analyst price target upgrade")
    assert "모멘텀/과열" in flags
    assert "애널리스트/목표가" in flags


def test_summarize_news_flags_counts_by_label():
    headlines = [
        type("Headline", (), {"title": "Company faces SEC investigation"})(),
        type("Headline", (), {"title": "Company faces lawsuit"})(),
        type("Headline", (), {"title": "Company raises guidance after earnings"})(),
    ]
    summary = summarize_news_flags(headlines)
    assert "규제/소송 2건" in summary
    assert "실적/가이던스 1건" in summary
