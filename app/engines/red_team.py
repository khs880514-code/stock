from __future__ import annotations

from app.models import Source


def build_bear_case(ticker: str, sector_tag: str) -> tuple[list[str], list[str], list[Source]]:
    normalized = ticker.upper()
    sources = [
        Source(
            title="SEC EDGAR company filings",
            url="https://www.sec.gov/edgar/search/",
            published_at="",
        )
    ]
    if sector_tag in {"SEMICONDUCTOR", "AI_SEMICONDUCTOR"} or normalized in {"AMD", "SMH"}:
        return (
            [
                "AI 수요가 좋아도 기대치가 이미 가격에 반영됐을 수 있음",
                "미국 10년물 금리 상승은 장기 성장주의 할인율 부담을 키울 수 있음",
                "공급망 또는 재고 조정이 실적 가이던스에 영향을 줄 수 있음",
            ],
            [
                "실적 발표 전후 변동성 확대",
                "미국 10년물 금리 급등",
                "섹터 ETF 거래량 급증과 가격 하락 동시 발생",
            ],
            sources,
        )
    if sector_tag == "BIG_TECH" or normalized == "AAPL":
        return (
            [
                "대형 기술주는 금리와 밸류에이션 변화에 민감할 수 있음",
                "제품 사이클 기대가 약해지면 주가 반응이 제한될 수 있음",
                "이미 높은 비중이면 포트폴리오 변동성이 확대될 수 있음",
            ],
            [
                "매출 성장률 둔화",
                "마진 가이던스 하향",
                "동일 테마 비중 상승",
            ],
            sources,
        )
    return (
        [
            "최근 반등이 기업 체질 개선보다 단기 수급일 수 있음",
            "손실 폭이 큰 종목은 평단 회복 심리가 판단을 흐릴 수 있음",
            "거래량 급증 후 변동성이 빠르게 축소될 수 있음",
        ],
        [
            "전일 대비 급등 후 거래량 둔화",
            "추가 공시 없이 가격만 반등",
            "기존 손실률이 큰 상태에서 추가 투입 욕구 증가",
        ],
        sources,
    )

