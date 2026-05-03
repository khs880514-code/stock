from app.engines.portfolio_risk import evaluate_buy_limits
from app.models import Holding, PortfolioSnapshot


def test_single_position_limit_blocks_extra_buy(config):
    portfolio = PortfolioSnapshot(
        cash_krw=20_000_000,
        total_value_krw=40_000_000,
        holdings=[
            Holding(
                ticker="AAPL",
                market="US",
                quantity=30,
                avg_price=135,
                current_price=280,
                currency="USD",
                asset_type="EQUITY",
                sector_tag="BIG_TECH",
            )
        ],
    )
    result = evaluate_buy_limits(portfolio, "AAPL", 1_000_000, "BIG_TECH", config)
    assert not result.ok
    assert any("1종목 비중" in reason for reason in result.reasons)


def test_min_cash_blocks_new_buy(config):
    portfolio = PortfolioSnapshot(cash_krw=8_200_000, total_value_krw=20_000_000, holdings=[])
    result = evaluate_buy_limits(portfolio, "QQQ", 1_000_000, "CORE_ETF", config)
    assert not result.ok
    assert any("현금" in reason for reason in result.reasons)

