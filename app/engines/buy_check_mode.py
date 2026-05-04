from __future__ import annotations

from datetime import datetime, timedelta

from app.config import AppConfig
from app.data.news_store import NewsStore
from app.data.price_history import PriceHistoryStore
from app.data.ticker_sensitivity import TickerSensitivityStore
from app.data.watchlist_store import WatchlistStore
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
    PostDropContext,
    PriceHistoryBar,
    TradeEntry,
)
from app.rules import holiday_gap_setup, post_drop_chase, post_run_decomposition
from app.rules.decision_protection import active_blackout, detect_regret_chase, suggest_blackout
from app.rules.post_run_news_mapping import classify_post_run_news


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
    cap_ratios: list[float] = []
    holding = find_holding(portfolio, request.ticker)
    sector_tag = holding.sector_tag if holding else DEFAULT_SECTOR_BY_TICKER.get(request.ticker, "UNKNOWN")
    sensitivity = _safe_sensitivity(config, request.ticker)
    watch_item = _safe_watch_item(config, request.ticker)
    blackout = active_blackout(watch_item, now.date())
    blackout_active = bool(blackout and blackout.active)

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

    if blackout_active and blackout:
        blockers.append(
            f"decision_protection: {request.ticker} 관찰 블랙아웃 {blackout.do_not_watch_until}까지"
        )
        support_notes.append("[decision_protection] 블랙아웃 중에는 가격/갭/급등분해 세부 신호를 숨깁니다.")
        post_drop_context = PostDropContext(triggered=False, bypass_reason="blackout")
        holiday_gap_signal = None
        relative_weakness_signal = None
        post_run_context = None
        regret_pattern = None
    else:
        full_price_history = price_history or _safe_history(config, request.ticker, now)
        post_drop_context = post_drop_chase.evaluate(
            ticker=request.ticker,
            amount_krw=request.desired_amount_krw,
            fomo=request.fomo_score,
            portfolio=portfolio,
            price_history=full_price_history,
            earnings_dates=earnings_dates or [event.event_time.date() for event in events],
            today=now.date(),
            config=config,
        )
        if post_drop_context.triggered and post_drop_context.explanation:
            support_notes.append(post_drop_context.explanation)
            if post_drop_context.cap_ratio is not None:
                cap_ratios.append(post_drop_context.cap_ratio)
            if post_drop_context.action == "block":
                blockers.append("post_drop_chase: 최근 급락 후 추격매수 차단")

        kospi_history = _safe_history(config, "^KS11", now)
        us_market_history = _safe_history(config, "^GSPC", now) or _safe_history(config, "SPY", now)
        us_sector_history = (
            _safe_history(config, sensitivity.us_sector_proxy_symbol, now)
            if sensitivity and sensitivity.us_sector_proxy_symbol
            else []
        )
        gap_days, us_gap_return = _holiday_gap_inputs(full_price_history, us_market_history, now)
        holiday_gap_signal = holiday_gap_setup.evaluate(
            ticker=request.ticker,
            today=now.date(),
            sensitivity=sensitivity,
            gap_days=gap_days,
            us_accumulated_return_pct=us_gap_return,
            config=config,
        )
        if holiday_gap_signal.explanation:
            support_notes.append(holiday_gap_signal.explanation)
        if holiday_gap_signal.triggered and holiday_gap_signal.cap_ratio is not None:
            cap_ratios.append(holiday_gap_signal.cap_ratio)

        relative_weakness_signal = holiday_gap_setup.evaluate_relative_weakness(
            ticker=request.ticker,
            ticker_history=full_price_history,
            kospi_history=kospi_history,
            today=now.date(),
        )
        if relative_weakness_signal.triggered and relative_weakness_signal.explanation:
            support_notes.append(relative_weakness_signal.explanation)

        latest_news = _safe_news(config, request.ticker)
        post_run_context = post_run_decomposition.evaluate(
            ticker=request.ticker,
            today=now.date(),
            ticker_history=full_price_history,
            kospi_history=kospi_history,
            us_sector_history=us_sector_history,
            us_market_history=us_market_history,
            sensitivity=sensitivity,
            news_categories=classify_post_run_news(latest_news),
            news_available=bool(latest_news),
            config=config,
        )
        if post_run_context.triggered and post_run_context.explanation:
            support_notes.append(post_run_context.explanation)
        if post_run_context.triggered and post_run_context.cap_ratio is not None:
            cap_ratios.append(post_run_context.cap_ratio)

        regret_pattern = detect_regret_chase(
            ticker=request.ticker,
            now=now,
            db_path=config.db_path,
            config=config,
        )
        if regret_pattern.triggered and regret_pattern.explanation:
            blockers.append(regret_pattern.explanation)

    bear_case, do_not_buy_if, sources = build_bear_case(request.ticker, sector_tag)
    if blockers:
        decision = AlertDecision(
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
            ticker_sensitivity_used=sensitivity,
            holiday_gap_signal=holiday_gap_signal,
            relative_weakness_signal=relative_weakness_signal,
            post_run_decomposition=post_run_context,
            regret_pattern=regret_pattern,
        )
        return _with_blackout_suggestion(decision, now, config)

    max_amount = min(
        request.desired_amount_krw,
        limit_check.capped_amount_krw,
        max(portfolio.cash_krw - config.min_cash_krw, 0),
    )
    if cap_ratios:
        max_amount = int(max_amount * min(cap_ratios))
        support_notes.append(f"사용자 확인 필요: 조정 후 최대 검토 금액 {max_amount:,}원")
    decision = AlertDecision(
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
        ticker_sensitivity_used=sensitivity,
        holiday_gap_signal=holiday_gap_signal,
        relative_weakness_signal=relative_weakness_signal,
        post_run_decomposition=post_run_context,
        regret_pattern=regret_pattern,
    )
    return _with_blackout_suggestion(decision, now, config)


def _safe_sensitivity(config: AppConfig, ticker: str):
    try:
        return TickerSensitivityStore(config.db_path).get(ticker)
    except Exception:
        return None


def _safe_watch_item(config: AppConfig, ticker: str):
    try:
        return WatchlistStore(config.db_path).get(ticker)
    except Exception:
        return None


def _safe_history(config: AppConfig, ticker: str | None, now: datetime) -> list[PriceHistoryBar]:
    if not ticker:
        return []
    try:
        return PriceHistoryStore(config.db_path).get_window(
            ticker,
            now.date() - timedelta(days=180),
            now.date(),
        )
    except Exception:
        return []


def _safe_news(config: AppConfig, ticker: str):
    try:
        return NewsStore(config.db_path).latest(ticker, limit=20)
    except Exception:
        return []


def _holiday_gap_inputs(
    ticker_history: list[PriceHistoryBar], us_market_history: list[PriceHistoryBar], now: datetime
) -> tuple[int, float | None]:
    eligible = [bar for bar in ticker_history if bar.date <= now.date()]
    if not eligible:
        return 0, None
    eligible.sort(key=lambda bar: bar.date)
    last_local_date = eligible[-1].date
    gap_days = (now.date() - last_local_date).days
    if gap_days <= 0:
        return 0, 0.0
    us_rows = [bar for bar in us_market_history if last_local_date <= bar.date <= now.date()]
    us_rows.sort(key=lambda bar: bar.date)
    if len(us_rows) < 2 or us_rows[0].close <= 0:
        return gap_days, None
    return gap_days, (us_rows[-1].close - us_rows[0].close) / us_rows[0].close


def _with_blackout_suggestion(decision: AlertDecision, now: datetime, config: AppConfig) -> AlertDecision:
    suggested = suggest_blackout(decision, now, config)
    if suggested is None:
        return decision
    return decision.model_copy(update={"blackout_suggested": suggested})


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
