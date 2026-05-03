from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.config import AppConfig
from app.models import Holding, PortfolioSnapshot


@pytest.fixture
def config() -> AppConfig:
    return AppConfig()


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 5, 3, 9, 0, tzinfo=ZoneInfo("Asia/Seoul"))


@pytest.fixture
def portfolio() -> PortfolioSnapshot:
    holdings = [
        Holding(
            ticker="QQQ",
            market="US",
            quantity=5,
            avg_price=430.0,
            current_price=660.0,
            currency="USD",
            asset_type="ETF",
            sector_tag="CORE_ETF",
        ),
        Holding(
            ticker="AMD",
            market="US",
            quantity=5,
            avg_price=105.0,
            current_price=164.0,
            currency="USD",
            asset_type="EQUITY",
            sector_tag="AI_SEMICONDUCTOR",
        ),
    ]
    return PortfolioSnapshot(cash_krw=20_000_000, holdings=holdings, total_value_krw=28_000_000)

