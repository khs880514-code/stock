from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from app.models import Source


@dataclass(frozen=True)
class Headline:
    ticker: str
    title: str
    source: Source


class MockNewsCollector:
    def collect(self, tickers: list[str]) -> list[Headline]:
        now = datetime.now(tz=ZoneInfo("Asia/Seoul")).date().isoformat()
        headlines: list[Headline] = []
        for ticker in tickers:
            if ticker.upper() == "AMD":
                headlines.append(
                    Headline(
                        ticker="AMD",
                        title="AMD earnings expectations focus on data center demand",
                        source=Source(title="AMD IR news", url="https://ir.amd.com/", published_at=now),
                    )
                )
            if ticker.upper() == "SMH":
                headlines.append(
                    Headline(
                        ticker="SMH",
                        title="Semiconductor ETF volume rises as rates and oil move",
                        source=Source(title="VanEck SMH", url="https://www.vaneck.com/us/en/investments/semiconductor-etf-smh/overview/", published_at=now),
                    )
                )
        return headlines

