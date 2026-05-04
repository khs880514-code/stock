from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


KRX_HOLIDAYS_2026 = {
    date(2026, 1, 1): "New Year's Day",
    date(2026, 2, 16): "Korean New Year Holiday",
    date(2026, 2, 17): "Korean New Year Holiday",
    date(2026, 2, 18): "Korean New Year Holiday",
    date(2026, 5, 1): "Labor Day",
    date(2026, 5, 5): "Children's Day",
    date(2026, 5, 25): "Buddha's Birthday observed",
    date(2026, 8, 17): "Liberation Day observed",
    date(2026, 9, 24): "Chuseok Holiday",
    date(2026, 9, 25): "Chuseok Holiday",
    date(2026, 9, 28): "Chuseok Holiday observed",
    date(2026, 10, 5): "National Foundation Day observed",
    date(2026, 10, 9): "Hangul Day",
    date(2026, 12, 25): "Christmas Day",
    date(2026, 12, 31): "Year-end market closure",
}


@dataclass(frozen=True)
class MarketSessionStatus:
    market: str
    session_date: date
    is_open: bool
    reason: str = ""
    next_open_date: date | None = None


def status_for_ticker(ticker: str, market: str, session_date: date) -> MarketSessionStatus:
    normalized_market = _normalize_market(ticker, market)
    if normalized_market != "KR":
        return MarketSessionStatus(
            market=normalized_market,
            session_date=session_date,
            is_open=True,
            next_open_date=session_date,
        )
    return krx_status(session_date)


def krx_status(session_date: date) -> MarketSessionStatus:
    if session_date.weekday() >= 5:
        return MarketSessionStatus(
            market="KR",
            session_date=session_date,
            is_open=False,
            reason="weekend",
            next_open_date=next_krx_open_date(session_date),
        )
    holiday_reason = KRX_HOLIDAYS_2026.get(session_date)
    if holiday_reason:
        return MarketSessionStatus(
            market="KR",
            session_date=session_date,
            is_open=False,
            reason=holiday_reason,
            next_open_date=next_krx_open_date(session_date),
        )
    return MarketSessionStatus(
        market="KR",
        session_date=session_date,
        is_open=True,
        next_open_date=session_date,
    )


def next_krx_open_date(session_date: date) -> date:
    cursor = session_date + timedelta(days=1)
    for _ in range(14):
        if cursor.weekday() < 5 and cursor not in KRX_HOLIDAYS_2026:
            return cursor
        cursor += timedelta(days=1)
    return cursor


def _normalize_market(ticker: str, market: str) -> str:
    normalized_ticker = ticker.upper().strip()
    normalized_market = market.upper().strip()
    if normalized_ticker.endswith((".KS", ".KQ")):
        return "KR"
    return normalized_market


def _next_weekday(session_date: date) -> date:
    cursor = session_date + timedelta(days=1)
    while cursor.weekday() >= 5:
        cursor += timedelta(days=1)
    return cursor
