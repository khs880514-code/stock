from __future__ import annotations

from datetime import date, datetime, timedelta

from app.config import AppConfig
from app.engines.buy_check_mode import review_buy_request
from app.models import Action, BuyReviewRequest, Holding, PortfolioSnapshot, PriceHistoryBar
from app.rules.post_drop_chase import evaluate


TODAY = date(2026, 5, 3)


def bars(ticker: str, closes: list[float], start: date = date(2026, 4, 27)) -> list[PriceHistoryBar]:
    return [
        PriceHistoryBar(ticker=ticker, date=start + timedelta(days=idx), close=close)
        for idx, close in enumerate(closes)
    ]


def empty_portfolio() -> PortfolioSnapshot:
    return PortfolioSnapshot(cash_krw=20_000_000, holdings=[], total_value_krw=20_000_000)


def test_meta_earnings_drop_warn_with_low_fomo():
    context = evaluate(
        "META",
        1_000_000,
        5,
        empty_portfolio(),
        bars("META", [100, 100, 100, 90, 90]),
        [date(2026, 4, 30)],
        TODAY,
        AppConfig(),
    )
    assert context.triggered
    assert context.severity == "high"
    assert context.action == "warn"
    assert context.cap_ratio == 0.5


def test_meta_high_fomo_blocks():
    context = evaluate(
        "META",
        1_000_000,
        7,
        empty_portfolio(),
        bars("META", [100, 100, 100, 90, 90]),
        [date(2026, 4, 30)],
        TODAY,
        AppConfig(),
    )
    assert context.action == "block"


def test_amd_earnings_without_drop_not_triggered():
    context = evaluate(
        "AMD",
        1_000_000,
        5,
        empty_portfolio(),
        bars("AMD", [100, 100.5, 100.3, 100.2, 100.1]),
        [date(2026, 5, 1)],
        TODAY,
        AppConfig(),
    )
    assert not context.triggered


def test_core_etf_bypass():
    context = evaluate(
        "QQQ",
        1_000_000,
        5,
        empty_portfolio(),
        bars("QQQ", [100, 92, 92, 92, 92]),
        [],
        TODAY,
        AppConfig(),
    )
    assert context.bypass_reason == "core_etf"


def test_random_drop_medium_warn():
    context = evaluate(
        "XYZ",
        1_000_000,
        5,
        empty_portfolio(),
        bars("XYZ", [100, 100, 85, 85, 85]),
        [],
        TODAY,
        AppConfig(),
    )
    assert context.severity == "medium"
    assert context.action == "warn"
    assert context.cap_ratio == 0.7


def test_long_hold_average_bypass():
    portfolio = PortfolioSnapshot(
        cash_krw=20_000_000,
        total_value_krw=40_000_000,
        holdings=[
            Holding(
                ticker="META",
                quantity=100,
                avg_price=100,
                current_price=100,
                currency="USD",
                sector_tag="BIG_TECH",
            ).model_copy(update={"held_since": TODAY - timedelta(days=120)})
        ],
    )
    context = evaluate(
        "META",
        2_000_000,
        5,
        portfolio,
        bars("META", [100, 90, 90, 90, 90]),
        [],
        TODAY,
        AppConfig(),
    )
    assert context.bypass_reason == "long_hold_average"


def test_long_hold_large_amount_triggers():
    portfolio = PortfolioSnapshot(
        cash_krw=40_000_000,
        total_value_krw=60_000_000,
        holdings=[
            Holding(
                ticker="META",
                quantity=100,
                avg_price=100,
                current_price=100,
                currency="USD",
                sector_tag="BIG_TECH",
            ).model_copy(update={"held_since": TODAY - timedelta(days=120)})
        ],
    )
    context = evaluate(
        "META",
        9_000_000,
        5,
        portfolio,
        bars("META", [100, 90, 90, 90, 90]),
        [],
        TODAY,
        AppConfig(),
    )
    assert context.triggered


def test_insufficient_price_data_bypass():
    context = evaluate("META", 1_000_000, 5, empty_portfolio(), bars("META", [100]), [], TODAY, AppConfig())
    assert context.bypass_reason == "insufficient_price_data"


def test_single_day_exact_threshold_triggers():
    context = evaluate(
        "META",
        1_000_000,
        5,
        empty_portfolio(),
        bars("META", [100, 93, 93, 93, 93]),
        [],
        TODAY,
        AppConfig(),
    )
    assert context.triggered


def test_single_day_just_above_threshold_not_triggered():
    context = evaluate(
        "META",
        1_000_000,
        5,
        empty_portfolio(),
        bars("META", [100, 93.01, 93.01, 93.01, 93.01]),
        [],
        TODAY,
        AppConfig(),
    )
    assert not context.triggered


def test_cumulative_exact_threshold_triggers():
    context = evaluate(
        "META",
        1_000_000,
        5,
        empty_portfolio(),
        bars("META", [100, 99, 97, 94, 90]),
        [],
        TODAY,
        AppConfig(),
    )
    assert context.triggered


def test_missing_earnings_data_defaults_medium():
    context = evaluate(
        "META",
        1_000_000,
        5,
        empty_portfolio(),
        bars("META", [100, 90, 90, 90, 90]),
        [],
        TODAY,
        AppConfig(),
    )
    assert context.severity == "medium"


def test_post_drop_and_earnings_d7_both_explained_block_stronger():
    now = datetime(2026, 5, 3, 9, 0)
    decision = review_buy_request(
        BuyReviewRequest(
            ticker="META",
            desired_amount_krw=1_000_000,
            reason_text="실적 전 급락 후 검토",
            fomo_score=7,
            friend_influence_score=1,
        ),
        empty_portfolio(),
        events=[],
        recent_trades=[],
        now=now,
        config=AppConfig(),
        price_history=bars("META", [100, 90, 90, 90, 90]),
        earnings_dates=[date(2026, 5, 1)],
    )
    assert decision.action == Action.NO_TRADE
    assert any("post_drop_chase" in reason for reason in decision.reason)


def test_cap_applied_after_post_drop_warn():
    now = datetime(2026, 5, 3, 9, 0)
    decision = review_buy_request(
        BuyReviewRequest(
            ticker="XYZ",
            desired_amount_krw=1_000_000,
            reason_text="급락 후 확인",
            fomo_score=5,
            friend_influence_score=1,
        ),
        empty_portfolio(),
        events=[],
        recent_trades=[],
        now=now,
        config=AppConfig(),
        price_history=bars("XYZ", [100, 90, 90, 90, 90]),
        earnings_dates=[],
    )
    assert decision.action == Action.SMALL_BUY_CANDIDATE
    assert decision.max_amount_krw == 700_000
    assert any("사용자 확인" in reason for reason in decision.reason)
    assert decision.post_drop_context is not None
