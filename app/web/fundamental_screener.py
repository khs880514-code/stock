from __future__ import annotations

import html
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.config import AppConfig
from app.data.default_universe import seed_user_default_universe
from app.data.filings_collector import FilingStore
from app.data.fundamentals_store import FundamentalSnapshot, FundamentalsStore
from app.data.market_fundamentals import update_market_fundamentals
from app.data.news_store import NewsStore
from app.data.opendart_fundamentals import update_from_opendart
from app.data.research_notes_store import ResearchNotesStore
from app.engines.stock_screener import ScreenerCandidate, screen


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


def handle_dart_fundamental_post(config: AppConfig, form: dict[str, str]) -> str:
    ticker = form.get("ticker", "").strip()
    bsns_year = int(form.get("bsns_year") or datetime.now(tz=KST).year - 1)
    reprt_code = form.get("reprt_code", "11011")
    sector_tag = form.get("sector_tag", "UNKNOWN")
    snapshot = update_from_opendart(
        config.db_path,
        ticker=ticker,
        bsns_year=bsns_year,
        reprt_code=reprt_code,
        sector_tag=sector_tag,
    )
    return f"OpenDART fundamentals saved: {snapshot.ticker} {snapshot.company_name}"


def handle_market_fundamental_post(config: AppConfig, form: dict[str, str]) -> str:
    ticker = form.get("ticker", "").strip()
    sector_tag = form.get("sector_tag", "UNKNOWN")
    snapshot = update_market_fundamentals(
        config.db_path,
        ticker=ticker,
        sector_tag=sector_tag,
        fx_usd_krw=config.fx_usd_krw,
        today=datetime.now(tz=KST).date(),
    )
    return f"Market summary saved: {snapshot.ticker} {snapshot.company_name}"


def handle_seed_test_universe_post(config: AppConfig) -> str:
    result = seed_user_default_universe(config, today=datetime.now(tz=KST).date())
    return (
        "Default test universe seeded: "
        f"accounts {result.accounts_added}, holdings {result.holdings_added}, "
        f"watchlist {result.watchlist_added}, fundamentals {result.fundamentals_added}"
    )


def build_screener_context(
    config: AppConfig,
) -> tuple[list[ScreenerCandidate], dict[str, dict[str, int]], dict[str, FundamentalSnapshot]]:
    snapshots = FundamentalsStore(config.db_path).list_all()
    candidates = screen(snapshots)
    snapshot_by_ticker = {item.ticker: item for item in snapshots}
    return candidates, _candidate_context_counts(config, candidates), snapshot_by_ticker


def render_screener_panel(
    candidates: list[ScreenerCandidate],
    candidate_context: dict[str, dict[str, int]],
    snapshot_by_ticker: dict[str, FundamentalSnapshot],
) -> str:
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
</div>
{_candidate_detail_cards(candidates, candidate_context, snapshot_by_ticker)}"""


def _candidate_context_counts(config: AppConfig, candidates: list[ScreenerCandidate]) -> dict[str, dict[str, int]]:
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
    dart_year = datetime.now(tz=KST).year - 1
    current_year = datetime.now(tz=KST).year
    return f"""<div class="stacked-forms">
<form method="post" action="/seed-test-universe">
  <button>Seed default test universe</button>
  <p class="form-note">Adds Samsung, SK Hynix, Pearl Abyss, QQQ, SMH, AAPL, AMD, and about 10 synthetic quality-screen test candidates only when missing.</p>
</form>
<form method="post" action="/dart-fundamental">
  <label>OpenDART ticker<input name="ticker" value="005930.KS" required></label>
  <div class="row"><label>Business year<input name="bsns_year" type="number" value="{dart_year}" min="2015" max="{current_year}"></label><label>Report<select name="reprt_code"><option value="11011">Annual 11011</option><option value="11013">Q1 11013</option><option value="11012">Half 11012</option><option value="11014">Q3 11014</option></select></label></div>
  <label>Sector tag<input name="sector_tag" value="AI_SEMICONDUCTOR"></label>
  <button>OpenDART fundamentals fetch</button>
  <p class="form-note">OpenDART key is read from local .env. This fills reported profitability/growth/stability fields; PER/PBR still need market-price data.</p>
</form>
<form method="post" action="/market-fundamental">
  <label>Market summary ticker<input name="ticker" value="005930.KS" required></label>
  <label>Sector tag<input name="sector_tag" value="AI_SEMICONDUCTOR"></label>
  <button>Market PER/PBR/momentum fetch</button>
  <p class="form-note">Uses yfinance/Yahoo where available. This merges valuation, market cap, dividend yield, FCF yield, and 3M/12M momentum without overwriting DART-only fields.</p>
</form>
<form method="post" action="/fundamental">
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
</form>
</div>"""


def _candidate_table(candidates: list[ScreenerCandidate], candidate_context: dict[str, dict[str, int]]) -> str:
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


def _candidate_row(item: ScreenerCandidate, context: dict[str, int]) -> str:
    reasons = "<br>".join(_e(reason) for reason in item.reasons[:3]) or "-"
    cautions = "<br>".join(_e(caution) for caution in item.cautions[:2])
    missing = ", ".join(item.missing_metrics[:5])
    caution_text = "<br>".join(part for part in [cautions, _e(f"부족: {missing}") if missing else ""] if part) or "-"
    linked = f"뉴스 {context['news']} / 공시 {context['filings']} / 리서치 {context['research']}"
    return (
        f"<tr><td><b>{_e(item.status)}</b></td><td>{_e(item.ticker)}<br><span>{_e(item.company_name or item.sector_tag)}</span></td>"
        f"<td>{item.score}<br><span>data {item.data_points}</span></td><td>{reasons}</td><td>{caution_text}</td><td>{_e(linked)}</td></tr>"
    )


def _candidate_detail_cards(
    candidates: list[ScreenerCandidate],
    candidate_context: dict[str, dict[str, int]],
    snapshot_by_ticker: dict[str, FundamentalSnapshot],
) -> str:
    if not candidates:
        return ""
    cards = "".join(
        _candidate_detail_card(item, snapshot_by_ticker.get(item.ticker), candidate_context.get(item.ticker, {}))
        for item in candidates[:12]
    )
    return f"""<div class="candidate-details">
  <h3>종목별 상세 검토</h3>
  <p class="form-note">각 카드는 재무지표 묶음과 다음 확인 질문입니다. 매수 신호가 아니라 사용자가 후보를 비교하기 위한 검토 메모입니다.</p>
  {cards}
</div>"""


def _candidate_detail_card(item: ScreenerCandidate, snapshot: FundamentalSnapshot | None, context: dict[str, int]) -> str:
    if snapshot is None:
        return ""
    questions = _review_questions(item, context)
    return f"""<details class="candidate-card">
  <summary><b>{_e(item.ticker)}</b> {_e(snapshot.company_name or item.sector_tag)} <span>{_e(item.status)} / score {item.score}</span></summary>
  <div class="candidate-card-grid">
    {_factor_box("가치", [("PER", snapshot.per), ("Forward PER", snapshot.forward_per), ("PBR", snapshot.pbr), ("PSR", snapshot.psr), ("EV/EBITDA", snapshot.ev_ebitda)])}
    {_factor_box("수익성", [("ROE %", snapshot.roe_pct), ("ROA %", snapshot.roa_pct), ("ROIC %", snapshot.roic_pct), ("영업이익률 %", snapshot.operating_margin_pct), ("순이익률 %", snapshot.net_margin_pct)])}
    {_factor_box("성장", [("매출 성장률 %", snapshot.revenue_growth_pct), ("EPS 성장률 %", snapshot.eps_growth_pct), ("영업이익 성장률 %", snapshot.operating_income_growth_pct)])}
    {_factor_box("안정성/현금흐름", [("부채비율 %", snapshot.debt_to_equity_pct), ("유동비율", snapshot.current_ratio), ("이자보상배율", snapshot.interest_coverage), ("FCF Yield %", snapshot.fcf_yield_pct)])}
    {_factor_box("모멘텀/출처", [("3M 모멘텀 %", snapshot.price_momentum_3m_pct), ("12M 모멘텀 %", snapshot.price_momentum_12m_pct), ("기준일", snapshot.as_of_date), ("출처", snapshot.source)])}
    <div class="factor-box"><b>다음 확인</b><ul>{''.join(f'<li>{_e(question)}</li>' for question in questions)}</ul></div>
  </div>
  <p class="form-note">메모: {_e(snapshot.notes or "-")}</p>
</details>"""


def _factor_box(title: str, rows: list[tuple[str, object]]) -> str:
    values = "".join(f"<tr><th>{_e(label)}</th><td>{_e(_fmt(value))}</td></tr>" for label, value in rows)
    return f'<div class="factor-box"><b>{_e(title)}</b><table><tbody>{values}</tbody></table></div>'


def _review_questions(item: ScreenerCandidate, context: dict[str, int]) -> list[str]:
    questions: list[str] = []
    if item.cautions:
        questions.append(f"주의 사유 확인: {item.cautions[0]}")
    if item.missing_metrics:
        questions.append(f"부족 지표 보강: {', '.join(item.missing_metrics[:4])}")
    if context.get("news", 0) == 0:
        questions.append("최근 뉴스 업데이트 후 실적/규제/수주/경쟁사 이슈 확인")
    if context.get("filings", 0) == 0:
        questions.append("최근 공시 또는 사업보고서 확인")
    if context.get("research", 0) == 0:
        questions.append("외부 리서치/NotebookLM 요약 또는 반대 근거 메모 추가")
    if not questions:
        questions.append("뉴스·공시·리서치와 재무지표가 서로 모순되지 않는지 최종 비교")
    return questions[:5]


def _fmt(value: object) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def _optional_float(form: dict[str, str], key: str) -> float | None:
    value = form.get(key, "").strip()
    return float(value) if value else None


def _e(value: object) -> str:
    return html.escape(str(value), quote=True)
