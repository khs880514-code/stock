from datetime import date

from app.config import AppConfig
from app.models import PriceHistoryBar, TickerSensitivitySnapshot
from app.rules.holiday_gap_setup import evaluate, evaluate_relative_weakness


def test_hynix_like_holiday_gap_is_high_risk():
    signal = evaluate(
        ticker="000660.KS",
        today=date(2026, 5, 4),
        sensitivity=TickerSensitivitySnapshot(
            ticker="000660.KS",
            sector_tag="AI_SEMICONDUCTOR",
            us_sector_proxy_symbol="SMH",
            foreign_ownership_pct=53.0,
            foreign_ownership_taken_at=date(2026, 5, 4),
            us_sector_corr_60d=0.78,
            corr_taken_at=date(2026, 5, 4),
        ),
        gap_days=3,
        us_accumulated_return_pct=0.02,
        config=AppConfig(),
    )

    assert signal.triggered is True
    assert signal.severity == "high"
    assert signal.cap_ratio == 0.70


def test_low_foreign_low_corr_gap_is_not_capped():
    signal = evaluate(
        ticker="263750.KQ",
        today=date(2026, 5, 4),
        sensitivity=TickerSensitivitySnapshot(
            ticker="263750.KQ",
            sector_tag="GAME",
            us_sector_proxy_symbol="HERO",
            foreign_ownership_pct=6.88,
            foreign_ownership_taken_at=date(2026, 5, 4),
            us_sector_corr_60d=0.18,
            corr_taken_at=date(2026, 5, 4),
        ),
        gap_days=3,
        us_accumulated_return_pct=0.02,
        config=AppConfig(),
    )

    assert signal.triggered is False
    assert signal.severity == "low"
    assert signal.cap_ratio is None


def test_missing_and_stale_sensitivity_are_marked_partial():
    missing = evaluate(
        ticker="005930.KS",
        today=date(2026, 5, 4),
        sensitivity=None,
        gap_days=3,
        us_accumulated_return_pct=0.02,
        config=AppConfig(),
    )
    assert missing.completeness == "partial_missing_sensitivity"

    stale = evaluate(
        ticker="005930.KS",
        today=date(2026, 5, 4),
        sensitivity=TickerSensitivitySnapshot(
            ticker="005930.KS",
            foreign_ownership_pct=55.0,
            foreign_ownership_taken_at=date(2026, 4, 29),
            us_sector_corr_60d=0.80,
            corr_taken_at=date(2026, 5, 4),
        ),
        gap_days=3,
        us_accumulated_return_pct=0.02,
        config=AppConfig(),
    )
    assert stale.completeness == "partial_stale_foreign"


def test_relative_weakness_is_signal_only():
    ticker_history = [
        PriceHistoryBar(ticker="005930.KS", date=date(2026, 4, 27), close=100),
        PriceHistoryBar(ticker="005930.KS", date=date(2026, 5, 4), close=99),
    ]
    kospi_history = [
        PriceHistoryBar(ticker="^KS11", date=date(2026, 4, 27), close=100),
        PriceHistoryBar(ticker="^KS11", date=date(2026, 5, 4), close=103),
    ]

    signal = evaluate_relative_weakness(
        ticker="005930.KS",
        ticker_history=ticker_history,
        kospi_history=kospi_history,
        today=date(2026, 5, 4),
    )

    assert signal.triggered is True
    assert signal.explanation and "차단이 아니라 확인 신호" in signal.explanation
