from __future__ import annotations

from datetime import date

from app.config import AppConfig
from app.data.ticker_sensitivity import is_corr_stale, is_foreign_stale
from app.models import HolidayGapSignal, PriceHistoryBar, RelativeWeaknessSignal, TickerSensitivitySnapshot


RULE_ID = "holiday_gap_setup"
RULE_VERSION = "holiday_gap_v1.0"


def evaluate(
    *,
    ticker: str,
    today: date,
    sensitivity: TickerSensitivitySnapshot | None,
    gap_days: int,
    us_accumulated_return_pct: float | None,
    config: AppConfig,
) -> HolidayGapSignal:
    if not config.holiday_gap_rule_enabled:
        return HolidayGapSignal(triggered=False, completeness="complete", explanation="holiday_gap disabled")

    normalized = ticker.upper().strip()
    if sensitivity is None:
        return HolidayGapSignal(
            triggered=False,
            gap_days=gap_days,
            us_accumulated_return_pct=us_accumulated_return_pct,
            completeness="partial_missing_sensitivity",
            explanation=f"[holiday_gap_setup] {normalized}: 민감도 데이터가 없어 연휴 갭 룰은 참고 정보로만 표시합니다.",
        )

    completeness = _completeness(sensitivity, today)
    if gap_days < config.holiday_gap_min_days or us_accumulated_return_pct is None:
        return HolidayGapSignal(
            triggered=False,
            gap_days=gap_days,
            us_accumulated_return_pct=us_accumulated_return_pct,
            completeness=completeness if us_accumulated_return_pct is not None else "insufficient_market_data",
        )

    foreign = sensitivity.foreign_ownership_pct or 0.0
    corr = sensitivity.us_sector_corr_60d if sensitivity.us_sector_corr_60d is not None else 0.0
    us_move = us_accumulated_return_pct
    if us_move < config.holiday_gap_min_us_accumulated_pct:
        return HolidayGapSignal(
            triggered=False,
            gap_days=gap_days,
            us_accumulated_return_pct=us_move,
            score=0,
            severity="low",
            completeness=completeness,
            explanation=f"[holiday_gap_setup] {normalized}: 연휴 갭은 있지만 미국 누적 상승이 임계값 미만입니다.",
        )

    score = compute_gap_score(
        foreign_ownership_pct=foreign,
        us_sector_corr_60d=corr,
        us_accumulated_return_pct=us_move,
        min_us_accumulated_pct=config.holiday_gap_min_us_accumulated_pct,
    )
    severity, cap_ratio = severity_and_cap(score, config)
    explanation = (
        f"[holiday_gap_setup | {severity}] {normalized}: 국내 휴장 {gap_days}일 동안 미국 관련 흐름이 "
        f"{us_move:.1%} 움직였고, 외국인 지분 {foreign:.2f}% / 미국 섹터 민감도 {corr:.2f}로 "
        f"갭 리스크를 산출했습니다."
    )
    if cap_ratio is not None:
        explanation += f" 신규 매수 상한을 {cap_ratio:.0%}로 낮춥니다."
    return HolidayGapSignal(
        triggered=severity != "low",
        gap_days=gap_days,
        us_accumulated_return_pct=us_move,
        score=score,
        severity=severity,
        cap_ratio=cap_ratio,
        completeness=completeness,
        explanation=explanation,
    )


def compute_gap_score(
    *,
    foreign_ownership_pct: float,
    us_sector_corr_60d: float | None,
    us_accumulated_return_pct: float,
    min_us_accumulated_pct: float,
) -> float:
    corr = max(min(us_sector_corr_60d or 0.0, 1.0), 0.0)
    move_scale = min(max(us_accumulated_return_pct / min_us_accumulated_pct, 0.0), 1.5)
    # Very high sector correlation means foreign ownership itself is the risk carrier.
    correlation_factor = 1.0 if corr >= 0.70 else corr
    return foreign_ownership_pct * correlation_factor * move_scale


def severity_and_cap(score: float, config: AppConfig) -> tuple[str, float | None]:
    if score >= config.holiday_gap_high_score:
        return "high", config.holiday_gap_cap_ratio_high
    if score >= config.holiday_gap_medium_score:
        return "medium", config.holiday_gap_cap_ratio_medium
    return "low", None


def evaluate_relative_weakness(
    *,
    ticker: str,
    ticker_history: list[PriceHistoryBar],
    kospi_history: list[PriceHistoryBar],
    today: date,
    lookback_days: int = 5,
) -> RelativeWeaknessSignal:
    ticker_window = _last_n(ticker_history, ticker, today, lookback_days)
    kospi_window = _last_n(kospi_history, "^KS11", today, lookback_days) or _last_n(
        kospi_history, "KOSPI", today, lookback_days
    )
    if len(ticker_window) < 2 or len(kospi_window) < 2:
        return RelativeWeaknessSignal(triggered=False)
    ticker_return = _return(ticker_window)
    kospi_return = _return(kospi_window)
    triggered = kospi_return >= 0.03 and ticker_return <= -0.01
    explanation = None
    if triggered:
        explanation = (
            f"[relative_weakness] KOSPI는 {kospi_return:.1%} 상승했지만 "
            f"{ticker.upper()}는 {ticker_return:.1%} 하락했습니다. 차단이 아니라 확인 신호입니다."
        )
    return RelativeWeaknessSignal(
        triggered=triggered,
        ticker_return_pct=ticker_return,
        kospi_return_pct=kospi_return,
        explanation=explanation,
    )


def _completeness(sensitivity: TickerSensitivitySnapshot, today: date) -> str:
    if is_foreign_stale(sensitivity, today):
        return "partial_stale_foreign"
    if is_corr_stale(sensitivity, today):
        return "partial_stale_corr"
    return "complete"


def _last_n(
    history: list[PriceHistoryBar], ticker: str, today: date, days: int
) -> list[PriceHistoryBar]:
    normalized = ticker.upper()
    rows = [bar for bar in history if bar.ticker == normalized and bar.date <= today and bar.close > 0]
    rows.sort(key=lambda bar: bar.date)
    return rows[-days:]


def _return(window: list[PriceHistoryBar]) -> float:
    return (window[-1].close - window[0].close) / window[0].close
