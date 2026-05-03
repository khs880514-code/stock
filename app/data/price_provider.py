from __future__ import annotations

from typing import Protocol

from app.models import PriceSnapshot


class PriceProvider(Protocol):
    def get_current_price(self, ticker: str, market: str = "US") -> PriceSnapshot:
        ...

    def get_history(self, ticker: str, days: int) -> list[PriceSnapshot]:
        ...

