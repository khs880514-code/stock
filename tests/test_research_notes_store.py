from app.data.research_notes_store import ResearchNote, ResearchNotesStore


def test_research_notes_store_filters_by_ticker(tmp_path):
    store = ResearchNotesStore(tmp_path / "research.sqlite3")
    note_id = store.add(
        ResearchNote(
            tickers=["AMD", "AAPL"],
            source_type="NOTEBOOKLM",
            source_name="김지윤의 지식플레이",
            source_url="https://example.com",
            reliability="HIGH",
            summary="반도체 지정학 리스크 요약",
            counter_points="정책 변화가 이미 가격에 반영됐을 수 있음",
            check_questions="원문 출처와 날짜가 맞나?",
        )
    )
    assert note_id > 0
    latest = store.latest("AMD")
    assert len(latest) == 1
    assert latest[0].source_type == "NOTEBOOKLM"
    assert latest[0].reliability == "HIGH"
    assert "가격에 반영" in latest[0].counter_points
    assert "원문 출처" in latest[0].check_questions
