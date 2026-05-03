from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.models import MacroIndicator, MacroSnapshot, Source


class MockMacroCollector:
    def collect(self, fx_usd_krw: float = 1501.0, wti_change_pct: float = 5.4) -> MacroSnapshot:
        now = datetime.now(tz=ZoneInfo("Asia/Seoul"))
        return MacroSnapshot(
            timestamp=now,
            indicators={
                "SP500": MacroIndicator(
                    name="S&P 500",
                    value=5965.0,
                    change_pct=-1.1,
                    moving_average_30d=6010.0,
                    source=Source(title="Stooq S&P 500", url="https://stooq.com/q/?s=%5Espx"),
                ),
                "NASDAQ": MacroIndicator(
                    name="Nasdaq Composite",
                    value=18610.0,
                    change_pct=-1.7,
                    moving_average_30d=18880.0,
                    source=Source(title="Stooq Nasdaq", url="https://stooq.com/q/?s=%5Eixic"),
                ),
                "VIX": MacroIndicator(
                    name="VIX",
                    value=18.5,
                    previous_value=17.9,
                    change_pct=3.4,
                    moving_average_30d=19.0,
                    source=Source(title="CBOE VIX", url="https://www.cboe.com/tradable_products/vix/"),
                ),
                "US10Y": MacroIndicator(
                    name="US 10Y Treasury",
                    value=4.62,
                    previous_value=4.50,
                    change_pct=2.67,
                    moving_average_30d=4.45,
                    unit="%",
                    source=Source(title="FRED DGS10", url="https://fred.stlouisfed.org/series/DGS10"),
                ),
                "USD_KRW": MacroIndicator(
                    name="USD/KRW",
                    value=fx_usd_krw,
                    previous_value=1486.0,
                    change_pct=((fx_usd_krw - 1486.0) / 1486.0) * 100,
                    moving_average_30d=1435.0,
                    source=Source(title="Exchange rate reference", url="https://finance.yahoo.com/quote/KRW=X/"),
                ),
                "WTI": MacroIndicator(
                    name="WTI Crude",
                    value=83.1,
                    previous_value=78.8,
                    change_pct=wti_change_pct,
                    moving_average_30d=79.2,
                    source=Source(title="FRED DCOILWTICO", url="https://fred.stlouisfed.org/series/DCOILWTICO"),
                ),
            },
        )

