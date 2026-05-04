from datetime import date, timedelta

from app.config import AppConfig
from app.models import PriceHistoryBar, TickerSensitivitySnapshot
from app.rules.post_run_decomposition import evaluate


def _bars(ticker: str, closes: list[float]) -> list[PriceHistoryBar]:
    start = date(2026, 4, 27)
    return [
        PriceHistoryBar(ticker=ticker, date=start + timedelta(days=idx), close=close)
        for idx, close in enumerate(closes)
    ]


def test_exact_five_percent_unexplained_run_is_high():
    result = evaluate(
        ticker="005930.KS",
        today=date(2026, 5, 4),
        ticker_history=_bars("005930.KS", [100, 101, 102, 103, 105]),
        kospi_history=[],
        us_sector_history=[],
        us_market_history=[],
        sensitivity=None,
        news_categories=[],
        news_available=False,
        config=AppConfig(),
    )

    assert result.triggered is True
    assert result.severity == "high"
    assert result.cap_ratio == 0.50
    assert result.completeness == "partial_no_sensitivity"


def test_market_sector_and_news_explanations_reduce_residual_to_low():
    result = evaluate(
        ticker="000660.KS",
        today=date(2026, 5, 4),
        ticker_history=_bars("000660.KS", [100, 103, 105, 108, 110]),
        kospi_history=_bars("^KS11", [100, 101, 102, 103, 103]),
        us_sector_history=_bars("SMH", [100, 104, 105, 106, 107]),
        us_market_history=_bars("^GSPC", [100, 101, 102, 102, 103]),
        sensitivity=TickerSensitivitySnapshot(
            ticker="000660.KS",
            sector_tag="AI_SEMICONDUCTOR",
            us_sector_proxy_symbol="SMH",
            us_sector_corr_60d=0.80,
            beta_to_kospi_60d=1.0,
        ),
        news_categories=["earnings_surprise"],
        news_available=True,
        config=AppConfig(),
    )

    assert result.triggered is True
    assert result.severity == "low"
    assert result.cap_ratio is None
    assert result.residual_pct is not None
    assert result.residual_pct < 0.03


def test_small_move_does_not_trigger():
    result = evaluate(
        ticker="005930.KS",
        today=date(2026, 5, 4),
        ticker_history=_bars("005930.KS", [100, 100.5, 101, 102, 104]),
        kospi_history=[],
        us_sector_history=[],
        us_market_history=[],
        sensitivity=None,
        news_categories=[],
        news_available=False,
        config=AppConfig(),
    )

    assert result.triggered is False
    assert result.total_change_pct is not None
    assert result.total_change_pct < 0.05
