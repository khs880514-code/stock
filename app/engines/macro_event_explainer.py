from __future__ import annotations

from datetime import datetime, timedelta

from app.config import AppConfig
from app.models import MacroSnapshot, MacroTrigger, PortfolioSnapshot, Source


def detect_macro_triggers(snapshot: MacroSnapshot, config: AppConfig) -> list[MacroTrigger]:
    triggers: list[MacroTrigger] = []
    fx = snapshot.get("USD_KRW")
    if fx:
        fx_change = fx.change_pct or 0.0
        crossed = fx.value >= 1500 or fx.value >= 1400 or fx.value >= 1300
        if abs(fx_change) >= 1.0 or crossed:
            triggers.append(
                MacroTrigger(
                    trigger_type="FX",
                    title=f"USD/KRW {fx.value:,.1f}",
                    observed_value=fx.value,
                    reason="원달러 환율 변동 또는 주요 레벨 통과",
                    source=fx.source,
                    occurred_at=snapshot.timestamp,
                )
            )

    us10y = snapshot.get("US10Y")
    if us10y and us10y.previous_value is not None:
        bp_change = (us10y.value - us10y.previous_value) * 100
        if abs(bp_change) >= 10:
            triggers.append(
                MacroTrigger(
                    trigger_type="US10Y",
                    title=f"US 10Y {bp_change:+.0f}bp",
                    observed_value=us10y.value,
                    reason="미국 10년물 금리 10bp 이상 변동",
                    source=us10y.source,
                    occurred_at=snapshot.timestamp,
                )
            )

    vix = snapshot.get("VIX")
    if vix and (vix.value >= 25 or vix.value >= 35):
        triggers.append(
            MacroTrigger(
                trigger_type="VIX",
                title=f"VIX {vix.value:.1f}",
                observed_value=vix.value,
                reason="VIX 임계값 진입",
                source=vix.source,
                occurred_at=snapshot.timestamp,
            )
        )

    wti = snapshot.get("WTI")
    if wti and wti.change_pct is not None and abs(wti.change_pct) >= 5.0:
        triggers.append(
            MacroTrigger(
                trigger_type="WTI",
                title=f"WTI {wti.change_pct:+.1f}%",
                observed_value=wti.value,
                reason="WTI 5% 이상 변동",
                source=wti.source,
                occurred_at=snapshot.timestamp,
            )
        )
    return triggers[: config.trigger_daily_cap]


def explain_macro_event(trigger: MacroTrigger, portfolio: PortfolioSnapshot) -> str:
    source_line = _source_line(trigger.source)
    exposure = _portfolio_exposure(portfolio, trigger.trigger_type)
    if trigger.trigger_type == "FX":
        mechanism = (
            "교과서적으로는 원화 약세가 달러 자산의 원화 환산가치를 높일 수 있다. "
            "반대로 수입물가와 금리 부담이 커지면 위험자산 선호가 약해질 수 있다."
        )
    elif trigger.trigger_type == "US10Y":
        mechanism = (
            "교과서적으로는 장기금리 상승이 성장주의 할인율 부담을 키울 수 있다. "
            "반대로 경기 기대가 동반된 금리 상승이면 이익 전망이 이를 일부 상쇄할 수 있다."
        )
    elif trigger.trigger_type == "WTI":
        mechanism = (
            "교과서적으로는 유가 상승이 인플레이션과 비용 부담을 키울 수 있다. "
            "반대로 에너지 수요가 견조하다는 신호라면 경기 해석은 달라질 수 있다."
        )
    else:
        mechanism = (
            "교과서적으로는 변동성 확대가 위험자산 할인 압력을 높일 수 있다. "
            "반대로 이미 과도한 공포가 반영된 구간에서는 반응이 짧게 끝날 수 있다."
        )

    return "\n".join(
        [
            f"■ 오늘의 시장 이벤트: {trigger.title}",
            "",
            "1. 무슨 일이 있었나 (사실)",
            f"- {trigger.reason}: 관측값 {trigger.observed_value:g}. {source_line}",
            "",
            "2. 교과서적 메커니즘",
            f"- {mechanism}",
            "- 어느 쪽 영향이 우세할지는 원인과 동시 지표에 따라 달라진다.",
            "",
            "3. 과거 비슷한 사례",
            "- 과거 같은 변수 변동 후에도 결과는 금리, 물가, 실적 기대 조합에 따라 달랐다.",
            "- 이번 상황에 같은 결론을 적용하지 않는다.",
            "",
            "4. 본인 포지션 연결",
            f"- {exposure}",
            "- 행동 권고는 큰 결정을 미루고 다음 정시 브리핑에서 재확인하는 수준으로 제한한다.",
        ]
    )


def trigger_frequency_review_needed(triggers: list[MacroTrigger], now: datetime, config: AppConfig) -> bool:
    cutoff = now - timedelta(days=7)
    recent = [trigger for trigger in triggers if cutoff <= trigger.occurred_at <= now]
    return len(recent) >= config.trigger_weekly_review_count


def _source_line(source: Source | None) -> str:
    if source is None:
        return "출처: mock data"
    return f"출처: {source.title} ({source.url})"


def _portfolio_exposure(portfolio: PortfolioSnapshot, trigger_type: str) -> str:
    tickers = ", ".join(holding.ticker for holding in portfolio.holdings) or "보유 종목 없음"
    if trigger_type == "FX":
        return f"달러 표시 보유 종목({tickers})은 원화 환산가치와 환율 변동에 노출된다."
    if trigger_type == "US10Y":
        return f"기술주와 반도체 비중이 있으면({tickers}) 할인율 변화에 노출된다."
    if trigger_type == "WTI":
        return f"유가 급변은 물가와 금리 기대를 통해 보유 성장주({tickers})에 간접 영향을 줄 수 있다."
    return f"보유 종목({tickers})은 변동성 확대 시 동반 가격 변동에 노출될 수 있다."

