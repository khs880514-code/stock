from __future__ import annotations

from datetime import date

from app.config import AppConfig
from app.models import PostRunDecomposition, PriceHistoryBar, TickerSensitivitySnapshot
from app.rules.post_run_news_mapping import explained_news_return


RULE_ID = "post_run_decomposition"
RULE_VERSION = "post_run_decomp_v1.0"


def evaluate(
    *,
    ticker: str,
    today: date,
    ticker_history: list[PriceHistoryBar],
    kospi_history: list[PriceHistoryBar],
    us_sector_history: list[PriceHistoryBar],
    us_market_history: list[PriceHistoryBar],
    sensitivity: TickerSensitivitySnapshot | None,
    news_categories: list[str],
    news_available: bool,
    config: AppConfig,
) -> PostRunDecomposition:
    if not config.post_run_decomp_rule_enabled:
        return PostRunDecomposition(triggered=False, completeness="disabled")

    normalized = ticker.upper().strip()
    ticker_window = _last_n(ticker_history, normalized, today, config.post_run_lookback_days)
    if len(ticker_window) < 2:
        return PostRunDecomposition(triggered=False, completeness="insufficient_price_data")

    total_change = _window_return(ticker_window)
    if total_change < config.post_run_min_total_change_pct:
        return PostRunDecomposition(
            triggered=False,
            total_change_pct=total_change,
            completeness="complete" if sensitivity and news_available else _partial_label(sensitivity, news_available),
        )

    beta = sensitivity.beta_to_kospi_60d if sensitivity and sensitivity.beta_to_kospi_60d is not None else 1.0
    kospi_return = _optional_return(kospi_history, "^KS11", today, config.post_run_lookback_days)
    if kospi_return is None:
        kospi_return = _optional_return(kospi_history, "KOSPI", today, config.post_run_lookback_days)
    market_explained = (kospi_return or 0.0) * beta

    sector_explained = 0.0
    if sensitivity and sensitivity.us_sector_corr_60d is not None:
        sector_return = _optional_return(
            us_sector_history,
            sensitivity.us_sector_proxy_symbol or "",
            today,
            config.post_run_lookback_days,
        )
        us_market_return = _optional_return(us_market_history, "^GSPC", today, config.post_run_lookback_days)
        if us_market_return is None:
            us_market_return = _optional_return(us_market_history, "SPY", today, config.post_run_lookback_days)
        if sector_return is not None and us_market_return is not None:
            sector_explained = (
                (sector_return - us_market_return)
                * sensitivity.us_sector_corr_60d
                * config.post_run_sector_translation_factor
            )

    news_explained = explained_news_return(news_categories) if news_available else 0.0
    residual = total_change - market_explained - sector_explained - news_explained
    severity, cap_ratio = severity_and_cap(residual, config)
    completeness = _partial_label(sensitivity, news_available)
    explanation = (
        f"[post_run_decomposition | {severity}] {normalized}: 최근 {config.post_run_lookback_days}거래일 "
        f"상승 {total_change:.1%} 중 시장 {market_explained:.1%}, 섹터 {sector_explained:.1%}, "
        f"뉴스 {news_explained:.1%}로 설명하고 잔여 {residual:.1%}를 남겼습니다."
    )
    if cap_ratio is not None:
        explanation += f" 잔여 급등 추격 위험으로 신규 매수 상한을 {cap_ratio:.0%}로 낮춥니다."

    return PostRunDecomposition(
        triggered=True,
        total_change_pct=total_change,
        market_explained_pct=market_explained,
        sector_explained_pct=sector_explained,
        news_explained_pct=news_explained,
        residual_pct=residual,
        severity=severity,
        cap_ratio=cap_ratio,
        completeness=completeness,
        explanation=explanation,
    )


def severity_and_cap(residual_pct: float, config: AppConfig) -> tuple[str, float | None]:
    if residual_pct >= config.post_run_residual_high_pct:
        return "high", config.post_run_cap_ratio_high
    if residual_pct > config.post_run_residual_medium_pct:
        return "medium", config.post_run_cap_ratio_medium
    return "low", None


def _partial_label(sensitivity: TickerSensitivitySnapshot | None, news_available: bool) -> str:
    if sensitivity is None:
        return "partial_no_sensitivity"
    if not news_available:
        return "partial_no_news"
    return "complete"


def _optional_return(
    history: list[PriceHistoryBar], ticker: str, today: date, lookback_days: int
) -> float | None:
    if not ticker:
        return None
    window = _last_n(history, ticker.upper(), today, lookback_days)
    return _window_return(window) if len(window) >= 2 else None


def _last_n(
    history: list[PriceHistoryBar], ticker: str, today: date, lookback_days: int
) -> list[PriceHistoryBar]:
    rows = [bar for bar in history if bar.ticker == ticker.upper() and bar.date <= today and bar.close > 0]
    rows.sort(key=lambda bar: bar.date)
    return rows[-lookback_days:]


def _window_return(window: list[PriceHistoryBar]) -> float:
    return (window[-1].close - window[0].close) / window[0].close
