from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

from app.db.database import connect, init_db


KST = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class NewsHeadline:
    ticker: str
    title: str
    url: str
    source_name: str
    published_at: str
    collected_at: str


class NewsStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        init_db(self.db_path)

    def upsert_many(self, items: list[NewsHeadline]) -> None:
        with connect(self.db_path) as conn:
            conn.executemany(
                """
                INSERT INTO news_headlines (
                  ticker, title, url, source_name, published_at, collected_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker, url) DO UPDATE SET
                  title=excluded.title,
                  source_name=excluded.source_name,
                  published_at=excluded.published_at,
                  collected_at=excluded.collected_at
                """,
                [
                    (
                        item.ticker,
                        item.title,
                        item.url,
                        item.source_name,
                        item.published_at,
                        item.collected_at,
                    )
                    for item in items
                ],
            )

    def latest(self, ticker: str | None = None, limit: int = 20) -> list[NewsHeadline]:
        params: tuple = ()
        where = ""
        if ticker:
            where = "WHERE ticker = ?"
            params = (ticker.upper(),)
        with connect(self.db_path) as conn:
            rows = conn.execute(
                f"""
                SELECT ticker, title, url, source_name, published_at, collected_at
                FROM news_headlines
                {where}
                ORDER BY collected_at DESC, published_at DESC
                LIMIT ?
                """,
                (*params, limit),
            ).fetchall()
        return [NewsHeadline(**dict(row)) for row in rows]


class GoogleNewsRssCollector:
    def collect(self, tickers: list[str], limit_per_ticker: int = 5) -> list[NewsHeadline]:
        collected: list[NewsHeadline] = []
        now = datetime.now(tz=KST).isoformat()
        for ticker in sorted({ticker.upper() for ticker in tickers if ticker.strip()}):
            query = quote(f"{ticker} stock")
            url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
            request = Request(url, headers={"User-Agent": "StockExpertFriend/1.0"})
            with urlopen(request, timeout=15) as response:
                root = ElementTree.fromstring(response.read())
            for item in root.findall(".//item")[:limit_per_ticker]:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                published = (item.findtext("pubDate") or "").strip()
                source_name = (item.findtext("source") or "Google News").strip()
                if title and link:
                    collected.append(
                        NewsHeadline(
                            ticker=ticker,
                            title=title,
                            url=link,
                            source_name=source_name,
                            published_at=published,
                            collected_at=now,
                        )
                    )
        return collected
