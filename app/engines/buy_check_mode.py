from __future__ import annotations

from datetime import datetime, timedelta

from app.config import AppConfig
from app.engines.event_risk import events_within_window
from app.engines.overconfidence_detector import detect_overconfidence
from app.engines.portfolio_risk import (
    evaluate_buy_limits,
    find_holding,
    is_loss_averaging_attempt,
)
from app.engines.red_team import build_bear_case
from app.engines.self_report_check import evaluate_self_report_consistency
from app.models import (
    Action,
    AlertDecision,
    BuyReviewRequest,
    ConfidenceLabel,
    DataQuality,
    Event,
    PortfolioSnapshot,
    PriceHistoryBar,
    TradeEntry,
)
from app.rules import post_drop_chase


DEFAULT_SECTOR_BY_TICKER = {
    "QQQ": "CORE_ETF",
    "SMH": "AI_SEMICONDUCTOR",
    "AAPL": "BIG_TECH",
    "AMD": "AI_SEMICONDUCTOR",
    "MVST": "SPECULATIVE_LOSS",
}


def review_buy_request(
    request: BuyReviewRequest,
    portfolio: PortfolioSnapshot,
    events: list[Event],
    recent_trades: list[TradeEntry],
    now: datetime,
    config: AppConfig,
    amount_bought_today_krw: int = 0,
    price_history: list[PriceHistoryBar] | None = None,
    earnings_dates: list | None = None,
) -> AlertDecision:
    blockers: list[str] = []
    support_notes: list[str] = []
    holding = find_holding(portfolio, request.ticker)
    sector_tag = holding.sector_tag if holding else DEFAULT_SECTOR_BY_TICKER.get(request.ticker, "UNKNOWN")

    if "market" in request.price_type.lower() or "시장가" in request.price_type:
        blockers.append("시장가 방식 입력은 차단")

    if request.fomo_score >= config.fomo_block_threshold:
        blockers.append(f"FOMO 점수 {request.fomo_score}/10: 차단 임계값 이상")
    elif request.fomo_score >= config.fomo_wait_threshold:
        blockers.append(f"FOMO 점수 {request.fomo_score}/10: 24시간 대기")

    if request.friend_influence_score >= config.influence_block_threshold:
        blockers.append(f"외부 영향 점수 {request.friend_influence_score}/10: 차단 임계값 이상")

    mismatch_blockers, mismatch_notes = evaluate_self_report_consistency(request)
    blockers.extend(mismatch_blockers)
    support_notes.extend(mismatch_notes)

    language = detect_overconfidence(request.reason_text)
    if language.level == "HIGH":
        blockers.append(f"과신 언어 HIGH 감지: {', '.join(language.matches)}")
    elif language.level == "MEDIUM":
        support_notes.append(f"과신 언어 MEDIUM 감지: {', '.join(language.matches)}")

    if events_within_window(events, request.ticker, now, config.earnings_block_days):
        blockers.append(f"실적 발표 D-{config.earnings_block_days} 이내")

    if _same_ticker_trade_within(recent_trades, request.ticker, now, days=7):
        blockers.append("1주일 내 같은 종목 매수 이력 존재")

    if is_loss_averaging_attempt(holding, config):
        blockers.append("손실 폭이 큰 종목의 추가 투입 시도")

    limit_check = evaluate_buy_limits(
        portfolio=portfolio,
        ticker=request.ticker,
        amount_krw=request.desired_amount_krw,
        sector_tag=sector_tag,
        config=config,
        amount_bought_today_krw=amount_bought_today_krw,
    )
    blocking_limit_reasons = [
        reason for reason in limit_check.reasons if "초과" in reason or "미만" in reason
    ]
    blockers.extend(blocking_limit_reasons)
    support_notes.extend([reason for reason in limit_check.reasons if reason not in blocking_limit_reasons])

    post_drop_context = post_drop_chase.evaluate(
        ticker=request.ticker,
        amount_krw=request.desired_amount_krw,
        fomo=request.fomo_score,
        portfolio=portfolio,
        price_history=price_history or [],
        earnings_dates=earnings_dates or [event.event_time.date() for event in events],
        today=now.date(),
        config=config,
    )
    if post_drop_context.triggered and post_drop_context.explanation:
        support_notes.append(post_drop_context.explanation)
        if post_drop_context.action == "block":
            blockers.append("post_drop_chase: 최근 급락 후 추격매수 차단")

    bear_case, do_not_buy_if, sources = build_bear_case(request.ticker, sector_tag)
    if blockers:
        return AlertDecision(
            ticker=request.ticker,
            action=Action.NO_TRADE,
            max_amount_krw=0,
            reason=blockers + support_notes,
            bear_case=bear_case,
            do_not_buy_if=do_not_buy_if,
            next_check=_next_check(blockers),
            confidence_label=ConfidenceLabel.MEDIUM,
            data_quality=DataQuality(price_data="HIGH", portfolio_data="HIGH", event_data="HIGH"),
            llm_assisted_fields=["bear_case", "do_not_buy_if"],
            sources=sources,
            post_drop_context=post_drop_context,
        )

    max_amount = min(
        request.desired_amount_krw,
        limit_check.capped_amount_krw,
        max(portfolio.cash_krw - config.min_cash_krw, 0),
    )
    if post_drop_context.triggered and post_drop_context.cap_ratio is not None:
        max_amount = int(max_amount * post_drop_context.cap_ratio)
        support_notes.append(f"사용자 확인 필요: 조정 후 최대 검토 금액 {max_amount:,}원")
    return AlertDecision(
        ticker=request.ticker,
        action=Action.SMALL_BUY_CANDIDATE,
        max_amount_krw=max_amount,
        reason=support_notes or ["룰엔진 차단 조건 없음. 소액 후보로만 표시"],
        bear_case=bear_case,
        do_not_buy_if=do_not_buy_if,
        next_check="정시 브리핑에서 가격, 거래량, 이벤트 일정을 다시 확인",
        confidence_label=ConfidenceLabel.MEDIUM,
        data_quality=DataQuality(price_data="HIGH", portfolio_data="HIGH", event_data="HIGH"),
        llm_assisted_fields=["bear_case", "do_not_buy_if"],
        sources=sources,
        post_drop_context=post_drop_context,
    )


def _same_ticker_trade_within(
    trades: list[TradeEntry], ticker: str, now: datetime, days: int
) -> bool:
    normalized = ticker.upper()
    cutoff = now - timedelta(days=days)
    return any(
        trade.ticker == normalized and trade.action.upper() == "BUY" and cutoff <= trade.timestamp <= now
        for trade in trades
    )


def _next_check(blockers: list[str]) -> str:
    if any("실적" in blocker for blocker in blockers):
        return "실적 발표 후 가격과 가이던스 반응 확인"
    if any("FOMO" in blocker or "과신" in blocker or "불일치" in blocker for blocker in blockers):
        return "24시간 뒤 같은 사유를 다시 읽고 필요성 재검토"
    if any("손실" in blocker for blocker in blockers):
        return "기업 체질 개선 근거가 공시로 확인될 때까지 보류"
    return "다음 정시 브리핑에서 조건 재확인"
