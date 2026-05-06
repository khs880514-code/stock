from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.config import AppConfig
from app.data.market_fundamentals import update_market_fundamentals
from app.data.news_store import GoogleNewsRssCollector, NewsStore


REVIEW_UNIVERSE: list[tuple[str, str]] = [
    ("005930.KS", "AI_SEMICONDUCTOR"),
    ("000660.KS", "AI_SEMICONDUCTOR"),
    ("035420.KS", "KOREA_PLATFORM"),
    ("035720.KS", "KOREA_PLATFORM"),
    ("005380.KS", "KOREA_AUTO"),
    ("000270.KS", "KOREA_AUTO"),
    ("068270.KS", "KOREA_BIO"),
    ("207940.KS", "KOREA_BIO"),
    ("373220.KS", "BATTERY"),
    ("051910.KS", "BATTERY"),
    ("AAPL", "BIG_TECH"),
    ("MSFT", "BIG_TECH"),
    ("GOOGL", "BIG_TECH"),
    ("AMZN", "BIG_TECH"),
    ("META", "BIG_TECH"),
    ("NVDA", "AI_SEMICONDUCTOR"),
    ("AMD", "AI_SEMICONDUCTOR"),
    ("AVGO", "AI_SEMICONDUCTOR"),
    ("ASML", "SEMICONDUCTOR_EQUIPMENT"),
    ("TSM", "AI_SEMICONDUCTOR"),
    ("QCOM", "AI_SEMICONDUCTOR"),
    ("MU", "MEMORY_SEMICONDUCTOR"),
    ("AMAT", "SEMICONDUCTOR_EQUIPMENT"),
    ("LRCX", "SEMICONDUCTOR_EQUIPMENT"),
    ("PLTR", "AI_SOFTWARE"),
    ("TSLA", "EV"),
    ("QQQ", "CORE_ETF"),
    ("SMH", "AI_SEMICONDUCTOR"),
]


@dataclass(frozen=True)
class ReviewUniverseResult:
    requested: int
    fundamentals_updated: int
    news_added: int
    failed: list[str]


def collect_review_universe(
    config: AppConfig,
    *,
    count: int = 20,
    today: date | None = None,
    collect_news: bool = True,
) -> ReviewUniverseResult:
    count = max(10, min(count, len(REVIEW_UNIVERSE)))
    today = today or date.today()
    selected = REVIEW_UNIVERSE[:count]
    updated = 0
    failed: list[str] = []

    for ticker, sector_tag in selected:
        try:
            update_market_fundamentals(
                config.db_path,
                ticker=ticker,
                sector_tag=sector_tag,
                fx_usd_krw=config.fx_usd_krw,
                today=today,
            )
            updated += 1
        except Exception:
            failed.append(ticker)

    news_count = 0
    if collect_news:
        try:
            items = GoogleNewsRssCollector().collect([ticker for ticker, _ in selected])
            NewsStore(config.db_path).upsert_many(items)
            news_count = len(items)
        except Exception:
            failed.append("news")

    return ReviewUniverseResult(
        requested=count,
        fundamentals_updated=updated,
        news_added=news_count,
        failed=failed,
    )
