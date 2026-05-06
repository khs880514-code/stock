from __future__ import annotations

import html
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs
from zoneinfo import ZoneInfo

from app.alerts.message_templates import format_decision_message
from app.config import LEGAL_DISCLAIMER, AppConfig
from app.data.account_store import AccountStore, BrokerAccount, account_route_note, default_accounts
from app.data.buy_check_log import BuyCheckLogStore
from app.data.conditional_orders import ConditionalDecisionStore
from app.data.data_status import build_api_readiness_status, build_ticker_data_status
from app.data.earnings_calendar_store import EarningsCalendarStore, EarningsDate
from app.data.filings_collector import FilingStore, SecFilingsCollector
from app.data.news_store import GoogleNewsRssCollector, NewsStore
from app.data.price_history import PriceHistoryStore
from app.data.portfolio_store import PortfolioStore, holding_value_krw
from app.data.research_notes_store import ResearchNote, ResearchNotesStore
from app.data.ticker_sensitivity import TickerSensitivityStore
from app.data.watchlist_store import WatchlistStore
from app.db.database import init_db
from app.engines.buy_check_mode import review_buy_request
from app.engines.news_flags import classify_headline, summarize_news_flags
from app.journal.trade_journal import TradeJournal
from app.models import BuyReviewRequest, ConditionalDecision, Holding, MistakeType, TickerSensitivitySnapshot, TradeEntry
from app.web.beginner_guide import render_tab_intro, render_workflow_guide
from app.web.data_status_panel import render_data_status_panel
from app.web.fundamental_screener import (
    build_screener_context,
    handle_auto_candidates_post,
    handle_dart_fundamental_post,
    handle_fundamental_post,
    handle_market_fundamental_post,
    handle_seed_test_universe_post,
    render_screener_panel,
)
from app.web.styles import CSS
from app.web.tabs import render_tab_nav, render_tab_script
from app.web.portfolio_panel import render_holdings_table
from app.web.ticker_search import render_ticker_datalist, render_ticker_script, ticker_input, ticker_list_input


KST = ZoneInfo("Asia/Seoul")


def run_web_ui(config: AppConfig, host: str = "127.0.0.1", port: int = 8765) -> None:
    init_db(config.db_path)

    class Handler(StockExpertFriendHandler):
        app_config = config

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Stock Expert Friend UI: http://{host}:{port}")
    server.serve_forever()


class StockExpertFriendHandler(BaseHTTPRequestHandler):
    app_config: AppConfig

    def do_GET(self) -> None:
        if self.path not in {"/", "/index.html"}:
            self._send_html(render_dashboard(self.app_config, notice="존재하지 않는 경로입니다."))
            return
        self._send_html(render_dashboard(self.app_config))

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        form = {key: values[0] for key, values in parse_qs(body).items()}
        try:
            notice, decision = handle_post(self.path, self.app_config, form)
        except Exception as exc:
            notice, decision = f"처리 실패: {exc}", ""
        self._send_html(render_dashboard(self.app_config, notice=notice, decision_message=decision))

    def log_message(self, format: str, *args) -> None:
        return

    def _send_html(self, content: str) -> None:
        data = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def handle_post(path: str, config: AppConfig, form: dict[str, str]) -> tuple[str, str]:
    if path == "/cash":
        cash = _int(form, "cash_krw")
        PortfolioStore(config.db_path, config).set_cash(cash)
        return f"현금 저장 완료: {cash:,}원", ""

    if path == "/holding":
        store = PortfolioStore(config.db_path, config)
        avg_price = _float(form, "avg_price")
        ticker = form.get("ticker", "").upper().strip()
        current_price_text = form.get("current_price", "").strip()
        price_note = "입력 현재가 사용"
        if current_price_text:
            current_price = float(current_price_text)
        else:
            latest_price = _fetch_latest_price_for_holding(config, ticker)
            if latest_price is not None:
                current_price = latest_price.close
                price_note = f"최신 저장가 반영: {latest_price.close:g} {latest_price.date.isoformat()}"
            else:
                current_price = avg_price
                price_note = "현재가를 가져오지 못해 평단을 임시 현재가로 사용"
        holding = Holding(
            ticker=ticker,
            account_key=form.get("account_key", "GENERAL_TOSS"),
            market=form.get("market", "US"),
            quantity=_float(form, "quantity"),
            avg_price=avg_price,
            current_price=current_price,
            currency=form.get("currency", "USD"),
            asset_type=form.get("asset_type", "EQUITY").upper(),
            sector_tag=form.get("sector_tag", "UNKNOWN").upper(),
        )
        store.save_holding(holding)
        value_krw = int(holding_value_krw(holding, config.fx_usd_krw))
        return f"보유종목 저장 완료: {holding.ticker} / {holding.quantity:g}주 / 평가 {value_krw:,}원 / {price_note}", ""

    if path == "/delete-holding":
        ticker = form.get("ticker", "").upper().strip()
        deleted = PortfolioStore(config.db_path, config).delete_holding(ticker)
        if deleted:
            return f"보유종목 삭제 완료: {ticker}", ""
        return f"삭제할 보유종목을 찾지 못했습니다: {ticker}", ""

    if path == "/trade":
        journal = TradeJournal(config.db_path)
        entry = TradeEntry(
            timestamp=datetime.now(tz=KST),
            ticker=form.get("ticker", ""),
            account_key=form.get("account_key", "GENERAL_TOSS"),
            action=form.get("trade_action", "BUY").upper(),
            quantity=_float(form, "quantity"),
            avg_price=_float(form, "avg_price"),
            reason_text=form.get("reason", ""),
            fomo_score=_int(form, "fomo"),
            friend_influence_score=_int(form, "influence"),
            price_at_entry=_float(form, "price_at_entry") or _float(form, "avg_price"),
            mistake_type=MistakeType(form.get("mistake_type", "NONE").upper()),
        )
        trade_id = journal.add_trade(entry)
        return f"매매 일지 저장 완료: #{trade_id}", ""

    if path == "/watch":
        WatchlistStore(config.db_path).add_or_update(
            ticker=form.get("ticker", ""),
            market=form.get("market", "US"),
            reason=form.get("reason", ""),
            priority=_int(form, "priority"),
            sector_tag=form.get("sector_tag", "UNKNOWN"),
        )
        return f"관심종목 저장 완료: {form.get('ticker', '').upper()}", ""

    if path == "/sensitivity":
        today = datetime.now(tz=KST).date()
        TickerSensitivityStore(config.db_path).upsert(
            TickerSensitivitySnapshot(
                ticker=form.get("ticker", ""),
                market=form.get("market", "KR"),
                sector_tag=form.get("sector_tag", "UNKNOWN").upper(),
                us_sector_proxy_symbol=form.get("proxy", "").upper() or None,
                foreign_ownership_pct=_optional_float(form, "foreign_pct"),
                foreign_ownership_taken_at=today if form.get("foreign_pct") else None,
                us_sector_corr_60d=_optional_float(form, "sector_corr"),
                us_market_corr_60d=_optional_float(form, "market_corr"),
                fx_corr_60d=_optional_float(form, "fx_corr"),
                beta_to_kospi_60d=_optional_float(form, "beta_kospi"),
                corr_taken_at=today,
                manual_override=True,
            )
        )
        return f"종목 민감도 저장 완료: {form.get('ticker', '').upper()}", ""

    if path == "/seed-kr-semiconductor-sensitivity":
        count = TickerSensitivityStore(config.db_path).seed_kr_semiconductor_estimates()
        return f"국내 반도체 추정 민감도 저장 완료: {count}개", ""

    if path == "/blackout":
        until = date.fromisoformat(form.get("until_date", "")) if form.get("until_date") else datetime.now(tz=KST).date() + timedelta(days=1)
        WatchlistStore(config.db_path).set_blackout(
            form.get("ticker", ""),
            until,
            form.get("reason", "manual decision protection blackout"),
        )
        return f"관찰 블랙아웃 설정 완료: {form.get('ticker', '').upper()}", ""

    if path == "/clear-blackout":
        WatchlistStore(config.db_path).clear_blackout(form.get("ticker", ""), form.get("reason", "manual clear"))
        return f"관찰 블랙아웃 해제 완료: {form.get('ticker', '').upper()}", ""

    if path == "/conditional":
        expires_at = None
        if form.get("until_date"):
            expires_at = datetime.combine(date.fromisoformat(form["until_date"]), datetime.max.time(), tzinfo=KST)
        decision_id = ConditionalDecisionStore(config.db_path).add(
            ConditionalDecision(
                created_at=datetime.now(tz=KST),
                ticker=form.get("ticker", ""),
                condition_text=form.get("condition", ""),
                planned_action=form.get("planned_action", "WATCH").upper(),
                expires_at=expires_at,
                note=form.get("note", ""),
            )
        )
        return f"조건부 결정 저장 완료: #{decision_id}", ""

    if path == "/account":
        account = BrokerAccount(
            account_key=form.get("account_key", ""),
            account_type=form.get("account_type", "GENERAL"),
            broker_name=form.get("broker_name", ""),
            default_for=form.get("default_for", ""),
            notes=form.get("notes", ""),
        )
        AccountStore(config.db_path).upsert(account)
        return f"계좌 설정 저장 완료: {account.account_key.upper()} / {account.broker_name}", ""

    if path == "/seed-default-accounts":
        store = AccountStore(config.db_path)
        for account in default_accounts():
            store.upsert(account)
        return "기본 계좌 설정 완료: 일반=토스증권, ISA=키움증권", ""

    if path == "/seed-test-universe":
        return handle_seed_test_universe_post(config), ""

    if path == "/auto-candidates":
        return handle_auto_candidates_post(config, form), ""

    if path == "/buy-check":
        store = PortfolioStore(config.db_path, config)
        portfolio = store.snapshot()
        journal = TradeJournal(config.db_path)
        now = datetime.now(tz=KST)
        ticker = form.get("ticker", "").upper()
        account = AccountStore(config.db_path).get(form.get("account_key", "GENERAL_TOSS"))
        price_store = PriceHistoryStore(config.db_path)
        price_history = price_store.get_window(ticker, now.date() - timedelta(days=120), now.date())
        latest_price = price_store.latest_bar(ticker)
        latest_news = NewsStore(config.db_path).latest(ticker, limit=5)
        latest_filings = FilingStore(config.db_path).latest(ticker, limit=5)
        latest_research = ResearchNotesStore(config.db_path).latest(ticker, limit=5)
        data_status = build_ticker_data_status(config.db_path, [ticker], now.date())
        events = EarningsCalendarStore(config.db_path).upcoming_events([ticker], now)
        buy_request = BuyReviewRequest(
            ticker=ticker,
            desired_amount_krw=_int(form, "amount_krw"),
            reason_text=form.get("reason", ""),
            fomo_score=_int(form, "fomo"),
            friend_influence_score=_int(form, "influence"),
            price_type=form.get("price_type", "limit"),
        )
        decision = review_buy_request(
            buy_request,
            portfolio=portfolio,
            events=events,
            recent_trades=journal.recent_trades(now - timedelta(days=14)),
            now=now,
            config=config,
            price_history=price_history,
        )
        message = format_decision_message(f"{ticker} 매수 검토", decision)
        message = _append_recent_context(
            message,
            latest_price,
            latest_news,
            latest_filings,
            latest_research,
            data_status,
            account,
        )
        journal.log_alert("buy_check_web", message, decision)
        BuyCheckLogStore(config.db_path).add(
            decision_at=now,
            request=buy_request,
            decision=decision,
            price_at_decision=latest_price.close if latest_price else None,
        )
        return "매수 검토 완료", message

    if path == "/update-prices":
        tickers = _tracked_tickers(config)
        if not tickers:
            return "가격 업데이트 대상이 없습니다. 보유종목이나 관심종목을 먼저 입력하세요.", ""
        count = update_prices(config, tickers)
        return f"가격 업데이트 완료: {len(tickers)}개 종목, {count}개 가격 행 저장", ""

    if path == "/update-news":
        tickers = _tracked_tickers(config)
        if not tickers:
            return "뉴스 업데이트 대상이 없습니다. 보유종목이나 관심종목을 먼저 입력하세요.", ""
        items = GoogleNewsRssCollector().collect(tickers)
        NewsStore(config.db_path).upsert_many(items)
        return f"뉴스 업데이트 완료: {len(items)}개 헤드라인 저장", ""

    if path == "/update-filings":
        tickers = _tracked_tickers(config)
        if not tickers:
            return "공시 업데이트 대상이 없습니다. 보유종목이나 관심종목을 먼저 입력하세요.", ""
        items = SecFilingsCollector().collect(tickers)
        FilingStore(config.db_path).upsert_many(items)
        return f"공시 업데이트 완료: {len(items)}개 SEC 제출 저장", ""

    if path == "/earnings":
        ticker = form.get("ticker", "").upper()
        earnings_date = date.fromisoformat(form.get("earnings_date", ""))
        EarningsCalendarStore(config.db_path).upsert(
            EarningsDate(
                ticker=ticker,
                earnings_date=earnings_date,
                source=form.get("source", "manual"),
                source_url=form.get("source_url", ""),
                note=form.get("note", ""),
            )
        )
        return f"실적 일정 저장 완료: {ticker} {earnings_date.isoformat()}", ""

    if path == "/fundamental":
        return handle_fundamental_post(config, form), ""

    if path == "/dart-fundamental":
        return handle_dart_fundamental_post(config, form), ""

    if path == "/market-fundamental":
        return handle_market_fundamental_post(config, form), ""

    if path == "/research-note":
        note_id = ResearchNotesStore(config.db_path).add(
            ResearchNote(
                tickers=_split_tickers(form.get("tickers", "")),
                source_type=form.get("source_type", "NOTEBOOKLM"),
                source_name=form.get("source_name", ""),
                source_url=form.get("source_url", ""),
                reliability=form.get("reliability", "MEDIUM"),
                summary=form.get("summary", ""),
                counter_points=form.get("counter_points", ""),
                check_questions=form.get("check_questions", ""),
            )
        )
        return f"외부 리서치 노트 저장 완료: #{note_id}", ""

    return "알 수 없는 요청입니다.", ""


def render_dashboard(config: AppConfig, notice: str = "", decision_message: str = "") -> str:
    store = PortfolioStore(config.db_path, config)
    portfolio = store.snapshot()
    watch_items = WatchlistStore(config.db_path).list_items()
    accounts = AccountStore(config.db_path).list_accounts()
    tracked_tickers = sorted({holding.ticker for holding in portfolio.holdings} | {item.ticker for item in watch_items})
    trades = TradeJournal(config.db_path).recent_trades()
    sensitivity_items = TickerSensitivityStore(config.db_path).list_all()
    conditional_items = ConditionalDecisionStore(config.db_path).list_active(now=datetime.now(tz=KST))
    latest_news = NewsStore(config.db_path).latest(limit=12)
    latest_filings = FilingStore(config.db_path).latest(limit=12)
    screener_candidates, candidate_context, snapshot_by_ticker = build_screener_context(config)
    upcoming_earnings = EarningsCalendarStore(config.db_path).upcoming(
        tracked_tickers,
        datetime.now(tz=KST).date(),
        days=60,
    )
    research_notes = ResearchNotesStore(config.db_path).latest(limit=8)
    latest_prices = _latest_prices(config, portfolio.holdings, watch_items)
    data_status = build_ticker_data_status(
        config.db_path,
        tracked_tickers,
        datetime.now(tz=KST).date(),
    )
    api_status = build_api_readiness_status()
    holdings_value = max(portfolio.total_value_krw - portfolio.cash_krw, 0)
    cash_pct = (portfolio.cash_krw / portfolio.total_value_krw * 100) if portfolio.total_value_krw else 0
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>주식 판단 친구</title>
  <style>{CSS}</style>
</head>
<body>
  <header>
    <div>
      <h1>주식 판단 친구 <span>Stock Expert Friend</span></h1>
      <p>{_e(LEGAL_DISCLAIMER).replace(chr(10), "<br>")}</p>
    </div>
  </header>
  <main>
    {_notice(notice)}
    {render_tab_nav()}
    {render_ticker_datalist()}
    <section class="metrics tab-panel" data-tab-panel="overview">
      {_metric("총 평가액", f"{portfolio.total_value_krw:,}원")}
      {_metric("현금", f"{portfolio.cash_krw:,}원 ({cash_pct:.1f}%)")}
      {_metric("보유 평가액", f"{holdings_value:,}원")}
      {_metric("리스크 태그", ", ".join(portfolio.risk_tags) if portfolio.risk_tags else "없음")}
    </section>
    <section class="tab-panel" data-tab-panel="overview">
      {render_workflow_guide()}
    </section>
    <section class="tab-panel" data-tab-panel="overview">
      <h2>오늘 적용되는 안전 규칙</h2>
      {_rule_context_panel(config, portfolio, trades)}
    </section>
    <section class="tab-panel" data-tab-panel="buy-review">
      {render_tab_intro("매수 전 점검", "실제로 사기 전에 가장 먼저 쓰는 화면입니다. 종목, 금액, FOMO, 외부영향을 넣고 룰엔진으로 한 번 멈춰 봅니다.", "결과가 나온 뒤 보유 현황을 참고하고, 필요할 때만 아래 고급 보호장치를 펼치세요.")}
      <h2>매수 전 체크</h2>
      <div class="score-layout">
        {_buy_check_form()}
        {_score_guide()}
      </div>
    </section>
    {_decision(decision_message)}
    <section class="tab-panel" data-tab-panel="data-check">
      {render_tab_intro("정보 확인", "판단 전에 가격, 뉴스, 공시, 실적일이 얼마나 최신인지 확인하는 탭입니다.", "정보가 오래됐으면 후보를 고르기 전에 업데이트 버튼을 먼저 누르세요.")}
      <h2>최근 정보</h2>
      {_recent_info_panel(latest_prices, latest_news, latest_filings)}
    </section>
    <section class="tab-panel" data-tab-panel="candidate">
      {render_tab_intro("후보 고르기", "좋아 보이는 종목을 바로 사는 화면이 아니라, 재무지표와 근거로 후보를 좁히는 화면입니다.", "후보를 골랐다면 4번 매수 전 점검에서 FOMO와 외부영향을 다시 입력하세요.")}
      <h2>후보 찾기</h2>
      {render_screener_panel(screener_candidates, candidate_context, snapshot_by_ticker)}
    </section>
    <section class="tab-panel" data-tab-panel="data-check">
      <h2>정보 최신성</h2>
      {render_data_status_panel(data_status, api_status)}
    </section>
    <section class="tab-panel" data-tab-panel="settings">
      <h2>계좌 설정</h2>
      {_account_panel(accounts)}
    </section>
    <section class="grid two tab-panel" data-tab-panel="data-check">
      <div>
        <h2>실적 일정</h2>
        {_earnings_form()}
        {_earnings_table(upcoming_earnings)}
      </div>
      <div>
        <h2>외부 리서치 노트</h2>
        {_research_form()}
        {_research_notes_list(research_notes)}
      </div>
    </section>
    <section class="tab-panel" data-tab-panel="buy-review">
      <h2>현재 보유 상태</h2>
      {render_holdings_table(portfolio.holdings, config)}
    </section>
    <section class="tab-panel" data-tab-panel="buy-review">
      <h2>룰엔진 판단 기준</h2>
      {_rule_reference()}
    </section>
    <section class="tab-panel" data-tab-panel="buy-review">
      <details class="advanced-panel">
        <summary>고급 보호장치 펼치기: 종목 민감도 / 결정 보호</summary>
        <div class="grid two">
          <div>
            <h2>종목 민감도 / 연휴 갭</h2>
            {_sensitivity_form()}
            {_sensitivity_table(sensitivity_items)}
          </div>
          <div>
            <h2>결정 보호</h2>
            {_blackout_form()}
            {_conditional_form()}
            {_conditional_table(conditional_items)}
          </div>
        </div>
      </details>
    </section>
    <section class="tab-panel" data-tab-panel="portfolio">
      {render_tab_intro("내 계좌", "Toss 일반계좌와 Kiwoom ISA를 수동으로 맞추는 탭입니다. 자동 동기화는 의도적으로 사용하지 않습니다.", "보유와 현금이 맞으면 기록/복기 탭에서 매매 이유를 남기세요.")}
      <div class="grid three">
      <div>
        <h2>현금 입력</h2>
        {_cash_form(portfolio.cash_krw)}
      </div>
      <div>
        <h2>보유종목 입력</h2>
        {_holding_form()}
      </div>
      <div>
        <h2>관심종목 입력</h2>
        {_watch_form()}
      </div>
      </div>
    </section>
    <section class="tab-panel" data-tab-panel="portfolio">
      <h2>현재 보유종목 수정/삭제</h2>
      {render_holdings_table(portfolio.holdings, config)}
      <h2>관심종목</h2>
      {_watchlist_table(watch_items)}
    </section>
    <section class="tab-panel" data-tab-panel="journal">
      {render_tab_intro("기록/복기", "수익보다 중요한 것은 왜 샀고 왜 팔았는지 남기는 것입니다. 이 기록이 다음 룰 개선의 재료가 됩니다.")}
      <div class="score-layout">
        <div>
          <h2>매매 일지 입력</h2>
          {_trade_form()}
        </div>
        {_score_guide(compact=True)}
      </div>
      <h2>최근 매매 일지</h2>
      {_trades_table(trades)}
    </section>
  </main>
  {render_tab_script()}
  {render_ticker_script()}
</body>
</html>"""


def _cash_form(cash: int) -> str:
    return f"""<form method="post" action="/cash">
  <label>현금 KRW<input name="cash_krw" type="number" value="{cash}" required></label>
  <button>저장</button>
</form>"""


def _holding_form() -> str:
    return f"""<form method="post" action="/holding">
  {ticker_input("종목", "AAPL")}
  <label>계좌<select name="account_key"><option value="GENERAL_TOSS">일반 - 토스증권</option><option value="ISA_KIWOOM">ISA - 키움증권</option></select></label>
  <div class="row"><label>시장<select name="market"><option>US</option><option>KR</option></select></label><label>통화<select name="currency"><option>USD</option><option>KRW</option></select></label></div>
  <div class="row"><label>수량<input name="quantity" type="number" step="0.0001" required></label><label>평단<input name="avg_price" type="number" step="0.0001" required></label></div>
  <div class="row"><label>현재가<input name="current_price" type="number" step="0.0001"></label><label>자산유형<input name="asset_type" value="EQUITY"></label></div>
  <label>섹터 태그<input name="sector_tag" value="BIG_TECH"></label>
  <button>저장</button>
</form>"""


def _watch_form() -> str:
    return f"""<form method="post" action="/watch">
  {ticker_input("종목", "AMD")}
  <div class="row"><label>시장<select name="market"><option>US</option><option>KR</option></select></label><label>우선순위<input name="priority" type="number" value="2" min="1" max="5"></label></div>
  <label>섹터 태그<input name="sector_tag" value="AI_SEMICONDUCTOR"></label>
  <label>관찰 사유<textarea name="reason" required>실적 발표 후 재검토</textarea></label>
  <button>저장</button>
</form>"""


def _sensitivity_form() -> str:
    return """<div class="stacked-forms">
<form method="post" action="/seed-kr-semiconductor-sensitivity">
  <button>삼성전자/하이닉스 추정 민감도 저장</button>
  <p class="form-note">실제 관측값이 아니라 시뮬레이션용 출발점입니다. 외국인 지분과 상관 관측일은 비워두며, 확인 후 직접 덮어쓰세요.</p>
</form>
<form method="post" action="/sensitivity">
  {ticker_input("종목", "005930.KS")}
  <div class="row"><label>시장<select name="market"><option>KR</option><option>US</option></select></label><label>섹터 태그<input name="sector_tag" value="AI_SEMICONDUCTOR"></label></div>
  <div class="row"><label>미국 프록시<input name="proxy" value="SMH"></label><label>외국인 지분 %<input name="foreign_pct" type="number" step="0.01" placeholder="53.0"></label></div>
  <div class="row"><label>미국 섹터 상관<input name="sector_corr" type="number" step="0.01" placeholder="0.78"></label><label>KOSPI 베타<input name="beta_kospi" type="number" step="0.01" placeholder="1.00"></label></div>
  <div class="row"><label>미국 시장 상관<input name="market_corr" type="number" step="0.01"></label><label>환율 상관<input name="fx_corr" type="number" step="0.01"></label></div>
  <button>민감도 저장</button>
</form>
</div>"""


def _sensitivity_table(items) -> str:
    if not items:
        return '<p class="empty">저장된 종목 민감도 없음</p>'
    rows = "".join(
        (
            f"<tr><td>{_e(item.ticker)}</td><td>{_e(item.sector_tag)}</td>"
            f"<td>{_e(item.us_sector_proxy_symbol or '-')}</td>"
            f"<td>{_e(item.foreign_ownership_pct if item.foreign_ownership_pct is not None else '-')}</td>"
            f"<td>{_e(item.us_sector_corr_60d if item.us_sector_corr_60d is not None else '-')}</td>"
            f"<td>{_e(item.beta_to_kospi_60d if item.beta_to_kospi_60d is not None else '-')}</td></tr>"
        )
        for item in items
    )
    return "<table><thead><tr><th>종목</th><th>섹터</th><th>프록시</th><th>외국인%</th><th>섹터상관</th><th>베타</th></tr></thead><tbody>" + rows + "</tbody></table>"


def _blackout_form() -> str:
    return f"""<div class="stacked-forms">
  <form method="post" action="/blackout">
    {ticker_input("블랙아웃 종목", "005930.KS")}
    <div class="row"><label>해제일<input name="until_date" type="date"></label><label>사유<input name="reason" value="후회 추격 방지"></label></div>
    <button>관찰 블랙아웃 설정</button>
  </form>
  <form method="post" action="/clear-blackout">
    {ticker_input("해제 종목", "005930.KS")}
    <button>블랙아웃 해제</button>
  </form>
</div>"""


def _conditional_form() -> str:
    return f"""<form method="post" action="/conditional">
  {ticker_input("조건부 종목", "005930.KS")}
  <label>조건<textarea name="condition" required>외국인 순매수와 섹터 프록시 강세가 동시에 확인되면 재검토</textarea></label>
  <div class="row"><label>계획 행동<select name="planned_action"><option>WATCH</option><option>SMALL_BUY_CANDIDATE</option><option>NO_TRADE</option></select></label><label>만료일<input name="until_date" type="date"></label></div>
  <label>메모<textarea name="note"></textarea></label>
  <button>조건부 결정 저장</button>
</form>"""


def _conditional_table(items) -> str:
    if not items:
        return '<p class="empty">활성 조건부 결정 없음</p>'
    rows = "".join(
        (
            f"<tr><td>#{item.id or '-'}</td><td>{_e(item.ticker)}</td><td>{_e(item.planned_action)}</td>"
            f"<td>{_e(item.condition_text)}</td><td>{_e(item.expires_at.date().isoformat() if item.expires_at else '-')}</td></tr>"
        )
        for item in items
    )
    return "<table><thead><tr><th>ID</th><th>종목</th><th>행동</th><th>조건</th><th>만료</th></tr></thead><tbody>" + rows + "</tbody></table>"


def _account_panel(accounts) -> str:
    return f"""<div class="account-panel">
  <div>
    <form method="post" action="/seed-default-accounts">
      <button>기본값 저장: 일반 토스 / ISA 키움</button>
    </form>
    <p>현재는 계좌 라우팅 메모입니다. 토스/키움 API 연결과 계좌별 동일종목 분리 보유는 다음 단계에서 확장합니다.</p>
  </div>
  <div>
    {_account_form()}
  </div>
  <div>
    {_accounts_table(accounts)}
  </div>
</div>"""


def _account_form() -> str:
    return """<form method="post" action="/account">
  <label>계좌 키<input name="account_key" value="GENERAL_TOSS" required></label>
  <div class="row"><label>계좌 유형<select name="account_type"><option>GENERAL</option><option>ISA</option><option>PENSION</option><option>OTHER</option></select></label><label>증권사<input name="broker_name" value="토스증권" required></label></div>
  <label>기본 용도<input name="default_for" value="일반 매매/해외주식"></label>
  <label>메모<textarea name="notes" placeholder="수동 입력 기준, API 연결 전 주의사항 등"></textarea></label>
  <button>계좌 설정 저장</button>
</form>"""


def _accounts_table(accounts) -> str:
    if not accounts:
        return '<p class="empty">저장된 계좌 설정 없음</p>'
    rows = "".join(
        (
            f"<tr><td>{_e(item.account_key)}</td><td>{_e(item.account_type)}</td>"
            f"<td>{_e(item.broker_name)}</td><td>{_e(item.default_for)}</td>"
            f"<td>{_e(item.notes)}</td></tr>"
        )
        for item in accounts
    )
    return f"<table><thead><tr><th>키</th><th>유형</th><th>증권사</th><th>용도</th><th>메모</th></tr></thead><tbody>{rows}</tbody></table>"


def _earnings_form() -> str:
    return f"""<form method="post" action="/earnings">
  {ticker_input("종목", "AMD")}
  <div class="row"><label>실적일<input name="earnings_date" type="date" required></label><label>출처<input name="source" value="Investor Relations"></label></div>
  <label>출처 URL<input name="source_url" placeholder="https://..."></label>
  <label>메모<textarea name="note" placeholder="확정/예상 여부, 장전/장후 등"></textarea></label>
  <button>실적 일정 저장</button>
</form>"""


def _research_form() -> str:
    return f"""<form method="post" action="/research-note">
  {ticker_list_input("종목들", "AMD,AAPL")}
  <div class="row"><label>자료 유형<select name="source_type"><option>NOTEBOOKLM</option><option>YOUTUBE</option><option>ARTICLE</option><option>USER_NOTE</option></select></label><label>신뢰도<select name="reliability"><option>HIGH</option><option>MEDIUM</option><option>LOW</option></select></label></div>
  <label>출처명<input name="source_name" value="김지윤의 지식플레이"></label>
  <label>출처 URL<input name="source_url" placeholder="https://..."></label>
  <label>요약/근거<textarea name="summary" required placeholder="NotebookLM 요약, 핵심 주장, 반대 근거, 확인할 원문 링크 등을 붙여넣기"></textarea></label>
  <label>반대근거<textarea name="counter_points" placeholder="이 자료가 틀릴 수 있는 이유, 반대 시나리오"></textarea></label>
  <label>확인질문<textarea name="check_questions" placeholder="매수 전 직접 확인할 질문"></textarea></label>
  <button>리서치 노트 저장</button>
</form>"""


def _trade_form() -> str:
    return f"""<form method="post" action="/trade">
  {ticker_input("종목", "AAPL")}
  <label>계좌<select name="account_key"><option value="GENERAL_TOSS">일반 - 토스증권</option><option value="ISA_KIWOOM">ISA - 키움증권</option></select></label>
  <div class="row"><label>행동<select name="trade_action"><option>BUY</option><option>SELL</option><option>HOLD</option></select></label><label>수량<input name="quantity" type="number" step="0.0001" required></label></div>
  <div class="row"><label>평균가<input name="avg_price" type="number" step="0.0001" required></label><label>진입가<input name="price_at_entry" type="number" step="0.0001"></label></div>
  <div class="row"><label>FOMO<input name="fomo" type="number" min="0" max="10" value="3"></label><label>외부 영향<input name="influence" type="number" min="0" max="10" value="1"></label></div>
  <label>사유<textarea name="reason" required>분할 매수 기록</textarea></label>
  <input type="hidden" name="mistake_type" value="NONE">
  <button>저장</button>
</form>"""


def _buy_check_form() -> str:
    return f"""<form method="post" action="/buy-check">
  {ticker_input("종목", "AMD")}
  <label>검토 금액 KRW<input name="amount_krw" type="number" value="1000000" required></label>
  <label>검토 계좌<select name="account_key"><option value="GENERAL_TOSS">일반 - 토스증권</option><option value="ISA_KIWOOM">ISA - 키움증권</option></select></label>
  <div class="row"><label>FOMO<input name="fomo" type="number" min="0" max="10" value="5"></label><label>외부 영향<input name="influence" type="number" min="0" max="10" value="1"></label></div>
  <input type="hidden" name="price_type" value="limit">
  <label>검토 사유<textarea name="reason" required>왜 지금 검토하는지 입력</textarea></label>
  <button>룰엔진 확인</button>
</form>"""


def _score_guide(compact: bool = False) -> str:
    class_name = "score-guide compact" if compact else "score-guide"
    return f"""<aside class="{class_name}">
  <h3>점수 입력 기준</h3>
  <div class="guide-block">
    <strong>FOMO</strong>
    <ul>
      <li><b>0-2</b> 감정 압박 거의 없음</li>
      <li><b>3-4</b> 하루 기다릴 수 있음</li>
      <li><b>5-6</b> 가격을 자주 확인함</li>
      <li><b>7-8</b> 오늘 놓칠까 봐 사고 싶음</li>
      <li><b>9-10</b> 충동에 가까움</li>
    </ul>
  </div>
  <div class="guide-block">
    <strong>외부 영향</strong>
    <ul>
      <li><b>0-2</b> 내 계획과 기록 중심</li>
      <li><b>3-4</b> 참고만 한 수준</li>
      <li><b>5-6</b> 외부 의견 영향 큼</li>
      <li><b>7</b> 외부 말이 없었으면 안 봤을 가능성</li>
      <li><b>8-10</b> 추천/영상/커뮤니티가 핵심 동기</li>
    </ul>
  </div>
  <p>FOMO 7 이상은 대기, 9 이상 또는 외부 영향 8 이상은 차단 쪽으로 작동합니다.</p>
  <p>이 점수는 강제 장치가 아니라 자기기록입니다. 낮게 적으면 통과할 수 있지만, 사유 텍스트와 매매 결과에 함께 남습니다.</p>
  <p>사유에 놓칠까/후회/추천/커뮤니티 같은 표현이 있는데 점수를 낮게 적으면 불일치 경고나 대기가 붙습니다.</p>
</aside>"""


def _rule_context_panel(config: AppConfig, portfolio, trades) -> str:
    recent_buys = [
        trade
        for trade in trades
        if trade.action.upper() == "BUY"
        and trade.timestamp >= datetime.now(tz=KST) - timedelta(days=14)
    ]
    data_rows = [
        ("포트폴리오", "수동 입력한 현금과 보유종목"),
        ("최근 매매", f"최근 14일 BUY 기록 {len(recent_buys)}건"),
        ("실적 일정", "DB에 저장한 실적일을 매수 검토의 D-7 차단 룰에 연결"),
        ("가격 급락 룰", "가격 업데이트 후 저장된 히스토리를 매수 검토에 연결"),
        ("뉴스/RSS", "뉴스 업데이트 후 헤드라인과 주의 플래그를 검토 결과에 표시"),
        ("SEC 공시", "공시 업데이트 후 최근 8-K/10-Q/10-K 등을 검토 결과에 표시"),
    ]
    limit_rows = [
        ("1회 신규매수", f"{config.single_buy_max_krw:,}원"),
        ("1일 신규매수", f"{config.daily_buy_limit_krw:,}원"),
        ("최소 현금", f"{config.min_cash_krw:,}원"),
        ("1종목 비중", f"{config.max_single_position_pct:.0%}"),
        ("동일 테마 비중", f"{config.max_theme_pct:.0%}"),
    ]
    return f"""<div class="rule-context">
  <div>
    <h3>현재 입력 데이터</h3>
    <table><tbody>{''.join(f'<tr><th>{_e(k)}</th><td>{_e(v)}</td></tr>' for k, v in data_rows)}</tbody></table>
  </div>
  <div>
    <h3>보수적 기본 한도</h3>
    <table><tbody>{''.join(f'<tr><th>{_e(k)}</th><td>{_e(v)}</td></tr>' for k, v in limit_rows)}</tbody></table>
  </div>
  <div>
    <h3>판단 흐름</h3>
    <ol>
      <li>입력한 종목, 금액, 사유, FOMO, 외부 영향을 읽음</li>
      <li>현금/비중/최근 매매/실적/FOMO/손실 추가 투입을 확인</li>
      <li>하나라도 차단 조건이면 <b>NO_TRADE</b></li>
      <li>차단은 아니지만 감속 조건이면 금액 상한을 줄임</li>
      <li>주문은 하지 않고 기록과 알림만 남김</li>
    </ol>
  </div>
</div>"""


def _rule_reference() -> str:
    rows = [
        ("NO_TRADE", "지금은 아무것도 하지 않음. 룰엔진 차단 조건이 있음."),
        ("WATCH", "관찰만. 매수 후보 표시도 아님."),
        ("SMALL_BUY_CANDIDATE", "소액 후보. 주문 지시가 아니며 사용자가 다시 판단."),
        ("FOMO", "7 이상은 24시간 대기, 9 이상은 차단."),
        ("외부 영향", "8 이상은 차단. 추천/영상/커뮤니티 영향이 핵심이면 높게 입력."),
        ("실적 D-7", "보유/검토 종목의 실적 발표 7일 이내 신규매수 차단."),
        ("비중", "1종목 25%, 동일 테마 35%를 넘으면 차단."),
        ("현금", f"매수 후 현금이 기본 하한 미만이면 차단."),
        ("손실 종목 추가", "큰 손실 상태의 종목 추가 투입은 차단."),
        ("post_drop_chase", "최근 5거래일 급락 종목 추격매수는 경고 또는 차단."),
        ("holiday_gap_setup", "국내 휴장 중 미국 섹터가 크게 움직이고 종목 민감도가 높으면 매수 상한을 낮춤."),
        ("post_run_decomposition", "급등을 시장/섹터/뉴스 설명분으로 분해하고 잔여 급등만 추격 위험으로 표시."),
        ("decision_protection", "NO_TRADE/WATCH 이후 급등을 보고 따라 사는 후회 추격과 관찰 블랙아웃을 관리."),
    ]
    return f"""<div class="rule-reference">
  <table>
    <thead><tr><th>항목</th><th>의미</th></tr></thead>
    <tbody>{''.join(f'<tr><td>{_e(k)}</td><td>{_e(v)}</td></tr>' for k, v in rows)}</tbody>
  </table>
</div>"""


def _recent_info_panel(latest_prices, latest_news, latest_filings) -> str:
    return f"""<div class="recent-info">
  <div>
    <h3>정보 업데이트</h3>
    <div class="button-row">
      <form method="post" action="/update-prices"><button>가격 업데이트</button></form>
      <form method="post" action="/update-news"><button>뉴스 업데이트</button></form>
      <form method="post" action="/update-filings"><button>공시 업데이트</button></form>
    </div>
    <p>뉴스와 공시는 매수/매도 결정을 직접 바꾸지 않습니다. 출처 있는 참고 정보와 주의 플래그로 매수 검토 결과에 붙습니다.</p>
  </div>
  <div>
    <h3>최근 가격</h3>
    {_latest_prices_table(latest_prices)}
  </div>
  <div>
    <h3>최근 뉴스</h3>
    {_latest_news_list(latest_news)}
  </div>
  <div>
    <h3>최근 SEC 공시</h3>
    {_latest_filings_list(latest_filings)}
  </div>
</div>"""


def _latest_prices_table(items) -> str:
    if not items:
        return '<p class="empty">저장된 가격 없음</p>'
    rows = "".join(
        f"<tr><td>{_e(item['ticker'])}</td><td>{_e(item['date'])}</td><td>{item['close']:.2f}</td><td>{_e(item['source'])}</td></tr>"
        for item in items
    )
    return f"<table><thead><tr><th>종목</th><th>일자</th><th>종가</th><th>소스</th></tr></thead><tbody>{rows}</tbody></table>"


def _latest_news_list(items) -> str:
    if not items:
        return '<p class="empty">저장된 뉴스 없음</p>'
    rows = "".join(_news_item(item) for item in items)
    return f'<ul class="news-list">{rows}</ul>'


def _news_item(item) -> str:
    flags = classify_headline(item.title)
    flag_html = f'<span class="news-flags">{" / ".join(_e(flag) for flag in flags)}</span>' if flags else ""
    return (
        f'<li><b>{_e(item.ticker)}</b> '
        f'<a href="{_e(item.url)}" target="_blank" rel="noreferrer">{_e(item.title)}</a>'
        f'<span>{_e(item.source_name)}</span>{flag_html}</li>'
    )


def _latest_filings_list(items) -> str:
    if not items:
        return '<p class="empty">저장된 공시 없음</p>'
    rows = "".join(
        (
            f'<li><b>{_e(item.ticker)}</b> '
            f'<a href="{_e(item.source.url)}" target="_blank" rel="noreferrer">'
            f'{_e(item.filing_type)} {_e(item.filing_date)}</a>'
            f'<span>{_e(item.title)}</span></li>'
        )
        for item in items
    )
    return f'<ul class="news-list">{rows}</ul>'


def _earnings_table(items) -> str:
    if not items:
        return '<p class="empty">저장된 예정 실적 없음</p>'
    rows = "".join(
        f"<tr><td>{_e(item.ticker)}</td><td>{_e(item.earnings_date.isoformat())}</td><td>{_e(item.source)}</td><td>{_e(item.note)}</td></tr>"
        for item in items
    )
    return f"<table><thead><tr><th>종목</th><th>실적일</th><th>출처</th><th>메모</th></tr></thead><tbody>{rows}</tbody></table>"


def _research_notes_list(items) -> str:
    if not items:
        return '<p class="empty">저장된 리서치 노트 없음</p>'
    rows = "".join(
        (
            f'<li><b>{_e(",".join(item.tickers))}</b> {_e(item.source_type)} / {_e(item.reliability)}'
            f'<span>{_e(item.source_name)}</span><span>{_e(item.summary[:180])}</span>'
            f'<span>반대근거: {_e(item.counter_points[:120] or "-")}</span>'
            f'<span>확인질문: {_e(item.check_questions[:120] or "-")}</span></li>'
        )
        for item in items
    )
    return f'<ul class="news-list">{rows}</ul>'


def _watchlist_table(items) -> str:
    if not items:
        return '<p class="empty">관심종목 없음</p>'
    rows = "".join(
        f"<tr><td>P{item.priority}</td><td>{_e(item.ticker)}</td><td>{_e(item.sector_tag)}</td><td>{_e(item.reason)}</td></tr>"
        for item in items
    )
    return f"<table><thead><tr><th>우선</th><th>종목</th><th>태그</th><th>사유</th></tr></thead><tbody>{rows}</tbody></table>"


def _trades_table(trades) -> str:
    if not trades:
        return '<p class="empty">매매 일지 없음</p>'
    rows = "".join(
        f"<tr><td>{_e(t.timestamp.strftime('%Y-%m-%d %H:%M'))}</td><td>{_e(t.ticker)}</td><td>{_e(t.account_key)}</td><td>{_e(t.action)}</td><td>{t.quantity:g}</td><td>{t.avg_price:g}</td><td>{t.fomo_score}/10</td><td>{_e(t.reason_text)}</td></tr>"
        for t in trades[:20]
    )
    return f"<table><thead><tr><th>시각</th><th>종목</th><th>계좌</th><th>행동</th><th>수량</th><th>가격</th><th>FOMO</th><th>사유</th></tr></thead><tbody>{rows}</tbody></table>"


def _metric(label: str, value: str) -> str:
    return f'<div class="metric"><span>{_e(label)}</span><strong>{_e(value)}</strong></div>'


def _notice(text: str) -> str:
    return f'<div class="notice">{_e(text)}</div>' if text else ""


def _decision(text: str) -> str:
    return (
        f"""<section class="tab-panel" data-tab-panel="buy-review">
  <h2>검토 결과</h2>
  <pre>{_e(text)}</pre>
  <div class="result-note">
    <b>읽는 법:</b> 판단값은 주문 지시가 아닙니다. <b>NO_TRADE</b>는 차단 조건이 있다는 뜻이고,
    <b>SMALL_BUY_CANDIDATE</b>는 룰상 소액 검토 후보라는 뜻입니다. 최종 행동은 사용자가 직접 결정합니다.
  </div>
</section>"""
        if text
        else ""
    )


def _append_recent_context(
    message: str,
    latest_price,
    latest_news,
    latest_filings,
    latest_research,
    data_status,
    account,
) -> str:
    lines = [message, "", "[최근 정보]"]
    if latest_price is None:
        lines.append("- 최근 가격: 저장된 가격 없음. 먼저 가격 업데이트를 누르세요.")
    else:
        lines.append(
            f"- 최근 가격: {latest_price.date.isoformat()} 종가 {latest_price.close:.2f} "
            f"({latest_price.source})"
        )

    if not latest_news:
        lines.append("- 최근 뉴스: 저장된 뉴스 없음. 먼저 뉴스 업데이트를 누르세요.")
    else:
        flag_summary = summarize_news_flags(latest_news)
        if flag_summary:
            lines.append(f"- 뉴스 플래그: {', '.join(flag_summary)}")
        else:
            lines.append("- 뉴스 플래그: 특이 키워드 없음")
        lines.append("- 최근 헤드라인:")
        for item in latest_news[:3]:
            lines.append(f"  - {item.title} ({item.source_name}) {item.url}")

    if not latest_filings:
        lines.append("- 최근 SEC 공시: 저장된 공시 없음. 먼저 공시 업데이트를 누르세요.")
    else:
        lines.append("- 최근 SEC 공시:")
        for item in latest_filings[:3]:
            lines.append(
                f"  - {item.filing_type} {item.filing_date}: {item.title} "
                f"({item.source.url})"
            )
    if not latest_research:
        lines.append("- 외부 리서치 노트: 저장된 노트 없음.")
    else:
        lines.append("- 외부 리서치 노트(선택 참고자료, 룰 결정을 직접 변경하지 않음):")
        for item in latest_research[:3]:
            lines.append(
                f"  - {item.source_type}/{item.reliability} {item.source_name}: {item.summary[:160]}"
            )
            if item.counter_points:
                lines.append(f"    반대근거: {item.counter_points[:160]}")
            if item.check_questions:
                lines.append(f"    확인질문: {item.check_questions[:160]}")
    if data_status:
        status = data_status[0]
        lines.append(
            "- 데이터 상태: "
            f"{status.freshness_label} "
            f"(가격 {status.latest_price_date or '-'}, 뉴스 {status.latest_news_at or '-'}, "
            f"공시 {status.latest_filing_date or '-'}, 실적 {status.next_earnings_date or '-'})"
        )
    lines.append(f"- {account_route_note(account)}")
    return "\n".join(lines)


def _int(form: dict[str, str], key: str) -> int:
    return int(float(form.get(key, "0") or 0))


def _float(form: dict[str, str], key: str) -> float:
    return float(form.get(key, "0") or 0)


def _optional_float(form: dict[str, str], key: str) -> float | None:
    value = form.get(key, "").strip()
    return float(value) if value else None


def _fetch_latest_price_for_holding(config: AppConfig, ticker: str):
    if not ticker:
        return None
    store = PriceHistoryStore(config.db_path)
    today = datetime.now(tz=KST).date()
    try:
        store.fetch_yfinance_into_cache(ticker, today - timedelta(days=14), today)
    except Exception:
        pass
    return store.latest_bar(ticker)


def _tracked_tickers(config: AppConfig) -> list[str]:
    store = PortfolioStore(config.db_path, config)
    watch = WatchlistStore(config.db_path)
    tickers = {holding.ticker for holding in store.load_holdings()}
    tickers.update(item.ticker for item in watch.list_items())
    return sorted(tickers)


def _split_tickers(value: str) -> list[str]:
    return [part.strip().upper() for part in value.replace(";", ",").split(",") if part.strip()]


def update_prices(config: AppConfig, tickers: list[str]) -> int:
    store = PriceHistoryStore(config.db_path)
    start = datetime.now(tz=KST).date() - timedelta(days=90)
    end = datetime.now(tz=KST).date()
    total = 0
    for ticker in tickers:
        bars = store.fetch_yfinance_into_cache(ticker, start, end)
        total += len(bars)
    _refresh_holding_current_prices(config)
    return total


def _refresh_holding_current_prices(config: AppConfig) -> None:
    portfolio_store = PortfolioStore(config.db_path, config)
    price_store = PriceHistoryStore(config.db_path)
    for holding in portfolio_store.load_holdings():
        latest = price_store.latest_bar(holding.ticker)
        if latest is None:
            continue
        portfolio_store.save_holding(
            Holding(
                ticker=holding.ticker,
                account_key=holding.account_key,
                market=holding.market,
                quantity=holding.quantity,
                avg_price=holding.avg_price,
                current_price=latest.close,
                currency=holding.currency,
                asset_type=holding.asset_type,
                sector_tag=holding.sector_tag,
            )
        )


def _latest_prices(config: AppConfig, holdings, watch_items) -> list[dict[str, object]]:
    tickers = sorted({holding.ticker for holding in holdings} | {item.ticker for item in watch_items})
    store = PriceHistoryStore(config.db_path)
    items = []
    for ticker in tickers:
        latest = store.latest_bar(ticker)
        if latest is not None:
            items.append(
                {
                    "ticker": latest.ticker,
                    "date": latest.date.isoformat(),
                    "close": latest.close,
                    "source": latest.source,
                }
            )
    return items


def _e(value: object) -> str:
    return html.escape(str(value), quote=True)
