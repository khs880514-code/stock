from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from app.alerts.message_templates import compact_message, format_decision_message
from app.backtest.replay import run_backtest
from app.briefing.morning_briefing import build_morning_briefing
from app.briefing.premarket_briefing import build_premarket_briefing
from app.config import LEGAL_DISCLAIMER, AppConfig, load_config
from app.data.buy_check_log import BuyCheckLogStore
from app.data.conditional_orders import ConditionalDecisionStore
from app.data.earnings_calendar_store import EarningsCalendarStore
from app.data.macro_collector import MockMacroCollector
from app.data.mock_event_calendar import MockEventCalendar
from app.data.mock_price_provider import MockPriceProvider
from app.data.pipeline import run_mock_collection
from app.data.price_history import PriceHistoryStore
from app.data.portfolio_store import PortfolioStore, seed_demo_portfolio
from app.data.ticker_sensitivity import TickerSensitivityStore
from app.data.watchlist_store import WatchlistStore
from app.db.database import init_db
from app.engines.buy_check_mode import review_buy_request
from app.engines.core_etf_rules import evaluate_core_etf
from app.engines.macro_event_explainer import detect_macro_triggers, explain_macro_event
from app.journal.monthly_report import build_monthly_report
from app.journal.trade_journal import TradeJournal
from app.models import BuyReviewRequest, ConditionalDecision, Holding, MistakeType, TickerSensitivitySnapshot, TradeEntry
from app.web_ui import run_web_ui


KST = ZoneInfo("Asia/Seoul")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="stock-expert-friend")
    parser.add_argument("--demo", action="store_true", help="Run mock data demo.")
    parser.add_argument("--init-db", action="store_true", help="Initialize SQLite schema.")
    parser.add_argument("--db-path", default=None, help="SQLite DB path.")
    parser.add_argument("--buy-check", action="store_true", help="Run a buy-review check from CLI args.")
    parser.add_argument("--backtest", action="store_true", help="Replay historical buy trades.")
    parser.add_argument("--since", default=None, help="Backtest start date YYYY-MM-DD.")
    parser.add_argument("--until", default=None, help="Backtest end date YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--mode", choices=["strict", "reconstruct"], default="strict")
    parser.add_argument("--rule-version", default="current")
    parser.add_argument("--ticker", default="AMD")
    parser.add_argument("--amount-krw", type=int, default=1_000_000)
    parser.add_argument("--reason", default="실적 전 변동성이 커서 검토")
    parser.add_argument("--fomo", type=int, default=5)
    parser.add_argument("--influence", type=int, default=1)
    parser.add_argument("--price-type", default="limit")
    parser.add_argument("--set-cash", type=int, default=None, help="Set current cash in KRW.")
    parser.add_argument("--add-holding", action="store_true", help="Add or update one holding.")
    parser.add_argument("--remove-holding", action="store_true", help="Remove one holding by --ticker.")
    parser.add_argument("--list-portfolio", action="store_true", help="Show cash, holdings, and risk tags.")
    parser.add_argument("--snapshot-holdings", action="store_true", help="Persist current holdings snapshot.")
    parser.add_argument("--market", default="US", choices=["US", "KR"])
    parser.add_argument("--quantity", type=float, default=0.0)
    parser.add_argument("--avg-price", type=float, default=0.0)
    parser.add_argument("--current-price", type=float, default=0.0)
    parser.add_argument("--currency", default="USD", choices=["USD", "KRW"])
    parser.add_argument("--asset-type", default="EQUITY")
    parser.add_argument("--sector-tag", default="UNKNOWN")
    parser.add_argument("--record-trade", action="store_true", help="Record one manual journal entry.")
    parser.add_argument("--list-trades", action="store_true", help="List recent journal entries.")
    parser.add_argument("--trade-action", default="BUY")
    parser.add_argument("--timestamp", default=None, help="ISO timestamp. Defaults to now.")
    parser.add_argument("--price-1d", type=float, default=None)
    parser.add_argument("--price-1w", type=float, default=None)
    parser.add_argument("--price-1m", type=float, default=None)
    parser.add_argument("--outcome-note", default="")
    parser.add_argument("--mistake-type", default="NONE")
    parser.add_argument("--watch-add", action="store_true", help="Add or update one watchlist item.")
    parser.add_argument("--watch-remove", action="store_true", help="Remove one watchlist item by --ticker.")
    parser.add_argument("--watch-list", action="store_true", help="List watchlist items.")
    parser.add_argument("--priority", type=int, default=3)
    parser.add_argument("--sensitivity-set", action="store_true", help="Add or update ticker sensitivity.")
    parser.add_argument("--sensitivity-list", action="store_true", help="List ticker sensitivity snapshots.")
    parser.add_argument("--seed-kr-semiconductor-sensitivity", action="store_true", help="Seed Samsung Electronics and SK Hynix sensitivity defaults.")
    parser.add_argument("--foreign-pct", type=float, default=None)
    parser.add_argument("--sector-corr", type=float, default=None)
    parser.add_argument("--market-corr", type=float, default=None)
    parser.add_argument("--fx-corr", type=float, default=None)
    parser.add_argument("--beta-kospi", type=float, default=None)
    parser.add_argument("--proxy", default=None)
    parser.add_argument("--blackout-set", action="store_true", help="Set watch blackout for a ticker.")
    parser.add_argument("--blackout-clear", action="store_true", help="Clear watch blackout for a ticker.")
    parser.add_argument("--until-date", default=None, help="YYYY-MM-DD date for blackout or conditional expiry.")
    parser.add_argument("--conditional-add", action="store_true", help="Record a conditional decision.")
    parser.add_argument("--conditional-list", action="store_true", help="List active conditional decisions.")
    parser.add_argument("--condition", default="")
    parser.add_argument("--planned-action", default="WATCH")
    parser.add_argument("--web", action="store_true", help="Start local web UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    config = load_config()
    if args.db_path:
        config = AppConfig(**{**config.__dict__, "db_path": Path(args.db_path)})

    if args.init_db:
        init_db(config.db_path)
        print(f"Initialized DB: {config.db_path}")
        return

    if args.web:
        run_web_ui(config, host=args.host, port=args.port)
        return

    if args.set_cash is not None:
        print(run_set_cash(config, args.set_cash))
        return

    if args.add_holding:
        print(run_add_holding(config, args))
        return

    if args.remove_holding:
        print(run_remove_holding(config, args.ticker))
        return

    if args.list_portfolio:
        print(run_list_portfolio(config))
        return

    if args.snapshot_holdings:
        print(run_snapshot_holdings(config))
        return

    if args.record_trade:
        print(run_record_trade(config, args))
        return

    if args.list_trades:
        print(run_list_trades(config))
        return

    if args.watch_add:
        print(run_watch_add(config, args))
        return

    if args.watch_remove:
        print(run_watch_remove(config, args.ticker))
        return

    if args.watch_list:
        print(run_watch_list(config))
        return

    if args.sensitivity_set:
        print(run_sensitivity_set(config, args))
        return

    if args.sensitivity_list:
        print(run_sensitivity_list(config))
        return

    if args.seed_kr_semiconductor_sensitivity:
        print(run_seed_kr_semiconductor_sensitivity(config))
        return

    if args.blackout_set:
        print(run_blackout_set(config, args))
        return

    if args.blackout_clear:
        print(run_blackout_clear(config, args.ticker))
        return

    if args.conditional_add:
        print(run_conditional_add(config, args))
        return

    if args.conditional_list:
        print(run_conditional_list(config, args.ticker))
        return

    if args.demo:
        print(run_demo(config))
        return

    if args.buy_check:
        print(run_buy_check(config, args))
        return

    if args.backtest:
        if not args.since:
            raise SystemExit("--backtest requires --since YYYY-MM-DD")
        until = date.fromisoformat(args.until) if args.until else datetime.now(tz=KST).date()
        report = run_backtest(
            db_path=config.db_path,
            since=date.fromisoformat(args.since),
            until=until,
            mode=args.mode,
            rule_version=args.rule_version,
            config=config,
            report_dir=Path.cwd(),
        )
        print(_format_backtest_summary(report))
        return

    parser.print_help()


def run_demo(config: AppConfig) -> str:
    demo_config = AppConfig(**{**config.__dict__, "db_path": Path("demo_stock_expert_friend.sqlite3")})
    init_db(demo_config.db_path)
    collected = run_mock_collection(demo_config.db_path)
    store = PortfolioStore(demo_config.db_path, demo_config)
    portfolio = seed_demo_portfolio(store)
    journal = TradeJournal(demo_config.db_path)
    now = datetime.now(tz=KST)
    _ensure_demo_trade(journal, now)

    prices = MockPriceProvider()
    macro = MockMacroCollector().collect()
    events = MockEventCalendar().upcoming_events([holding.ticker for holding in portfolio.holdings], now)

    morning = build_morning_briefing(portfolio, prices, macro)
    premarket = build_premarket_briefing(portfolio, MockEventCalendar(), journal, macro, now)
    qqq_decision = evaluate_core_etf("QQQ", prices.get_current_price("QQQ"), macro)
    smh_decision = evaluate_core_etf("SMH", prices.get_current_price("SMH"), macro)
    buy_decision = review_buy_request(
        BuyReviewRequest(
            ticker="AMD",
            desired_amount_krw=1_200_000,
            reason_text="실적 전에 많이 빠져서 반등을 기대하고 싶음",
            fomo_score=8,
            friend_influence_score=2,
            price_type="limit",
        ),
        portfolio=portfolio,
        events=events,
        recent_trades=journal.recent_trades(now - timedelta(days=14)),
        now=now,
        config=demo_config,
    )
    macro_messages = [
        explain_macro_event(trigger, portfolio)
        for trigger in detect_macro_triggers(macro, demo_config)
    ]
    monthly = build_monthly_report(journal.recent_trades(now - timedelta(days=35)), now)

    journal.log_alert("morning_briefing", morning)
    journal.log_alert("premarket_briefing", premarket)
    journal.log_alert("buy_check", format_decision_message("AMD 매수 검토", buy_decision), buy_decision)

    sections = [
        LEGAL_DISCLAIMER,
        "",
        f"Mock collection: {', '.join(collected)}",
        "",
        morning,
        "",
        premarket,
        "",
        compact_message(format_decision_message("QQQ 코어 ETF 룰", qqq_decision)),
        "",
        compact_message(format_decision_message("SMH 코어 ETF 룰", smh_decision)),
        "",
        compact_message(format_decision_message("AMD 매수 검토", buy_decision)),
        "",
        "\n\n".join(macro_messages[:2]),
        "",
        monthly,
    ]
    return "\n".join(section for section in sections if section != "")


def run_buy_check(config: AppConfig, args: argparse.Namespace) -> str:
    init_db(config.db_path)
    store = PortfolioStore(config.db_path, config)
    portfolio = store.snapshot()
    if portfolio.total_value_krw == 0 and config.db_path.name.startswith("demo"):
        portfolio = seed_demo_portfolio(store)
    journal = TradeJournal(config.db_path)
    now = datetime.now(tz=KST)
    events = EarningsCalendarStore(config.db_path).upcoming_events([args.ticker], now)
    price_store = PriceHistoryStore(config.db_path)
    price_history = price_store.get_window(args.ticker, now.date() - timedelta(days=180), now.date())
    latest_price = price_store.latest_bar(args.ticker)
    decision = review_buy_request(
        BuyReviewRequest(
            ticker=args.ticker,
            desired_amount_krw=args.amount_krw,
            reason_text=args.reason,
            fomo_score=args.fomo,
            friend_influence_score=args.influence,
            price_type=args.price_type,
        ),
        portfolio=portfolio,
        events=events,
        recent_trades=journal.recent_trades(now - timedelta(days=14)),
        now=now,
        config=config,
        price_history=price_history,
    )
    message = format_decision_message(f"{args.ticker.upper()} 매수 검토", decision)
    journal.log_alert("buy_check", message, decision)
    BuyCheckLogStore(config.db_path).add(
        decision_at=now,
        request=BuyReviewRequest(
            ticker=args.ticker,
            desired_amount_krw=args.amount_krw,
            reason_text=args.reason,
            fomo_score=args.fomo,
            friend_influence_score=args.influence,
            price_type=args.price_type,
        ),
        decision=decision,
        price_at_decision=latest_price.close if latest_price else None,
    )
    return LEGAL_DISCLAIMER + "\n\n" + message


def run_set_cash(config: AppConfig, cash_krw: int) -> str:
    store = PortfolioStore(config.db_path, config)
    store.set_cash(cash_krw)
    return f"현금 입력 완료: {cash_krw:,}원"


def run_add_holding(config: AppConfig, args: argparse.Namespace) -> str:
    _require_positive(args.quantity, "--quantity")
    _require_positive(args.avg_price, "--avg-price")
    current_price = args.current_price if args.current_price > 0 else args.avg_price
    store = PortfolioStore(config.db_path, config)
    store.save_holding(
        Holding(
            ticker=args.ticker,
            market=args.market,
            quantity=args.quantity,
            avg_price=args.avg_price,
            current_price=current_price,
            currency=args.currency,
            asset_type=args.asset_type.upper(),
            sector_tag=args.sector_tag.upper(),
        )
    )
    return f"보유종목 저장 완료: {args.ticker.upper()} {args.quantity:g}주"


def run_remove_holding(config: AppConfig, ticker: str) -> str:
    removed = PortfolioStore(config.db_path, config).delete_holding(ticker)
    return f"보유종목 삭제 완료: {ticker.upper()}" if removed else f"보유종목 없음: {ticker.upper()}"


def run_list_portfolio(config: AppConfig) -> str:
    snapshot = PortfolioStore(config.db_path, config).snapshot()
    lines = [
        "포트폴리오",
        f"- 현금: {snapshot.cash_krw:,}원",
        f"- 총 평가액: {snapshot.total_value_krw:,}원",
        f"- 리스크 태그: {', '.join(snapshot.risk_tags) if snapshot.risk_tags else '없음'}",
        "보유종목:",
    ]
    if not snapshot.holdings:
        lines.append("- 없음")
    for holding in snapshot.holdings:
        lines.append(
            f"- {holding.ticker} {holding.quantity:g}주 "
            f"평단 {holding.avg_price:g}{holding.currency}, 현재 {holding.current_price:g}{holding.currency}, "
            f"{holding.sector_tag}"
        )
    return "\n".join(lines)


def run_snapshot_holdings(config: AppConfig) -> str:
    count = PortfolioStore(config.db_path, config).save_snapshot()
    return f"보유종목 스냅샷 저장 완료: {count}개 종목"


def run_record_trade(config: AppConfig, args: argparse.Namespace) -> str:
    _require_positive(args.quantity, "--quantity")
    _require_positive(args.avg_price, "--avg-price")
    timestamp = datetime.fromisoformat(args.timestamp) if args.timestamp else datetime.now(tz=KST)
    price_at_entry = args.current_price if args.current_price > 0 else args.avg_price
    journal = TradeJournal(config.db_path)
    trade_id = journal.add_trade(
        TradeEntry(
            timestamp=timestamp,
            ticker=args.ticker,
            action=args.trade_action.upper(),
            quantity=args.quantity,
            avg_price=args.avg_price,
            reason_text=args.reason,
            fomo_score=args.fomo,
            friend_influence_score=args.influence,
            price_at_entry=price_at_entry,
            price_1d=args.price_1d,
            price_1w=args.price_1w,
            price_1m=args.price_1m,
            outcome_note=args.outcome_note,
            mistake_type=MistakeType(args.mistake_type.upper()),
        )
    )
    return f"매매 일지 저장 완료: id={trade_id}, {args.ticker.upper()} {args.trade_action.upper()}"


def run_list_trades(config: AppConfig) -> str:
    trades = TradeJournal(config.db_path).recent_trades()
    lines = ["최근 매매 일지:"]
    if not trades:
        lines.append("- 없음")
    for trade in trades[:20]:
        lines.append(
            f"- #{trade.id or '-'} {trade.timestamp.isoformat()} {trade.ticker} "
            f"{trade.action.upper()} {trade.quantity:g}주 @ {trade.avg_price:g}, "
            f"FOMO {trade.fomo_score}/10, 사유: {trade.reason_text}"
        )
    return "\n".join(lines)


def run_watch_add(config: AppConfig, args: argparse.Namespace) -> str:
    WatchlistStore(config.db_path).add_or_update(
        ticker=args.ticker,
        market=args.market,
        reason=args.reason,
        priority=args.priority,
        sector_tag=args.sector_tag,
    )
    return f"관심종목 저장 완료: {args.ticker.upper()}"


def run_watch_remove(config: AppConfig, ticker: str) -> str:
    removed = WatchlistStore(config.db_path).remove(ticker)
    return f"관심종목 삭제 완료: {ticker.upper()}" if removed else f"관심종목 없음: {ticker.upper()}"


def run_watch_list(config: AppConfig) -> str:
    items = WatchlistStore(config.db_path).list_items()
    lines = ["관심종목:"]
    if not items:
        lines.append("- 없음")
    for item in items:
        lines.append(
            f"- P{item.priority} {item.ticker} ({item.market}, {item.sector_tag}): {item.reason}"
        )
    return "\n".join(lines)


def run_sensitivity_set(config: AppConfig, args: argparse.Namespace) -> str:
    store = TickerSensitivityStore(config.db_path)
    existing = store.get(args.ticker)
    snapshot = TickerSensitivitySnapshot(
        ticker=args.ticker,
        market=args.market,
        sector_tag=args.sector_tag,
        us_sector_proxy_symbol=args.proxy,
        foreign_ownership_pct=args.foreign_pct,
        foreign_ownership_taken_at=datetime.now(tz=KST).date() if args.foreign_pct is not None else None,
        us_sector_corr_60d=args.sector_corr,
        us_market_corr_60d=args.market_corr,
        fx_corr_60d=args.fx_corr,
        beta_to_kospi_60d=args.beta_kospi,
        corr_taken_at=(
            datetime.now(tz=KST).date()
            if any(value is not None for value in [args.sector_corr, args.market_corr, args.fx_corr, args.beta_kospi])
            else None
        ),
        manual_override=True,
    )
    if existing:
        snapshot = existing.model_copy(
            update={key: value for key, value in snapshot.model_dump().items() if value is not None}
        )
    store.upsert(snapshot)
    return f"종목 민감도 저장 완료: {snapshot.ticker}"


def run_sensitivity_list(config: AppConfig) -> str:
    items = TickerSensitivityStore(config.db_path).list_all()
    lines = ["종목 민감도"]
    if not items:
        lines.append("- 없음")
    for item in items:
        lines.append(
            f"- {item.ticker} {item.sector_tag} proxy={item.us_sector_proxy_symbol or '-'} "
            f"foreign={item.foreign_ownership_pct if item.foreign_ownership_pct is not None else '-'}% "
            f"sector_corr={item.us_sector_corr_60d if item.us_sector_corr_60d is not None else '-'}"
        )
    return "\n".join(lines)


def run_seed_kr_semiconductor_sensitivity(config: AppConfig) -> str:
    count = TickerSensitivityStore(config.db_path).seed_kr_semiconductor_estimates()
    return f"국내 반도체 추정 민감도 저장 완료: {count}개 (005930.KS, 000660.KS, 관측일 없음)"


def run_blackout_set(config: AppConfig, args: argparse.Namespace) -> str:
    until = date.fromisoformat(args.until_date) if args.until_date else datetime.now(tz=KST).date() + timedelta(days=1)
    reason = args.reason or "manual decision protection blackout"
    WatchlistStore(config.db_path).set_blackout(args.ticker, until, reason)
    return f"관찰 블랙아웃 설정 완료: {args.ticker.upper()} until={until.isoformat()}"


def run_blackout_clear(config: AppConfig, ticker: str) -> str:
    ok = WatchlistStore(config.db_path).clear_blackout(ticker)
    return f"관찰 블랙아웃 해제 완료: {ticker.upper()}" if ok else f"관찰 블랙아웃 대상 없음: {ticker.upper()}"


def run_conditional_add(config: AppConfig, args: argparse.Namespace) -> str:
    if not args.condition:
        raise SystemExit("--conditional-add requires --condition")
    expires_at = (
        datetime.combine(date.fromisoformat(args.until_date), datetime.max.time(), tzinfo=KST)
        if args.until_date
        else None
    )
    decision_id = ConditionalDecisionStore(config.db_path).add(
        ConditionalDecision(
            created_at=datetime.now(tz=KST),
            ticker=args.ticker,
            condition_text=args.condition,
            planned_action=args.planned_action.upper(),
            expires_at=expires_at,
            note=args.reason,
        )
    )
    return f"조건부 결정 저장 완료: #{decision_id} {args.ticker.upper()}"


def run_conditional_list(config: AppConfig, ticker: str | None = None) -> str:
    items = ConditionalDecisionStore(config.db_path).list_active(ticker=ticker, now=datetime.now(tz=KST))
    lines = ["조건부 결정"]
    if not items:
        lines.append("- 없음")
    for item in items:
        expires = item.expires_at.date().isoformat() if item.expires_at else "-"
        lines.append(f"- #{item.id or '-'} {item.ticker} {item.planned_action}: {item.condition_text} (expires={expires})")
    return "\n".join(lines)


def _format_backtest_summary(report: dict) -> str:
    totals = report["totals"]
    return "\n".join(
        [
            f"Backtest run_id={report['run_id']} rule_version={report['rule_version']}",
            f"Period: {report['period']}",
            (
                "Totals: "
                f"trades={totals['trades']}, blocked={totals['blocked']}, "
                f"warned={totals['warned']}, passed={totals['passed']}, skipped={totals['skipped']}"
            ),
            f"Report: {report['report_path']}",
        ]
    )


def _ensure_demo_trade(journal: TradeJournal, now: datetime) -> None:
    existing = journal.one_week_reviews(now)
    if existing:
        return
    journal.add_trade(
        TradeEntry(
            timestamp=now - timedelta(days=7, hours=1),
            ticker="AMD",
            action="BUY",
            quantity=5,
            avg_price=170.0,
            reason_text="AI 매출 기대와 조정 후 반등 가능성 확인",
            fomo_score=7,
            friend_influence_score=2,
            price_at_entry=170.0,
            price_1w=164.0,
            outcome_note="1주일 후 가격 하락. 실적 전 진입 여부 재검토 필요.",
            mistake_type=MistakeType.EARNINGS_CHASE,
        )
    )


def _require_positive(value: float, label: str) -> None:
    if value <= 0:
        raise SystemExit(f"{label} must be greater than 0")


if __name__ == "__main__":
    main()
