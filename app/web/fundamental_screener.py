from __future__ import annotations

import html
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.config import AppConfig
from app.data.filings_collector import FilingStore
from app.data.fundamentals_store import FundamentalSnapshot, FundamentalsStore
from app.data.news_store import NewsStore
from app.data.research_notes_store import ResearchNotesStore
from app.engines.stock_screener import screen


KST = ZoneInfo("Asia/Seoul")


def handle_fundamental_post(config: AppConfig, form: dict[str, str]) -> str:
    as_of = date.fromisoformat(form["as_of_date"]) if form.get("as_of_date") else datetime.now(tz=KST).date()
    snapshot = FundamentalSnapshot(
        ticker=form.get("ticker", ""),
        market=form.get("market", "KR"),
        company_name=form.get("company_name", ""),
        sector_tag=form.get("sector_tag", "UNKNOWN"),
        as_of_date=as_of,
        currency=form.get("currency", "KRW"),
        market_cap_krw=_optional_float(form, "market_cap_krw"),
        per=_optional_float(form, "per"),
        forward_per=_optional_float(form, "forward_per"),
        pbr=_optional_float(form, "pbr"),
        psr=_optional_float(form, "psr"),
        ev_ebitda=_optional_float(form, "ev_ebitda"),
        dividend_yield_pct=_optional_float(form, "dividend_yield_pct"),
        roe_pct=_optional_float(form, "roe_pct"),
        roa_pct=_optional_float(form, "roa_pct"),
        roic_pct=_optional_float(form, "roic_pct"),
        operating_margin_pct=_optional_float(form, "operating_margin_pct"),
        net_margin_pct=_optional_float(form, "net_margin_pct"),
        revenue_growth_pct=_optional_float(form, "revenue_growth_pct"),
        eps_growth_pct=_optional_float(form, "eps_growth_pct"),
        operating_income_growth_pct=_optional_float(form, "operating_income_growth_pct"),
        debt_to_equity_pct=_optional_float(form, "debt_to_equity_pct"),
        current_ratio=_optional_float(form, "current_ratio"),
        interest_coverage=_optional_float(form, "interest_coverage"),
        fcf_yield_pct=_optional_float(form, "fcf_yield_pct"),
        price_momentum_3m_pct=_optional_float(form, "price_momentum_3m_pct"),
        price_momentum_12m_pct=_optional_float(form, "price_momentum_12m_pct"),
        source=form.get("source", "manual"),
        notes=form.get("notes", ""),
    )
    FundamentalsStore(config.db_path).upsert(snapshot)
    return f"후보 재무지표 저장 완료: {snapshot.ticker.upper()}"


def build_screener_context(config: AppConfig) -> tuple[list, dict[str, dict[str, int]]]:
    candidates = screen(FundamentalsStore(config.db_path).list_all())
    return candidates, _candidate_context_counts(config, candidates)


def render_screener_panel(candidates, candidate_context: dict[str, dict[str, int]]) -> str:
    return f"""<div class="grid two">
  <div>
    <h3>재무지표 입력</h3>
    {_fundamental_form()}
  </div>
  <div>
    <h3>필터 결과</h3>
    <p class="form-note">PASS는 매수 지시가 아니라 추가 검토 후보입니다. 데이터가 부족하면 WATCH로 남기고, 뉴스/공시/리서치 근거를 옆에 붙입니다.</p>
    {_candidate_table(candidates, candidate_context)}
  </div>
</div>"""


def _candidate_context_counts(config: AppConfig, candidates) -> dict[str, dict[str, int]]:
    news_store = NewsStore(config.db_path)
    filing_store = FilingStore(config.db_path)
    research_store = ResearchNotesStore(config.db_path)
    counts: dict[str, dict[str, int]] = {}
    for item in candidates:
        counts[item.ticker] = {
            "news": len(news_store.latest(item.ticker, limit=5)),
            "filings": len(filing_store.latest(item.ticker, limit=5)),
            "research": len(research_store.latest(item.ticker, limit=5)),
        }
    return counts


def _fundamental_form() -> str:
    return """<form method="post" action="/fundamental">
  <label>종목<input name="ticker" value="005930.KS" required></label>
  <div class="row"><label>시장<select name="market"><option>KR</option><option>US</option></select></label><label>통화<select name="currency"><option>KRW</option><option>USD</option></select></label></div>
  <div class="row"><label>회사명<input name="company_name" value="삼성전자"></label><label>섹터 태그<input name="sector_tag" value="AI_SEMICONDUCTOR"></label></div>
  <div class="row"><label>기준일<input name="as_of_date" type="date"></label><label>출처<input name="source" value="manual"></label></div>
  <div class="row"><label>시가총액 KRW<input name="market_cap_krw" type="number" step="1"></label><label>PER<input name="per" type="number" step="0.01"></label></div>
  <div class="row"><label>Forward PER<input name="forward_per" type="number" step="0.01"></label><label>PBR<input name="pbr" type="number" step="0.01"></label></div>
  <div class="row"><label>PSR<input name="psr" type="number" step="0.01"></label><label>EV/EBITDA<input name="ev_ebitda" type="number" step="0.01"></label></div>
  <div class="row"><label>배당수익률 %<input name="dividend_yield_pct" type="number" step="0.01"></label><label>ROE %<input name="roe_pct" type="number" step="0.01"></label></div>
  <div class="row"><label>ROA %<input name="roa_pct" type="number" step="0.01"></label><label>ROIC %<input name="roic_pct" type="number" step="0.01"></label></div>
  <div class="row"><label>영업이익률 %<input name="operating_margin_pct" type="number" step="0.01"></label><label>순이익률 %<input name="net_margin_pct" type="number" step="0.01"></label></div>
  <div class="row"><label>매출 성장률 %<input name="revenue_growth_pct" type="number" step="0.01"></label><label>EPS 성장률 %<input name="eps_growth_pct" type="number" step="0.01"></label></div>
  <div class="row"><label>영업이익 성장률 %<input name="operating_income_growth_pct" type="number" step="0.01"></label><label>부채비율 %<input name="debt_to_equity_pct" type="number" step="0.01"></label></div>
  <div class="row"><label>유동비율<input name="current_ratio" type="number" step="0.01"></label><label>이자보상배율<input name="interest_coverage" type="number" step="0.01"></label></div>
  <div class="row"><label>FCF Yield %<input name="fcf_yield_pct" type="number" step="0.01"></label><label>3M 모멘텀 %<input name="price_momentum_3m_pct" type="number" step="0.01"></label></div>
  <div class="row"><label>12M 모멘텀 %<input name="price_momentum_12m_pct" type="number" step="0.01"></label><label>메모<input name="notes" placeholder="확인한 출처/주의점"></label></div>
  <button>재무지표 저장</button>
</form>"""


def _candidate_table(candidates, candidate_context: dict[str, dict[str, int]]) -> str:
    if not candidates:
        return '<p class="empty">저장된 재무지표가 없습니다. 왼쪽에서 후보 종목 지표를 먼저 입력하세요.</p>'
    rows = "".join(
        _candidate_row(item, candidate_context.get(item.ticker, {"news": 0, "filings": 0, "research": 0}))
        for item in candidates
    )
    return (
        "<table><thead><tr><th>상태</th><th>종목</th><th>점수</th><th>근거</th><th>주의/부족</th><th>연결 정보</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


def _candidate_row(item, context: dict[str, int]) -> str:
    reasons = "<br>".join(_e(reason) for reason in item.reasons[:3]) or "-"
    cautions = "<br>".join(_e(caution) for caution in item.cautions[:2])
    missing = ", ".join(item.missing_metrics[:5])
    caution_text = "<br>".join(part for part in [cautions, _e(f"부족: {missing}") if missing else ""] if part) or "-"
    linked = f"뉴스 {context['news']} / 공시 {context['filings']} / 리서치 {context['research']}"
    return (
        f"<tr><td><b>{_e(item.status)}</b></td><td>{_e(item.ticker)}<br><span>{_e(item.company_name or item.sector_tag)}</span></td>"
        f"<td>{item.score}<br><span>data {item.data_points}</span></td><td>{reasons}</td><td>{caution_text}</td><td>{_e(linked)}</td></tr>"
    )


def _optional_float(form: dict[str, str], key: str) -> float | None:
    value = form.get(key, "").strip()
    return float(value) if value else None


def _e(value: object) -> str:
    return html.escape(str(value), quote=True)
