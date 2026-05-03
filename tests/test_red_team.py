from app.engines.red_team import build_bear_case


def test_red_team_returns_bear_cases_and_sources():
    bear_case, indicators, sources = build_bear_case("AMD", "AI_SEMICONDUCTOR")
    assert len(bear_case) >= 3
    assert len(indicators) >= 3
    assert sources

