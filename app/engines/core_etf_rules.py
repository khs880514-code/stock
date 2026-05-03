from __future__ import annotations

from app.models import Action, AlertDecision, DataQuality, MacroSnapshot, PriceSnapshot


CORE_ETF_WHITELIST = {"QQQ", "SMH"}


def evaluate_core_etf(ticker: str, price: PriceSnapshot, macro: MacroSnapshot) -> AlertDecision:
    normalized = ticker.upper()
    vix = macro.get("VIX")
    wti = macro.get("WTI")
    reasons: list[str] = []
    action = Action.WATCH
    max_amount = 0

    if normalized == "QQQ" and price.change_pct <= -3.0:
        if vix and vix.value < 25:
            action = Action.SMALL_BUY_CANDIDATE
            max_amount = 1_000_000
            reasons.append("QQQ가 -3% 이상 하락했고 VIX가 25 미만")
        else:
            action = Action.NO_TRADE
            reasons.append("QQQ 하락과 변동성 확대가 동시에 관찰됨")

    elif normalized == "SMH" and price.change_pct <= -5.0:
        if wti and wti.change_pct is not None and wti.change_pct >= 5.0:
            action = Action.NO_TRADE
            reasons.append("SMH -5% 이상 하락과 WTI +5% 이상 변동이 겹침")
        else:
            action = Action.SMALL_BUY_CANDIDATE
            max_amount = 1_000_000
            reasons.append("SMH가 -5% 이상 하락했으나 유가 급등 조건은 없음")
    else:
        reasons.append("코어 ETF 눌림 조건 미충족")

    return AlertDecision(
        ticker=normalized,
        action=action,
        max_amount_krw=max_amount,
        reason=reasons,
        next_check="다음 정시 브리핑에서 가격과 변동성 재확인",
        data_quality=DataQuality(price_data="HIGH", portfolio_data="NOT_USED", event_data="NOT_USED"),
    )
