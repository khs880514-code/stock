from app.llm.output_filter import validate_llm_assist
from app.models import LlmAssist, Source


def test_filter_blocks_missing_sources():
    assist = LlmAssist(ticker="AMD", reason=["사실 요약"])
    result = validate_llm_assist(assist)
    assert not result.ok
    assert any("출처" in error for error in result.errors)


def test_filter_blocks_trade_directive_and_numeric_confidence():
    assist = LlmAssist(
        ticker="AMD",
        reason=["매수하세요. confidence: 0.82"],
        sources=[Source(title="AMD IR", url="https://ir.amd.com/")],
    )
    result = validate_llm_assist(assist)
    assert not result.ok
    assert any("매수/매도" in error for error in result.errors)
    assert any("숫자형" in error for error in result.errors)


def test_filter_accepts_sourced_neutral_text():
    assist = LlmAssist(
        ticker="AMD",
        reason=["거래량이 30일 평균보다 높음"],
        bear_case=["기대치가 높으면 실적 후 변동성이 커질 수 있음"],
        sources=[Source(title="AMD IR", url="https://ir.amd.com/")],
    )
    assert validate_llm_assist(assist).ok

