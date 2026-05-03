from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from time import sleep
from urllib.parse import quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from app.db.database import connect, init_db
from app.models import PriceHistoryBar


class PriceHistoryStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        init_db(self.db_path)

    def upsert_many(self, bars: list[PriceHistoryBar]) -> None:
        with connect(self.db_path) as conn:
            conn.executemany(
                """
                INSERT INTO price_history (ticker, date, open, high, low, close, volume, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker, date) DO UPDATE SET
                  open=excluded.open,
                  high=excluded.high,
                  low=excluded.low,
                  close=excluded.close,
                  volume=excluded.volume,
                  source=excluded.source
                """,
                [
                    (
                        bar.ticker,
                        bar.date.isoformat(),
                        bar.open,
                        bar.high,
                        bar.low,
                        bar.close,
                        bar.volume,
                        bar.source,
                    )
                    for bar in bars
                ],
            )

    def get_window(self, ticker: str, start: date, end: date) -> list[PriceHistoryBar]:
        with connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT ticker, date, open, high, low, close, volume, source
                FROM price_history
                WHERE ticker = ? AND date BETWEEN ? AND ?
                ORDER BY date ASC
                """,
                (ticker.upper(), start.isoformat(), end.isoformat()),
            ).fetchall()
        return [_row_to_bar(row) for row in rows]

    def fetch_yfinance_into_cache(self, ticker: str, start: date, end: date) -> list[PriceHistoryBar]:
        last_error: Exception | None = None
        for attempt in range(5):
            try:
                try:
                    bars = _fetch_yfinance(ticker, start, end)
                except RuntimeError:
                    bars = _fetch_yahoo_chart(ticker, start, end)
                self.upsert_many(bars)
                return bars
            except Exception as exc:  # pragma: no cover - exercised only with live adapter
                last_error = exc
                sleep(0.1 * (attempt + 1))
        raise RuntimeError(f"Unable to reconstruct price history for {ticker}") from last_error

    def latest_bar(self, ticker: str) -> PriceHistoryBar | None:
        with connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT ticker, date, open, high, low, close, volume, source
                FROM price_history
                WHERE ticker = ?
                ORDER BY date DESC
                LIMIT 1
                """,
                (ticker.upper(),),
            ).fetchone()
        return _row_to_bar(row) if row else None


def trading_day_offset(start: date, trading_days: int) -> date:
    calendar_date = _calendar_trading_day_offset(start, trading_days)
    if calendar_date is not None:
        return calendar_date
    step = 1 if trading_days >= 0 else -1
    remaining = abs(trading_days)
    current = start
    while remaining:
        current += timedelta(days=step)
        if current.weekday() < 5:
            remaining -= 1
    return current


def _calendar_trading_day_offset(start: date, trading_days: int) -> date | None:
    try:
        import pandas_market_calendars as mcal
    except ModuleNotFoundError:
        return None
    span_days = max(abs(trading_days) * 3, 10)
    if trading_days >= 0:
        schedule_start = start + timedelta(days=1)
        schedule_end = start + timedelta(days=span_days)
        schedule = mcal.get_calendar("NYSE").schedule(
            start_date=schedule_start.isoformat(),
            end_date=schedule_end.isoformat(),
        )
        sessions = list(schedule.index.date)
        return sessions[trading_days - 1] if trading_days and len(sessions) >= trading_days else start
    schedule_start = start - timedelta(days=span_days)
    schedule_end = start - timedelta(days=1)
    schedule = mcal.get_calendar("NYSE").schedule(
        start_date=schedule_start.isoformat(),
        end_date=schedule_end.isoformat(),
    )
    sessions = list(schedule.index.date)
    return sessions[trading_days] if len(sessions) >= abs(trading_days) else None


def _fetch_yfinance(ticker: str, start: date, end: date) -> list[PriceHistoryBar]:
    try:
        import yfinance as yf
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise RuntimeError("yfinance is not installed") from exc

    hist = yf.Ticker(ticker).history(start=start.isoformat(), end=(end + timedelta(days=1)).isoformat())
    bars: list[PriceHistoryBar] = []
    for idx, row in hist.iterrows():
        dt = idx.to_pydatetime()
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("America/New_York"))
        bars.append(
            PriceHistoryBar(
                ticker=ticker,
                date=dt.date(),
                open=float(row["Open"]) if row["Open"] == row["Open"] else None,
                high=float(row["High"]) if row["High"] == row["High"] else None,
                low=float(row["Low"]) if row["Low"] == row["Low"] else None,
                close=float(row["Close"]),
                volume=int(row["Volume"]) if row["Volume"] == row["Volume"] else None,
                source="yfinance",
            )
        )
    return bars


def _fetch_yahoo_chart(ticker: str, start: date, end: date) -> list[PriceHistoryBar]:
    period1 = int(datetime.combine(start, datetime.min.time()).timestamp())
    period2 = int(datetime.combine(end + timedelta(days=1), datetime.min.time()).timestamp())
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{quote(ticker.upper())}?period1={period1}&period2={period2}&interval=1d"
    )
    request = Request(url, headers={"User-Agent": "StockExpertFriend/1.0"})
    with urlopen(request, timeout=15) as response:
        data = json.loads(response.read().decode("utf-8"))
    result = data.get("chart", {}).get("result") or []
    if not result:
        raise RuntimeError(f"No Yahoo chart data for {ticker}")
    item = result[0]
    timestamps = item.get("timestamp") or []
    quote_data = (item.get("indicators", {}).get("quote") or [{}])[0]
    bars: list[PriceHistoryBar] = []
    for idx, ts in enumerate(timestamps):
        close = _nth(quote_data.get("close"), idx)
        if close is None:
            continue
        bars.append(
            PriceHistoryBar(
                ticker=ticker,
                date=datetime.fromtimestamp(ts, tz=ZoneInfo("America/New_York")).date(),
                open=_nth(quote_data.get("open"), idx),
                high=_nth(quote_data.get("high"), idx),
                low=_nth(quote_data.get("low"), idx),
                close=float(close),
                volume=int(_nth(quote_data.get("volume"), idx) or 0),
                source="yahoo_chart",
            )
        )
    if not bars:
        raise RuntimeError(f"No usable Yahoo chart rows for {ticker}")
    return bars


def _nth(values, idx: int):
    if not values or idx >= len(values):
        return None
    return values[idx]


def _row_to_bar(row) -> PriceHistoryBar:
    data = dict(row)
    data["date"] = datetime.strptime(data["date"], "%Y-%m-%d").date()
    return PriceHistoryBar(**data)
