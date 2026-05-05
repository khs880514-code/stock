from __future__ import annotations

import io
import json
import os
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable
from urllib.parse import urlencode
from urllib.request import urlopen
from xml.etree import ElementTree

from app.data.fundamentals_store import FundamentalSnapshot, FundamentalsStore


CORP_CODE_URL = "https://opendart.fss.or.kr/api/corpCode.xml"
SINGLE_ACCOUNT_URL = "https://opendart.fss.or.kr/api/fnlttSinglAcnt.json"
REPORT_END_DATES = {
    "11013": (3, 31),
    "11012": (6, 30),
    "11014": (9, 30),
    "11011": (12, 31),
}


@dataclass(frozen=True)
class DartCorpCode:
    corp_code: str
    corp_name: str
    stock_code: str


class OpenDartClient:
    def __init__(
        self,
        api_key: str | None = None,
        opener: Callable[[str], object] = urlopen,
    ) -> None:
        self.api_key = api_key or os.getenv("SEF_DART_API_KEY", "")
        if not self.api_key:
            raise ValueError("SEF_DART_API_KEY is not set.")
        self._opener = opener

    def corp_codes(self) -> list[DartCorpCode]:
        url = f"{CORP_CODE_URL}?{urlencode({'crtfc_key': self.api_key})}"
        data = _read_response(self._opener(url))
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            xml_name = archive.namelist()[0]
            root = ElementTree.fromstring(archive.read(xml_name))
        result: list[DartCorpCode] = []
        for item in root.findall("list"):
            stock_code = _xml_text(item, "stock_code")
            if not stock_code:
                continue
            result.append(
                DartCorpCode(
                    corp_code=_xml_text(item, "corp_code"),
                    corp_name=_xml_text(item, "corp_name"),
                    stock_code=stock_code.zfill(6),
                )
            )
        return result

    def corp_code_for_ticker(self, ticker: str) -> DartCorpCode:
        stock_code = normalize_stock_code(ticker)
        for item in self.corp_codes():
            if item.stock_code == stock_code:
                return item
        raise ValueError(f"OpenDART corp code not found for {ticker}.")

    def single_company_accounts(self, ticker: str, bsns_year: int, reprt_code: str = "11011") -> dict:
        corp = self.corp_code_for_ticker(ticker)
        params = {
            "crtfc_key": self.api_key,
            "corp_code": corp.corp_code,
            "bsns_year": str(bsns_year),
            "reprt_code": reprt_code,
        }
        url = f"{SINGLE_ACCOUNT_URL}?{urlencode(params)}"
        payload = json.loads(_read_response(self._opener(url)).decode("utf-8"))
        if payload.get("status") not in {None, "000"}:
            raise ValueError(f"OpenDART error {payload.get('status')}: {payload.get('message')}")
        return {**payload, "corp_name": corp.corp_name, "stock_code": corp.stock_code}


def update_from_opendart(
    db_path: Path | str,
    ticker: str,
    bsns_year: int,
    reprt_code: str = "11011",
    sector_tag: str = "UNKNOWN",
    client: OpenDartClient | None = None,
) -> FundamentalSnapshot:
    client = client or OpenDartClient()
    payload = client.single_company_accounts(ticker, bsns_year=bsns_year, reprt_code=reprt_code)
    snapshot = snapshot_from_accounts(payload, ticker, bsns_year, reprt_code, sector_tag)
    FundamentalsStore(db_path).upsert(snapshot)
    return snapshot


def snapshot_from_accounts(
    payload: dict,
    ticker: str,
    bsns_year: int,
    reprt_code: str,
    sector_tag: str = "UNKNOWN",
) -> FundamentalSnapshot:
    rows = payload.get("list", [])
    revenue = _pick_account(rows, ["매출액", "수익(매출액)", "영업수익"], "IS")
    prior_revenue = _pick_account(rows, ["매출액", "수익(매출액)", "영업수익"], "IS", prior=True)
    operating_income = _pick_account(rows, ["영업이익"], "IS")
    prior_operating_income = _pick_account(rows, ["영업이익"], "IS", prior=True)
    net_income = _pick_account(rows, ["당기순이익"], "IS")
    assets = _pick_account(rows, ["자산총계"], "BS")
    liabilities = _pick_account(rows, ["부채총계"], "BS")
    equity = _pick_account(rows, ["자본총계"], "BS")
    return FundamentalSnapshot(
        ticker=canonical_kr_ticker(ticker),
        market="KR",
        company_name=str(payload.get("corp_name", "")),
        sector_tag=sector_tag or "UNKNOWN",
        as_of_date=_report_end_date(bsns_year, reprt_code),
        currency=_currency(rows),
        roe_pct=_ratio(net_income, equity),
        roa_pct=_ratio(net_income, assets),
        operating_margin_pct=_ratio(operating_income, revenue),
        net_margin_pct=_ratio(net_income, revenue),
        revenue_growth_pct=_growth(revenue, prior_revenue),
        operating_income_growth_pct=_growth(operating_income, prior_operating_income),
        debt_to_equity_pct=_ratio(liabilities, equity),
        source=f"opendart:fnlttSinglAcnt:{bsns_year}:{reprt_code}",
        notes=(
            "OpenDART single-company major accounts. Ratios are derived from reported major "
            "accounts; valuation metrics still need a market-price data source."
        ),
    )


def normalize_stock_code(ticker: str) -> str:
    code = ticker.strip().upper().split(".", 1)[0]
    return code.zfill(6) if code.isdigit() else code


def canonical_kr_ticker(ticker: str) -> str:
    raw = ticker.strip().upper()
    if "." in raw:
        code, suffix = raw.split(".", 1)
        return f"{normalize_stock_code(code)}.{suffix}"
    return f"{normalize_stock_code(raw)}.KS"


def _pick_account(rows: list[dict], names: list[str], statement: str, prior: bool = False) -> float | None:
    candidates = [
        row
        for row in rows
        if row.get("sj_div") == statement and any(name in str(row.get("account_nm", "")) for name in names)
    ]
    candidates.sort(key=lambda row: (0 if row.get("fs_div") == "CFS" else 1, int(row.get("ord") or 9999)))
    for row in candidates:
        keys = ["frmtrm_add_amount", "frmtrm_amount"] if prior else _amount_keys(statement)
        for key in keys:
            amount = _parse_amount(row.get(key))
            if amount is not None:
                return amount
    return None


def _amount_keys(statement: str) -> list[str]:
    if statement == "IS":
        return ["thstrm_add_amount", "thstrm_amount"]
    return ["thstrm_amount", "thstrm_add_amount"]


def _parse_amount(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text or text in {"-", "N/A"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    try:
        amount = float(text)
    except ValueError:
        return None
    return -amount if negative else amount


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in {None, 0}:
        return None
    return round(numerator / denominator * 100, 2)


def _growth(current: float | None, prior: float | None) -> float | None:
    if current is None or prior in {None, 0}:
        return None
    return round((current - prior) / abs(prior) * 100, 2)


def _report_end_date(bsns_year: int, reprt_code: str) -> date:
    month, day = REPORT_END_DATES.get(reprt_code, (12, 31))
    return date(int(bsns_year), month, day)


def _currency(rows: list[dict]) -> str:
    for row in rows:
        value = str(row.get("currency", "")).strip().upper()
        if value:
            return value
    return "KRW"


def _read_response(response: object) -> bytes:
    with response:
        return response.read()


def _xml_text(element: ElementTree.Element, name: str) -> str:
    found = element.find(name)
    return (found.text or "").strip() if found is not None else ""
