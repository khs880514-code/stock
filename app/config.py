from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


LEGAL_DISCLAIMER = """이 시스템은 개인 투자자의 자기 판단을 돕는 기록·알림·복기 도구입니다.
최종 투자 판단과 주문은 사용자 본인이 직접 수행합니다.
이 시스템은 투자일임, 투자자문, 유사투자자문 서비스를 제공하지 않습니다.
이 시스템은 수익률을 보장하지 않습니다."""


@dataclass(frozen=True)
class AppConfig:
    db_path: Path = Path("stock_expert_friend.sqlite3")
    timezone: str = "Asia/Seoul"
    fx_usd_krw: float = 1350.0
    single_buy_min_krw: int = 1_000_000
    single_buy_max_krw: int = 1_000_000
    daily_buy_limit_krw: int = 3_000_000
    max_single_position_pct: float = 0.25
    max_theme_pct: float = 0.35
    min_cash_krw: int = 10_000_000
    loss_averaging_block_pct: float = -0.50
    fomo_wait_threshold: int = 7
    fomo_block_threshold: int = 9
    influence_block_threshold: int = 8
    earnings_block_days: int = 7
    trigger_daily_cap: int = 3
    trigger_weekly_review_count: int = 5
    post_drop_rule_enabled: bool = True
    post_drop_lookback_days: int = 5
    post_drop_threshold_single: float = -0.07
    post_drop_threshold_cumulative: float = -0.10
    post_drop_earnings_link_window: int = 3
    post_drop_long_hold_days: int = 90
    post_drop_max_average_down_ratio: float = 0.30
    post_drop_cap_ratio_high: float = 0.5
    post_drop_cap_ratio_medium: float = 0.7
    post_drop_fomo_block_high: int = 6
    post_drop_fomo_block_medium: int = 7
    holiday_gap_rule_enabled: bool = True
    holiday_gap_min_days: int = 3
    holiday_gap_min_us_accumulated_pct: float = 0.02
    holiday_gap_medium_score: int = 20
    holiday_gap_high_score: int = 50
    holiday_gap_cap_ratio_medium: float = 0.85
    holiday_gap_cap_ratio_high: float = 0.70
    post_run_decomp_rule_enabled: bool = True
    post_run_lookback_days: int = 5
    post_run_min_total_change_pct: float = 0.05
    post_run_sector_translation_factor: float = 0.6
    post_run_residual_high_pct: float = 0.05
    post_run_residual_medium_pct: float = 0.03
    post_run_cap_ratio_high: float = 0.50
    post_run_cap_ratio_medium: float = 0.70
    decision_protection_enabled: bool = True
    regret_chase_lookback_days: int = 14
    regret_chase_gain_pct: float = 0.08
    blackout_default_days: int = 1


def load_config() -> AppConfig:
    db_path = Path(os.getenv("SEF_DB_PATH", "stock_expert_friend.sqlite3"))
    return AppConfig(
        db_path=db_path,
        timezone=os.getenv("SEF_TIMEZONE", "Asia/Seoul"),
        fx_usd_krw=float(os.getenv("SEF_FX_USD_KRW", "1350")),
        single_buy_min_krw=int(os.getenv("SEF_SINGLE_BUY_MIN_KRW", "1000000")),
        single_buy_max_krw=int(os.getenv("SEF_SINGLE_BUY_MAX_KRW", "1000000")),
        daily_buy_limit_krw=int(os.getenv("SEF_DAILY_BUY_LIMIT_KRW", "3000000")),
        max_single_position_pct=float(os.getenv("SEF_MAX_SINGLE_POSITION_PCT", "0.25")),
        max_theme_pct=float(os.getenv("SEF_MAX_THEME_PCT", "0.35")),
        min_cash_krw=int(os.getenv("SEF_MIN_CASH_KRW", "10000000")),
        holiday_gap_rule_enabled=os.getenv("SEF_HOLIDAY_GAP_RULE_ENABLED", "1") != "0",
        post_run_decomp_rule_enabled=os.getenv("SEF_POST_RUN_DECOMP_RULE_ENABLED", "1") != "0",
        decision_protection_enabled=os.getenv("SEF_DECISION_PROTECTION_ENABLED", "1") != "0",
    )
