from __future__ import annotations

from app.data.news_collector import Headline
from app.engines.red_team import build_bear_case
from app.llm.output_filter import validate_llm_assist
from app.models import ConfidenceLabel, DataQuality, LlmAssist


class DeterministicAnalyst:
    """Local stand-in for optional LLM calls.

    It produces schema-shaped assist text for demo and tests. A real LLM adapter
    can be added behind the same method boundaries after API keys are configured.
    """

    def classify_headlines(self, ticker: str, headlines: list[Headline]) -> LlmAssist:
        reason = [headline.title for headline in headlines if headline.ticker.upper() == ticker.upper()]
        sources = [headline.source for headline in headlines if headline.ticker.upper() == ticker.upper()]
        assist = LlmAssist(
            ticker=ticker,
            reason=reason[:3] or ["조건부 헤드라인 없음"],
            next_check="다음 정시 브리핑에서 거래량과 공시 여부 재확인",
            confidence_label=ConfidenceLabel.MEDIUM,
            data_quality=DataQuality(
                price_data="HIGH",
                portfolio_data="NOT_USED",
                event_data="NOT_USED",
                news_context="MEDIUM" if sources else "NOT_USED",
            ),
            sources=sources,
        )
        result = validate_llm_assist(assist)
        if not result.ok:
            raise ValueError("; ".join(result.errors))
        return assist

    def review_reason(self, ticker: str, reason_text: str, sector_tag: str) -> LlmAssist:
        bear_case, leading_indicators, sources = build_bear_case(ticker, sector_tag)
        reason = [
            "입력 사유는 가격 움직임, 외부 영향, 선호 기업 편향 여부를 분리해 재검토해야 함",
            f"사용자 입력 요약: {reason_text[:120]}",
        ]
        assist = LlmAssist(
            ticker=ticker,
            reason=reason,
            bear_case=bear_case,
            do_not_buy_if=leading_indicators,
            next_check="정시 브리핑과 공시 링크로 사실관계 재확인",
            confidence_label=ConfidenceLabel.MEDIUM,
            data_quality=DataQuality(price_data="HIGH", portfolio_data="HIGH", event_data="MEDIUM"),
            sources=sources,
        )
        result = validate_llm_assist(assist)
        if not result.ok:
            raise ValueError("; ".join(result.errors))
        return assist

