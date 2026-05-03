from __future__ import annotations

from app.data.macro_collector import MockMacroCollector
from app.data.news_collector import MockNewsCollector
from app.data.price_provider import PriceProvider
from app.llm.analyst import DeterministicAnalyst
from app.models import MacroSnapshot, PortfolioSnapshot


def build_morning_briefing(
    portfolio: PortfolioSnapshot,
    price_provider: PriceProvider,
    macro: MacroSnapshot | None = None,
) -> str:
    macro = macro or MockMacroCollector().collect()
    tickers = [holding.ticker for holding in portfolio.holdings]
    lines: list[str] = ["■ 06:00 미장 마감 후 브리핑", ""]
    lines.append("보유 종목 어제 결과")
    notable: list[str] = []
    for ticker in tickers:
        price = price_provider.get_current_price(ticker)
        marker = " [!]" if price.volume_ratio >= 1.5 else ""
        lines.append(
            f"- {ticker}: {price.current_price:g}{price.currency}, {price.change_pct:+.1f}%, "
            f"거래량 {price.volume_ratio:.2f}배{marker}"
        )
        if price.volume_ratio >= 1.5 or abs(price.change_pct) >= 5.0:
            notable.append(ticker)

    lines.extend(["", "매크로 한 줄"])
    for key in ["SP500", "NASDAQ", "VIX", "US10Y", "USD_KRW", "WTI"]:
        indicator = macro.get(key)
        if not indicator:
            continue
        ma = f", 30일 평균 {indicator.moving_average_30d:g}" if indicator.moving_average_30d else ""
        change = f", {indicator.change_pct:+.1f}%" if indicator.change_pct is not None else ""
        lines.append(f"- {indicator.name}: {indicator.value:g}{indicator.unit}{change}{ma}")

    lines.extend(["", "이벤트 캘린더", "- 보유 종목 실적 일정은 08:30 브리핑에서 확인"])
    if notable:
        headlines = MockNewsCollector().collect(notable)
        headline_tickers = {headline.ticker.upper() for headline in headlines}
        analyst = DeterministicAnalyst()
        classified = [ticker for ticker in notable if ticker.upper() in headline_tickers]
        if classified:
            lines.extend(["", "조건부 헤드라인 분류"])
        for ticker in classified[:2]:
            assist = analyst.classify_headlines(ticker, headlines)
            lines.append(f"- {ticker}: " + " / ".join(assist.reason[:3]))
            if assist.sources:
                lines.append(f"  출처: {assist.sources[0].url}")
    return _limit("\n".join(lines))


def _limit(message: str, limit: int = 1500) -> str:
    return message if len(message) <= limit else message[: limit - 20].rstrip() + "\n...(축약)"
