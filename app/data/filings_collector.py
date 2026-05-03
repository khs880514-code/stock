from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
from time import sleep
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from app.db.database import connect, init_db
from app.models import Source


KST = ZoneInfo("Asia/Seoul")
SEC_TICKER_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
IMPORTANT_FORMS = {"8-K", "10-K", "10-Q", "S-1", "S-3", "424B", "424B5", "DEF 14A"}


@dataclass(frozen=True)
class FilingItem:
    ticker: str
    filing_type: str
    title: str
    source: Source
    cik: str = ""
    accession_number: str = ""
    filing_date: str = ""
    report_date: str = ""
    acceptance_datetime: str = ""
    primary_document: str = ""
    collected_at: str = ""


class FilingStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        init_db(self.db_path)

    def upsert_many(self, items: list[FilingItem]) -> None:
        with connect(self.db_path) as conn:
            conn.executemany(
                """
                INSERT INTO sec_filings (
                  ticker, cik, accession_number, form_type, filing_date, report_date,
                  acceptance_datetime, primary_document, primary_doc_description,
                  url, source_name, collected_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker, accession_number) DO UPDATE SET
                  cik=excluded.cik,
                  form_type=excluded.form_type,
                  filing_date=excluded.filing_date,
                  report_date=excluded.report_date,
                  acceptance_datetime=excluded.acceptance_datetime,
                  primary_document=excluded.primary_document,
                  primary_doc_description=excluded.primary_doc_description,
                  url=excluded.url,
                  source_name=excluded.source_name,
                  collected_at=excluded.collected_at
                """,
                [
                    (
                        item.ticker,
                        item.cik,
                        item.accession_number,
                        item.filing_type,
                        item.filing_date,
                        item.report_date,
                        item.acceptance_datetime,
                        item.primary_document,
                        item.title,
                        str(item.source.url),
                        item.source.title,
                        item.collected_at,
                    )
                    for item in items
                ],
            )

    def latest(self, ticker: str | None = None, limit: int = 20) -> list[FilingItem]:
        params: tuple = ()
        where = ""
        if ticker:
            where = "WHERE ticker = ?"
            params = (ticker.upper(),)
        with connect(self.db_path) as conn:
            rows = conn.execute(
                f"""
                SELECT ticker, cik, accession_number, form_type, filing_date, report_date,
                       acceptance_datetime, primary_document, primary_doc_description,
                       url, source_name, collected_at
                FROM sec_filings
                {where}
                ORDER BY filing_date DESC, acceptance_datetime DESC
                LIMIT ?
                """,
                (*params, limit),
            ).fetchall()
        return [
            FilingItem(
                ticker=row["ticker"],
                filing_type=row["form_type"],
                title=row["primary_doc_description"] or row["form_type"],
                source=Source(
                    title=row["source_name"],
                    url=row["url"],
                    published_at=row["filing_date"],
                ),
                cik=row["cik"],
                accession_number=row["accession_number"],
                filing_date=row["filing_date"],
                report_date=row["report_date"] or "",
                acceptance_datetime=row["acceptance_datetime"] or "",
                primary_document=row["primary_document"] or "",
                collected_at=row["collected_at"],
            )
            for row in rows
        ]


class SecFilingsCollector:
    def __init__(
        self,
        user_agent: str | None = None,
        timeout_seconds: int = 15,
        request_pause_seconds: float = 0.12,
    ) -> None:
        self.user_agent = user_agent or os.getenv(
            "SEF_SEC_USER_AGENT",
            "StockExpertFriend/1.0 contact@example.com",
        )
        self.timeout_seconds = timeout_seconds
        self.request_pause_seconds = request_pause_seconds

    def collect(self, tickers: list[str], limit_per_ticker: int = 5) -> list[FilingItem]:
        ticker_map = self._ticker_map()
        collected: list[FilingItem] = []
        for ticker in sorted({ticker.upper() for ticker in tickers if ticker.strip()}):
            cik = ticker_map.get(ticker)
            if cik is None:
                continue
            collected.extend(self._collect_ticker(ticker, cik, limit_per_ticker))
            sleep(self.request_pause_seconds)
        return collected

    def _ticker_map(self) -> dict[str, int]:
        data = self._request_json(SEC_TICKER_URL)
        return {
            item["ticker"].upper(): int(item["cik_str"])
            for item in data.values()
            if item.get("ticker") and item.get("cik_str")
        }

    def _collect_ticker(self, ticker: str, cik: int, limit: int) -> list[FilingItem]:
        data = self._request_json(SEC_SUBMISSIONS_URL.format(cik=f"{cik:010d}"))
        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form") or []
        collected: list[FilingItem] = []
        now = datetime.now(tz=KST).isoformat()
        for idx, form_type in enumerate(forms):
            if form_type not in IMPORTANT_FORMS:
                continue
            accession_number = _safe_nth(recent.get("accessionNumber"), idx)
            filing_date = _safe_nth(recent.get("filingDate"), idx)
            if not accession_number or not filing_date:
                continue
            primary_document = _safe_nth(recent.get("primaryDocument"), idx)
            description = _safe_nth(recent.get("primaryDocDescription"), idx) or form_type
            collected.append(
                FilingItem(
                    ticker=ticker,
                    filing_type=form_type,
                    title=description,
                    source=Source(
                        title=f"SEC EDGAR {form_type}",
                        url=_filing_url(cik, accession_number, primary_document),
                        published_at=filing_date,
                    ),
                    cik=f"{cik:010d}",
                    accession_number=accession_number,
                    filing_date=filing_date,
                    report_date=_safe_nth(recent.get("reportDate"), idx),
                    acceptance_datetime=_safe_nth(recent.get("acceptanceDateTime"), idx),
                    primary_document=primary_document,
                    collected_at=now,
                )
            )
            if len(collected) >= limit:
                break
        return collected

    def _request_json(self, url: str) -> dict:
        request = Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json",
            },
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))


class MockFilingsCollector:
    def collect(self, tickers: list[str]) -> list[FilingItem]:
        return [
            FilingItem(
                ticker=ticker.upper(),
                filing_type="MOCK",
                title=f"{ticker.upper()} mock filing placeholder",
                source=Source(title="SEC EDGAR", url="https://www.sec.gov/edgar/search/"),
                collected_at=datetime.now(tz=KST).isoformat(),
            )
            for ticker in tickers
        ]


def _safe_nth(values, idx: int) -> str:
    if not values or idx >= len(values):
        return ""
    return str(values[idx] or "")


def _filing_url(cik: int, accession_number: str, primary_document: str) -> str:
    accession_path = accession_number.replace("-", "")
    base = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_path}"
    return f"{base}/{primary_document}" if primary_document else base
