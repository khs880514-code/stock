from __future__ import annotations

from dataclasses import dataclass

from app.config import AppConfig
from app.data.portfolio_store import holding_value_krw
from app.models import Holding, PortfolioSnapshot


@dataclass(frozen=True)
class LimitCheck:
    ok: bool
    reasons: list[str]
    capped_amount_krw: int


THEME_GROUPS = {
    "BIG_TECH": "TECH_AI",
    "SEMICONDUCTOR": "TECH_AI",
    "AI_SEMICONDUCTOR": "TECH_AI",
    "CORE_ETF": "TECH_AI",
    "SPECULATIVE_LOSS": "SPECULATIVE_LOSS",
}


def theme_group(sector_tag: str) -> str:
    return THEME_GROUPS.get(sector_tag, sector_tag)


def find_holding(portfolio: PortfolioSnapshot, ticker: str) -> Holding | None:
    normalized = ticker.upper()
    return next((holding for holding in portfolio.holdings if holding.ticker == normalized), None)


def evaluate_buy_limits(
    portfolio: PortfolioSnapshot,
    ticker: str,
    amount_krw: int,
    sector_tag: str,
    config: AppConfig,
    amount_bought_today_krw: int = 0,
) -> LimitCheck:
    reasons: list[str] = []
    capped_amount = min(amount_krw, config.single_buy_max_krw)
    if amount_krw > config.single_buy_max_krw:
        reasons.append(f"1회 신규매수 한도 {config.single_buy_max_krw:,}원으로 제한")

    if amount_bought_today_krw + amount_krw > config.daily_buy_limit_krw:
        reasons.append(f"1일 신규매수 한도 {config.daily_buy_limit_krw:,}원 초과")

    if portfolio.cash_krw - amount_krw < config.min_cash_krw:
        reasons.append(f"매수 후 현금이 최소 보유액 {config.min_cash_krw:,}원 미만")

    total = max(portfolio.total_value_krw, 1)
    current_holding = find_holding(portfolio, ticker)
    current_value = (
        holding_value_krw(current_holding, config.fx_usd_krw) if current_holding is not None else 0.0
    )
    if (current_value + amount_krw) / total > config.max_single_position_pct:
        reasons.append(f"1종목 비중 한도 {config.max_single_position_pct:.0%} 초과")

    target_theme = theme_group(sector_tag)
    theme_value = 0.0
    for holding in portfolio.holdings:
        if theme_group(holding.sector_tag) == target_theme:
            theme_value += holding_value_krw(holding, config.fx_usd_krw)
    if (theme_value + amount_krw) / total > config.max_theme_pct:
        reasons.append(f"동일 테마 비중 한도 {config.max_theme_pct:.0%} 초과")

    ok = not any(
        reason
        for reason in reasons
        if "초과" in reason or "미만" in reason
    )
    return LimitCheck(ok=ok, reasons=reasons, capped_amount_krw=max(capped_amount, 0))


def is_loss_averaging_attempt(holding: Holding | None, config: AppConfig) -> bool:
    if holding is None or holding.avg_price <= 0:
        return False
    drawdown = (holding.current_price - holding.avg_price) / holding.avg_price
    return drawdown <= config.loss_averaging_block_pct

