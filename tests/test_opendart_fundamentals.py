from __future__ import annotations

import io
import json
import zipfile

from app.config import AppConfig
from app.data.fundamentals_store import FundamentalSnapshot, FundamentalsStore
from app.data.opendart_fundamentals import OpenDartClient, snapshot_from_accounts, update_from_opendart
from app.web_ui import handle_post


class FakeResponse:
    def __init__(self, data: bytes) -> None:
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        return None

    def read(self) -> bytes:
        return self.data


def test_opendart_corp_code_and_snapshot_mapping():
    client = OpenDartClient(api_key="test-key", opener=fake_opener)

    corp = client.corp_code_for_ticker("005930.KS")
    assert corp.corp_code == "00126380"
    assert corp.corp_name == "삼성전자"

    payload = client.single_company_accounts("005930.KS", bsns_year=2025, reprt_code="11011")
    snapshot = snapshot_from_accounts(payload, "005930.KS", 2025, "11011", "AI_SEMICONDUCTOR")

    assert snapshot.ticker == "005930.KS"
    assert snapshot.company_name == "삼성전자"
    assert snapshot.as_of_date.isoformat() == "2025-12-31"
    assert snapshot.revenue_growth_pct == 25.0
    assert snapshot.operating_margin_pct == 20.0
    assert snapshot.operating_income_growth_pct == 100.0
    assert snapshot.net_margin_pct == 15.0
    assert snapshot.roe_pct == 12.5
    assert snapshot.roa_pct == 7.5
    assert snapshot.debt_to_equity_pct == 66.67
    assert snapshot.source == "opendart:fnlttSinglAcnt:2025:11011"


def test_opendart_update_persists_fundamental_snapshot(tmp_path):
    client = OpenDartClient(api_key="test-key", opener=fake_opener)
    db_path = tmp_path / "dart.sqlite3"

    saved = update_from_opendart(db_path, "005930", 2025, client=client, sector_tag="AI_SEMICONDUCTOR")
    loaded = FundamentalsStore(db_path).get("005930.KS")

    assert saved.ticker == "005930.KS"
    assert loaded is not None
    assert loaded.company_name == "삼성전자"
    assert loaded.revenue_growth_pct == 25.0


def test_web_dart_fundamental_post_uses_fetcher(tmp_path, monkeypatch):
    config = AppConfig(db_path=tmp_path / "web-dart.sqlite3")

    def fake_update(db_path, ticker, bsns_year, reprt_code, sector_tag):
        item = FundamentalSnapshot(
            ticker=ticker,
            market="KR",
            company_name="Fake Corp",
            sector_tag=sector_tag,
            revenue_growth_pct=3.0,
            source=f"opendart:fnlttSinglAcnt:{bsns_year}:{reprt_code}",
        )
        FundamentalsStore(db_path).upsert(item)
        return item

    monkeypatch.setattr("app.web.fundamental_screener.update_from_opendart", fake_update)
    notice, _ = handle_post(
        "/dart-fundamental",
        config,
        {"ticker": "005930.KS", "bsns_year": "2025", "reprt_code": "11011", "sector_tag": "AI_SEMICONDUCTOR"},
    )

    assert "OpenDART" in notice
    assert FundamentalsStore(config.db_path).get("005930.KS") is not None


def fake_opener(url: str) -> FakeResponse:
    if "corpCode.xml" in url:
        return FakeResponse(_corp_code_zip())
    if "fnlttSinglAcnt.json" in url:
        return FakeResponse(json.dumps(_accounts_payload(), ensure_ascii=False).encode("utf-8"))
    raise AssertionError(f"unexpected url: {url}")


def _corp_code_zip() -> bytes:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<result>
  <list><corp_code>00126380</corp_code><corp_name>삼성전자</corp_name><stock_code>005930</stock_code></list>
  <list><corp_code>00164779</corp_code><corp_name>SK하이닉스</corp_name><stock_code>000660</stock_code></list>
</result>"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("CORPCODE.xml", xml.encode("utf-8"))
    return buffer.getvalue()


def _accounts_payload() -> dict:
    return {
        "status": "000",
        "message": "정상",
        "list": [
            _row("매출액", "IS", "CFS", "1", "1,000", "800"),
            _row("영업이익", "IS", "CFS", "2", "200", "100"),
            _row("당기순이익", "IS", "CFS", "3", "150", "120"),
            _row("자산총계", "BS", "CFS", "4", "2,000", "1,800"),
            _row("부채총계", "BS", "CFS", "5", "800", "700"),
            _row("자본총계", "BS", "CFS", "6", "1,200", "1,100"),
        ],
    }


def _row(account_nm: str, sj_div: str, fs_div: str, ord_value: str, current: str, prior: str) -> dict:
    return {
        "account_nm": account_nm,
        "sj_div": sj_div,
        "fs_div": fs_div,
        "ord": ord_value,
        "thstrm_amount": current,
        "thstrm_add_amount": current,
        "frmtrm_amount": prior,
        "frmtrm_add_amount": prior,
        "currency": "KRW",
    }
