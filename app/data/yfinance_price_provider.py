from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.models import PriceSnapshot


class YfinancePriceProvider:
    def get_current_price(self, ticker: str, market: str = "US") -> PriceSnapshot:
        try:
            import yfinance as yf
        except ModuleNotFoundError as exc:
            raise RuntimeError("Install yfinance to use this adapter.") from exc

        hist = yf.Ticker(ticker).history(period="35d")
        if hist.empty:
            raise RuntimeError(f"No yfinance data for {ticker}.")
        last = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else last
        avg_volume = int(hist["Volume"].tail(30).mean() or 0)
        volume = int(last["Volume"] or 0)
        current = float(last["Close"])
        previous = float(prev["Close"])
        change_pct = ((current - previous) / previous * 100) if previous else 0.0
        ratio = (volume / avg_volume) if avg_volume else 0.0
        return PriceSnapshot(
            ticker=ticker,
            current_price=current,
            previous_close=previous,
            change_pct=change_pct,
            volume=volume,
            volume_avg_30d=avg_volume,
            volume_ratio=ratio,
            currency="KRW" if market == "KR" else "USD",
            timestamp=datetime.now(tz=ZoneInfo("Asia/Seoul")),
        )

    def get_history(self, ticker: str, days: int) -> list[PriceSnapshot]:
        try:
            import yfinance as yf
        except ModuleNotFoundError as exc:
            raise RuntimeError("Install yfinance to use this adapter.") from exc

        hist = yf.Ticker(ticker).history(period=f"{max(days + 2, 5)}d")
        snapshots: list[PriceSnapshot] = []
        for idx in range(1, min(days + 1, len(hist))):
            row = hist.iloc[-idx]
            prev = hist.iloc[-idx - 1] if idx + 1 <= len(hist) else row
            current = float(row["Close"])
            previous = float(prev["Close"])
            snapshots.append(
                PriceSnapshot(
                    ticker=ticker,
                    current_price=current,
                    previous_close=previous,
                    change_pct=((current - previous) / previous * 100) if previous else 0.0,
                    volume=int(row["Volume"] or 0),
                    volume_avg_30d=int(hist["Volume"].tail(30).mean() or 0),
                    volume_ratio=1.0,
                    currency="USD",
                    timestamp=row.name.to_pydatetime(),
                )
            )
        return list(reversed(snapshots))

