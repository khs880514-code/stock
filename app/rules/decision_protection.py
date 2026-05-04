from __future__ import annotations

from datetime import date, datetime, timedelta

from app.config import AppConfig
from app.data.buy_check_log import BuyCheckLogStore
from app.data.price_history import PriceHistoryStore
from app.data.watchlist_store import WatchlistItem
from app.models import Action, AlertDecision, BlackoutInfo, RegretChasePattern


RULE_ID = "decision_protection"
RULE_VERSION = "decision_protection_v1.0"


def active_blackout(item: WatchlistItem | None, today: date) -> BlackoutInfo | None:
    if item is None or not item.do_not_watch_until:
        return None
    until = date.fromisoformat(item.do_not_watch_until)
    if until < today:
        return BlackoutInfo(ticker=item.ticker, active=False, do_not_watch_until=until)
    set_at = datetime.fromisoformat(item.blackout_set_at) if item.blackout_set_at else None
    return BlackoutInfo(
        ticker=item.ticker,
        active=True,
        do_not_watch_until=until,
        reason=item.blackout_reason or "",
        set_at=set_at,
    )


def suggest_blackout(decision: AlertDecision, now: datetime, config: AppConfig) -> BlackoutInfo | None:
    if not config.decision_protection_enabled:
        return None
    if decision.action not in {Action.NO_TRADE, Action.WATCH}:
        return None
    reasons = " ".join(decision.reason)
    if "FOMO" not in reasons and "과신" not in reasons and "post_drop" not in reasons:
        return None
    until = now.date() + timedelta(days=config.blackout_default_days)
    return BlackoutInfo(
        ticker=decision.ticker,
        active=False,
        do_not_watch_until=until,
        reason="매수 금지/대기 직후 가격 확인으로 후회 추격이 생기는 것을 막기 위한 관찰 블랙아웃 제안",
        set_at=now,
    )


def detect_regret_chase(
    *,
    ticker: str,
    now: datetime,
    db_path,
    config: AppConfig,
) -> RegretChasePattern:
    if not config.decision_protection_enabled:
        return RegretChasePattern(triggered=False)

    since = now - timedelta(days=config.regret_chase_lookback_days)
    entries = BuyCheckLogStore(db_path).recent_for_ticker(ticker, since)
    latest_price = PriceHistoryStore(db_path).latest_bar(ticker)
    if latest_price is None:
        return RegretChasePattern(triggered=False)

    for entry in entries:
        if entry.action not in {Action.NO_TRADE.value, Action.WATCH.value}:
            continue
        if not entry.price_at_decision or entry.price_at_decision <= 0:
            continue
        gain = (latest_price.close - entry.price_at_decision) / entry.price_at_decision
        if gain >= config.regret_chase_gain_pct:
            return RegretChasePattern(
                triggered=True,
                last_decision_at=entry.decision_at,
                last_action=entry.action,
                price_then=entry.price_at_decision,
                price_now=latest_price.close,
                gain_since_decision_pct=gain,
                explanation=(
                    f"[decision_protection] 최근 {entry.action} 판단 이후 가격이 {gain:.1%} 상승했습니다. "
                    "지금 매수 검토는 놓친 기회 보상 심리가 섞였는지 먼저 확인해야 합니다."
                ),
            )
    return RegretChasePattern(triggered=False)
