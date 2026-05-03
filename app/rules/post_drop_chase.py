from __future__ import annotations

from datetime import date, datetime

from app.config import AppConfig
from app.engines.core_etf_rules import CORE_ETF_WHITELIST
from app.models import Holding, PortfolioSnapshot, PostDropContext, PriceHistoryBar


RULE_ID = "post_drop_chase"
RULE_VERSION = "post_drop_v1.0"


def evaluate(
    ticker: str,
    amount_krw: int,
    fomo: int | None,
    portfolio: PortfolioSnapshot,
    price_history: list[PriceHistoryBar],
    earnings_dates: list[date],
    today: date,
    config: AppConfig,
) -> PostDropContext:
    normalized = ticker.upper().strip()
    if not config.post_drop_rule_enabled:
        return PostDropContext(triggered=False, bypass_reason="disabled")

    if normalized in CORE_ETF_WHITELIST:
        return PostDropContext(triggered=False, bypass_reason="core_etf")

    holding = _find_holding(portfolio, normalized)
    held_days = _held_days(holding, today)
    existing_value = _position_value_krw(holding, config.fx_usd_krw)
    if (
        held_days >= config.post_drop_long_hold_days
        and existing_value > 0
        and amount_krw <= existing_value * config.post_drop_max_average_down_ratio
    ):
        return PostDropContext(triggered=False, bypass_reason="long_hold_average")

    window = last_n_trading_days(price_history, normalized, today, config.post_drop_lookback_days)
    if len(window) < 2:
        return PostDropContext(triggered=False, bypass_reason="insufficient_price_data")

    daily_returns = [
        (window[idx].close - window[idx - 1].close) / window[idx - 1].close
        for idx in range(1, len(window))
        if window[idx - 1].close
    ]
    if not daily_returns:
        return PostDropContext(triggered=False, bypass_reason="insufficient_price_data")

    worst_single_offset, worst_single_pct = min(enumerate(daily_returns), key=lambda item: item[1])
    cumulative_pct = (window[-1].close - window[0].close) / window[0].close

    triggered_single = worst_single_pct <= config.post_drop_threshold_single
    triggered_cumulative = cumulative_pct <= config.post_drop_threshold_cumulative
    if not (triggered_single or triggered_cumulative):
        return PostDropContext(triggered=False)

    if triggered_single and (not triggered_cumulative or worst_single_pct <= cumulative_pct):
        drop_start = window[worst_single_offset].date
        drop_end = window[worst_single_offset + 1].date
        drop_pct = worst_single_pct
    else:
        drop_start = window[0].date
        drop_end = window[-1].date
        drop_pct = cumulative_pct

    linked_dates = [
        earnings_date
        for earnings_date in earnings_dates
        if abs((earnings_date - drop_start).days) <= config.post_drop_earnings_link_window
        or abs((earnings_date - drop_end).days) <= config.post_drop_earnings_link_window
    ]
    is_linked = bool(linked_dates)
    severity = "high" if is_linked else "medium"
    earnings_date = _closest_earnings(linked_dates, drop_end) if linked_dates else None
    action, cap_ratio = action_and_cap(severity, fomo, config)
    explanation = build_explanation(normalized, drop_start, drop_end, drop_pct, severity, earnings_date, cap_ratio)
    return PostDropContext(
        triggered=True,
        drop_pct=drop_pct,
        drop_start_date=drop_start,
        drop_end_date=drop_end,
        is_earnings_linked=is_linked,
        earnings_date=earnings_date,
        severity=severity,
        action=action,
        cap_ratio=cap_ratio,
        explanation=explanation,
    )


def action_and_cap(
    severity: str, fomo: int | None, config: AppConfig
) -> tuple[str, float]:
    score = fomo or 0
    if severity == "high":
        if score >= config.post_drop_fomo_block_high:
            return "block", 0.0
        return "warn", config.post_drop_cap_ratio_high
    if score >= config.post_drop_fomo_block_medium:
        return "block", 0.0
    return "warn", config.post_drop_cap_ratio_medium


def last_n_trading_days(
    price_history: list[PriceHistoryBar], ticker: str, today: date, days: int
) -> list[PriceHistoryBar]:
    normalized = ticker.upper()
    eligible = [
        bar for bar in price_history if bar.ticker == normalized and bar.date <= today and bar.close > 0
    ]
    eligible.sort(key=lambda bar: bar.date)
    return eligible[-days:]


def build_explanation(
    ticker: str,
    drop_start: date,
    drop_end: date,
    drop_pct: float,
    severity: str,
    earnings_date: date | None,
    cap_ratio: float,
) -> str:
    if severity == "high":
        return (
            f"[post_drop_chase | high] {ticker}는 {drop_start} ~ {drop_end} 동안 "
            f"{drop_pct:.1%} 하락했고, 실적 발표일 {earnings_date}와 인접합니다. "
            f"급락 직후 매수는 추가 하락 위험이 큽니다. "
            f"매수 금액 상한이 {cap_ratio:.0%}로 축소되었습니다."
        )
    return (
        f"[post_drop_chase | medium] {ticker}는 {drop_start} ~ {drop_end} 동안 "
        f"{drop_pct:.1%} 하락했습니다. 뉴스/실적 연관은 확인되지 않았으나, "
        f"급락 직후 매수는 신중하게 검토하세요. "
        f"매수 금액 상한이 {cap_ratio:.0%}로 축소되었습니다."
    )


def _find_holding(portfolio: PortfolioSnapshot, ticker: str) -> Holding | None:
    return next((holding for holding in portfolio.holdings if holding.ticker == ticker), None)


def _held_days(holding: Holding | None, today: date) -> int:
    if holding is None:
        return 0
    held_since = getattr(holding, "held_since", None)
    if held_since is None:
        return 0
    if isinstance(held_since, datetime):
        return (today - held_since.date()).days
    if isinstance(held_since, date):
        return (today - held_since).days
    return 0


def _position_value_krw(holding: Holding | None, fx_usd_krw: float) -> float:
    if holding is None:
        return 0.0
    multiplier = fx_usd_krw if holding.currency == "USD" else 1.0
    return holding.quantity * holding.current_price * multiplier


def _closest_earnings(earnings_dates: list[date], target: date) -> date | None:
    if not earnings_dates:
        return None
    return min(earnings_dates, key=lambda item: abs((item - target).days))

