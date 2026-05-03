from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.models import PriceSnapshot


KST = ZoneInfo("Asia/Seoul")


class MockPriceProvider:
    def __init__(self) -> None:
        now = datetime.now(tz=KST)
        self._prices: dict[str, PriceSnapshot] = {
            "QQQ": PriceSnapshot(
                ticker="QQQ",
                current_price=659.6,
                previous_close=680.0,
                change_pct=-3.0,
                volume=72_000_000,
                volume_avg_30d=54_000_000,
                volume_ratio=1.33,
                currency="USD",
                timestamp=now,
            ),
            "SMH": PriceSnapshot(
                ticker="SMH",
                current_price=247.0,
                previous_close=260.0,
                change_pct=-5.0,
                volume=23_000_000,
                volume_avg_30d=14_000_000,
                volume_ratio=1.64,
                currency="USD",
                timestamp=now,
            ),
            "AAPL": PriceSnapshot(
                ticker="AAPL",
                current_price=280.0,
                previous_close=276.0,
                change_pct=1.45,
                volume=61_000_000,
                volume_avg_30d=55_000_000,
                volume_ratio=1.11,
                currency="USD",
                timestamp=now,
            ),
            "AMD": PriceSnapshot(
                ticker="AMD",
                current_price=164.0,
                previous_close=170.0,
                change_pct=-3.53,
                volume=89_000_000,
                volume_avg_30d=48_000_000,
                volume_ratio=1.85,
                currency="USD",
                timestamp=now,
            ),
            "MVST": PriceSnapshot(
                ticker="MVST",
                current_price=0.52,
                previous_close=0.48,
                change_pct=8.33,
                volume=13_000_000,
                volume_avg_30d=4_000_000,
                volume_ratio=3.25,
                currency="USD",
                timestamp=now,
            ),
            "SPY": PriceSnapshot(
                ticker="SPY",
                current_price=590.0,
                previous_close=598.0,
                change_pct=-1.34,
                volume=81_000_000,
                volume_avg_30d=70_000_000,
                volume_ratio=1.16,
                currency="USD",
                timestamp=now,
            ),
            "KOSPI": PriceSnapshot(
                ticker="KOSPI",
                current_price=2925.0,
                previous_close=2910.0,
                change_pct=0.52,
                volume=620_000_000,
                volume_avg_30d=590_000_000,
                volume_ratio=1.05,
                currency="KRW",
                timestamp=now,
            ),
        }

    def get_current_price(self, ticker: str, market: str = "US") -> PriceSnapshot:
        normalized = ticker.upper().strip()
        if normalized not in self._prices:
            return PriceSnapshot(
                ticker=normalized,
                current_price=100.0,
                previous_close=100.0,
                change_pct=0.0,
                volume=1_000_000,
                volume_avg_30d=1_000_000,
                volume_ratio=1.0,
                currency="KRW" if market == "KR" else "USD",
                timestamp=datetime.now(tz=KST),
            )
        return self._prices[normalized]

    def get_history(self, ticker: str, days: int) -> list[PriceSnapshot]:
        current = self.get_current_price(ticker)
        history: list[PriceSnapshot] = []
        for offset in range(days, 0, -1):
            drift = 1 - (offset * 0.002)
            history.append(
                PriceSnapshot(
                    ticker=current.ticker,
                    current_price=round(current.current_price * drift, 2),
                    previous_close=round(current.previous_close * drift, 2),
                    change_pct=current.change_pct,
                    volume=current.volume,
                    volume_avg_30d=current.volume_avg_30d,
                    volume_ratio=current.volume_ratio,
                    currency=current.currency,
                    timestamp=current.timestamp - timedelta(days=offset),
                )
            )
        return history

