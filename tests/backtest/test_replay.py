from __future__ import annotations

from datetime import date, datetime, timedelta

from app.config import AppConfig
from app.backtest.context import BacktestTrade, build_context
from app.backtest.replay import run_backtest
from app.data.price_history import PriceHistoryStore
from app.db.database import connect, init_db
from app.models import PriceHistoryBar


DECISION_AT = datetime(2026, 1, 15, 9, 0)


def setup_trade_journal(db_path, ticker="META", fomo=5) -> None:
    init_db(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trade_journal (
              trade_id INTEGER PRIMARY KEY,
              decision_at TEXT NOT NULL,
              ticker TEXT NOT NULL,
              amount_krw INTEGER NOT NULL,
              reason TEXT,
              fomo INTEGER,
              influence INTEGER,
              action_taken TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO trade_journal
            (trade_id, decision_at, ticker, amount_krw, reason, fomo, influence, action_taken)
            VALUES (1, ?, ?, 1000000, 'backtest trade', ?, 0, 'buy')
            """,
            (DECISION_AT.isoformat(), ticker, fomo),
        )


def setup_snapshot(db_path, ticker="META") -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO holdings_snapshot (taken_at, trade_id, ticker, shares, avg_cost_usd, fx_usdkrw)
            VALUES (?, 1, ?, 10, 100, 1350)
            """,
            ((DECISION_AT - timedelta(days=1)).isoformat(), ticker),
        )


def setup_earnings(db_path, ticker="META", earnings_date=date(2026, 1, 1)) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO earnings_calendar_history (ticker, earnings_date, source, recorded_at)
            VALUES (?, ?, 'manual', ?)
            """,
            (ticker, earnings_date.isoformat(), DECISION_AT.isoformat()),
        )


def setup_prices(db_path, ticker="META", drop=False, days=140) -> list[PriceHistoryBar]:
    store = PriceHistoryStore(db_path)
    start = DECISION_AT.date() - timedelta(days=20)
    bars: list[PriceHistoryBar] = []
    close = 100.0
    for idx in range(days):
        current = start + timedelta(days=idx)
        if current.weekday() >= 5:
            continue
        if drop and current == DECISION_AT.date() - timedelta(days=2):
            close = 90.0
        else:
            close += 0.1
        bars.append(PriceHistoryBar(ticker=ticker, date=current, close=round(close, 2)))
    store.upsert_many(bars)
    return bars


def test_strict_mode_full_snapshot(tmp_path):
    db_path = tmp_path / "bt.sqlite3"
    setup_trade_journal(db_path)
    setup_snapshot(db_path)
    setup_earnings(db_path)
    setup_prices(db_path)
    report = run_backtest(db_path, date(2026, 1, 1), date(2026, 1, 31), mode="strict", report_dir=tmp_path)
    assert report["totals"]["trades"] == 1
    assert report["totals"]["skipped"] == 0


def test_strict_mode_missing_snapshot_skips(tmp_path):
    db_path = tmp_path / "bt.sqlite3"
    setup_trade_journal(db_path)
    setup_earnings(db_path)
    setup_prices(db_path)
    report = run_backtest(db_path, date(2026, 1, 1), date(2026, 1, 31), mode="strict", report_dir=tmp_path)
    assert report["totals"]["skipped"] == 1


def test_reconstruct_mode_missing_snapshot_uses_empty_portfolio(tmp_path):
    db_path = tmp_path / "bt.sqlite3"
    setup_trade_journal(db_path)
    setup_prices(db_path)
    report = run_backtest(
        db_path,
        date(2026, 1, 1),
        date(2026, 1, 31),
        mode="reconstruct",
        report_dir=tmp_path,
    )
    assert report["totals"]["trades"] == 1
    assert report["verdicts"][0]["context_completeness"] == "reconstructed"


def test_delisted_ticker_reconstruct_failure_skips(tmp_path, monkeypatch):
    db_path = tmp_path / "bt.sqlite3"
    setup_trade_journal(db_path, ticker="DELISTED")

    def fail_fetch(self, ticker, start, end):
        raise RuntimeError("missing")

    monkeypatch.setattr(PriceHistoryStore, "fetch_yfinance_into_cache", fail_fetch)
    report = run_backtest(
        db_path,
        date(2026, 1, 1),
        date(2026, 1, 31),
        mode="reconstruct",
        report_dir=tmp_path,
    )
    assert report["totals"]["skipped"] == 1


def test_future_window_truncated_outputs_null_outcomes(tmp_path):
    db_path = tmp_path / "bt.sqlite3"
    setup_trade_journal(db_path)
    setup_snapshot(db_path)
    setup_earnings(db_path)
    setup_prices(db_path, days=30)
    report = run_backtest(
        db_path,
        date(2026, 1, 1),
        date(2026, 1, 31),
        mode="strict",
        report_dir=tmp_path,
        today=DECISION_AT.date() + timedelta(days=10),
    )
    verdict = report["verdicts"][0]
    assert verdict["outcome_30d_usd_pct"] is None
    assert verdict["outcome_90d_usd_pct"] is None


def test_rule_version_diff(tmp_path):
    db_path = tmp_path / "bt.sqlite3"
    setup_trade_journal(db_path, fomo=5)
    setup_snapshot(db_path)
    setup_earnings(db_path, earnings_date=DECISION_AT.date() - timedelta(days=2))
    setup_prices(db_path, drop=True)
    current = run_backtest(
        db_path,
        date(2026, 1, 1),
        date(2026, 1, 31),
        mode="strict",
        rule_version="current",
        report_dir=tmp_path,
    )
    legacy = run_backtest(
        db_path,
        date(2026, 1, 1),
        date(2026, 1, 31),
        mode="strict",
        rule_version="legacy_no_post_drop",
        report_dir=tmp_path,
    )
    assert current["verdicts"][0]["verdict"] != legacy["verdicts"][0]["verdict"]


def test_lookahead_bias_guard(tmp_path):
    db_path = tmp_path / "bt.sqlite3"
    setup_trade_journal(db_path)
    setup_snapshot(db_path)
    setup_earnings(db_path)
    setup_prices(db_path, drop=True)
    trade = BacktestTrade(
        trade_id=1,
        decision_at=DECISION_AT,
        ticker="META",
        amount_krw=1_000_000,
        reason="guard",
        fomo=5,
        influence=0,
    )
    context = build_context(db_path, trade, mode="strict", config=AppConfig())
    assert context is not None
    assert max(bar.date for bar in context.rule_price_history) <= DECISION_AT.date()
    assert any(bar.date > DECISION_AT.date() for bar in context.price_window)
