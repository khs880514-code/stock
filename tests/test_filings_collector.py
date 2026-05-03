from app.data.filings_collector import FilingItem, FilingStore, SecFilingsCollector
from app.models import Source


def test_filing_store_upserts_and_lists_latest(tmp_path):
    store = FilingStore(tmp_path / "filings.sqlite3")
    store.upsert_many(
        [
            FilingItem(
                ticker="AAPL",
                filing_type="8-K",
                title="Current report",
                source=Source(
                    title="SEC EDGAR 8-K",
                    url="https://www.sec.gov/Archives/edgar/data/320193/example/aapl.htm",
                    published_at="2026-05-01",
                ),
                cik="0000320193",
                accession_number="0000320193-26-000001",
                filing_date="2026-05-01",
                primary_document="aapl.htm",
                collected_at="2026-05-02T00:00:00+09:00",
            )
        ]
    )
    latest = store.latest("AAPL")
    assert len(latest) == 1
    assert latest[0].filing_type == "8-K"
    assert latest[0].accession_number == "0000320193-26-000001"


def test_sec_collector_parses_submissions_without_live_network():
    class FakeCollector(SecFilingsCollector):
        def _request_json(self, url: str) -> dict:
            if url.endswith("company_tickers.json"):
                return {"0": {"ticker": "AAPL", "cik_str": 320193, "title": "Apple Inc."}}
            return {
                "filings": {
                    "recent": {
                        "accessionNumber": ["0000320193-26-000001", "0000320193-26-000002"],
                        "filingDate": ["2026-05-01", "2026-04-01"],
                        "reportDate": ["2026-04-30", "2026-03-31"],
                        "acceptanceDateTime": ["20260501160000", "20260401160000"],
                        "form": ["8-K", "4"],
                        "primaryDocument": ["aapl-8k.htm", "ownership.xml"],
                        "primaryDocDescription": ["Current report", "Ownership"],
                    }
                }
            }

    items = FakeCollector(user_agent="TestApp/1.0 test@example.com", request_pause_seconds=0).collect(["AAPL"])
    assert len(items) == 1
    assert items[0].filing_type == "8-K"
    assert items[0].cik == "0000320193"
    assert "000032019326000001/aapl-8k.htm" in str(items[0].source.url)
