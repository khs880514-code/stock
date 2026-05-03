from __future__ import annotations

from datetime import datetime

from app.data.event_calendar import EventCalendar
from app.journal.trade_journal import TradeJournal
from app.models import MacroSnapshot, PortfolioSnapshot


def build_premarket_briefing(
    portfolio: PortfolioSnapshot,
    event_calendar: EventCalendar,
    journal: TradeJournal,
    macro: MacroSnapshot,
    now: datetime,
) -> str:
    tickers = [holding.ticker for holding in portfolio.holdings]
    events = event_calendar.upcoming_events(tickers, since=now, days=14)
    lines = [
        "■ 08:30 국장 시작 전 브리핑",
        "",
        "어제 미장 ↔ 오늘 국장 연관성",
        _market_link_line(macro),
        "",
        "오늘/이번 주 일정",
    ]
    if events:
        for event in events[:5]:
            lines.append(f"- {event.ticker} {event.event_type}: {event.event_time.strftime('%Y-%m-%d %H:%M')}")
    else:
        lines.append("- 보유 종목 기준 주요 일정 없음")

    reviews = journal.one_week_reviews(now)
    lines.extend(["", "1주일 전 매매 회고"])
    if not reviews:
        lines.append("- 1주일 전 기록된 매매 없음")
    for trade in reviews[:3]:
        result = ""
        if trade.price_1w is not None and trade.price_at_entry:
            pct = (trade.price_1w - trade.price_at_entry) / trade.price_at_entry * 100
            result = f", 1주일 결과 {pct:+.1f}%"
        lines.append(
            f"- {trade.timestamp.date()}, {trade.ticker} {trade.action.upper()} "
            f"{trade.quantity:g}주. 당시 사유: \"{trade.reason_text}\". "
            f"FOMO {trade.fomo_score}/10{result}"
        )
    return _limit("\n".join(lines))


def _market_link_line(macro: MacroSnapshot) -> str:
    vix = macro.get("VIX")
    fx = macro.get("USD_KRW")
    wti = macro.get("WTI")
    parts: list[str] = []
    if vix:
        parts.append(f"VIX {vix.value:g}")
    if fx:
        parts.append(f"USD/KRW {fx.value:g}")
    if wti and wti.change_pct is not None:
        parts.append(f"WTI {wti.change_pct:+.1f}%")
    return "- " + ", ".join(parts) if parts else "- 매크로 데이터 없음"


def _limit(message: str, limit: int = 1500) -> str:
    return message if len(message) <= limit else message[: limit - 20].rstrip() + "\n...(축약)"

