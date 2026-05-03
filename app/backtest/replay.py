from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app.backtest.context import BacktestTrade, build_context
from app.backtest.report import build_report
from app.config import AppConfig
from app.data.price_history import trading_day_offset
from app.db.database import connect, init_db
from app.engines.buy_check_mode import review_buy_request
from app.models import Action, BuyReviewRequest


KST = ZoneInfo("Asia/Seoul")


def run_backtest(
    db_path: Path | str,
    since: date,
    until: date,
    mode: str = "strict",
    rule_version: str = "current",
    config: AppConfig | None = None,
    report_dir: Path | str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    config = config or AppConfig(db_path=Path(db_path))
    today = today or datetime.now(tz=KST).date()
    init_db(db_path)
    run_id = _create_run(db_path, rule_version, since, until, mode)
    verdicts: list[dict[str, Any]] = []
    for trade in _load_buy_trades(db_path, since, until, config):
        context = build_context(db_path, trade, mode, _config_for_rule_version(config, rule_version))
        if context is None:
            verdict = _emit_verdict(db_path, run_id, trade.trade_id, "skip", [], None, "incomplete")
            verdicts.append(verdict)
            continue

        decision = review_buy_request(
            BuyReviewRequest(
                ticker=trade.ticker,
                desired_amount_krw=trade.amount_krw,
                reason_text=trade.reason,
                fomo_score=trade.fomo,
                friend_influence_score=trade.influence,
            ),
            portfolio=context.portfolio_at_t,
            events=[],
            recent_trades=[],
            now=trade.decision_at,
            config=_config_for_rule_version(config, rule_version),
            price_history=context.rule_price_history,
            earnings_dates=context.earnings_dates,
        )
        triggered_rules = _triggered_rules(decision)
        verdict_name = _decision_to_verdict(decision, trade.amount_krw)
        outcomes = compute_outcomes(context.price_window, trade.decision_at.date(), context.fx_usdkrw_at_t, today)
        verdict = _emit_verdict(
            db_path,
            run_id,
            trade.trade_id,
            verdict_name,
            triggered_rules,
            outcomes,
            context.completeness,
        )
        verdicts.append(verdict)

    report = build_report(run_id, rule_version, since.isoformat(), until.isoformat(), verdicts)
    _finalize_run(db_path, run_id, report["totals"])
    output_dir = Path(report_dir) if report_dir else Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"backtest_report_{datetime.now(tz=KST).strftime('%Y%m%d_%H%M%S')}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["report_path"] = str(report_path)
    return report


def compute_outcomes(
    price_window,
    decision_date: date,
    fx_at_t0: float,
    today: date,
) -> dict[str, float | None]:
    future = [bar for bar in price_window if bar.date > decision_date]
    if not future:
        return {
            "outcome_30d_usd_pct": None,
            "outcome_90d_usd_pct": None,
            "outcome_30d_krw_pct": None,
            "outcome_90d_krw_pct": None,
        }
    entry = future[0]
    needs_30 = trading_day_offset(entry.date, 30)
    needs_90 = trading_day_offset(entry.date, 90)

    def pct_at(required_date: date) -> float | None:
        if today < required_date:
            return None
        candidates = [bar for bar in future if bar.date >= required_date]
        if not candidates:
            return None
        return (candidates[0].close - entry.close) / entry.close

    outcome_30 = pct_at(needs_30)
    outcome_90 = pct_at(needs_90)
    return {
        "outcome_30d_usd_pct": outcome_30,
        "outcome_90d_usd_pct": outcome_90,
        "outcome_30d_krw_pct": outcome_30 if outcome_30 is not None else None,
        "outcome_90d_krw_pct": outcome_90 if outcome_90 is not None else None,
    }


def _load_buy_trades(
    db_path: Path | str, since: date, until: date, config: AppConfig
) -> list[BacktestTrade]:
    with connect(db_path) as conn:
        tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "trade_journal" in tables:
            rows = conn.execute(
                """
                SELECT trade_id, decision_at, ticker, amount_krw, reason, fomo, influence
                FROM trade_journal
                WHERE decision_at BETWEEN ? AND ? AND action_taken = 'buy'
                ORDER BY decision_at ASC
                """,
                (since.isoformat(), (until + timedelta(days=1)).isoformat()),
            ).fetchall()
            return [
                BacktestTrade(
                    trade_id=row["trade_id"],
                    decision_at=datetime.fromisoformat(row["decision_at"]),
                    ticker=row["ticker"].upper(),
                    amount_krw=int(row["amount_krw"]),
                    reason=row["reason"] or "",
                    fomo=int(row["fomo"] or 0),
                    influence=int(row["influence"] or 0),
                )
                for row in rows
            ]
        rows = conn.execute(
            """
            SELECT id, timestamp, ticker, quantity, avg_price, reason_text, fomo_score, friend_influence_score
            FROM trades
            WHERE timestamp BETWEEN ? AND ? AND UPPER(action) = 'BUY'
            ORDER BY timestamp ASC
            """,
            (since.isoformat(), (until + timedelta(days=1)).isoformat()),
        ).fetchall()
    return [
        BacktestTrade(
            trade_id=row["id"],
            decision_at=datetime.fromisoformat(row["timestamp"]),
            ticker=row["ticker"].upper(),
            amount_krw=int(row["quantity"] * row["avg_price"] * config.fx_usd_krw),
            reason=row["reason_text"] or "",
            fomo=int(row["fomo_score"] or 0),
            influence=int(row["friend_influence_score"] or 0),
        )
        for row in rows
    ]


def _create_run(db_path, rule_version: str, since: date, until: date, mode: str) -> int:
    with connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO backtest_run (
              run_at, rule_version, since_date, until_date, mode,
              total_trades, blocked_count, warned_count, passed_count, skipped_count
            )
            VALUES (?, ?, ?, ?, ?, 0, 0, 0, 0, 0)
            """,
            (datetime.now(tz=KST).isoformat(), rule_version, since.isoformat(), until.isoformat(), mode),
        )
        return int(cursor.lastrowid)


def _finalize_run(db_path, run_id: int, totals: dict[str, int]) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            UPDATE backtest_run
            SET total_trades = ?, blocked_count = ?, warned_count = ?, passed_count = ?, skipped_count = ?
            WHERE run_id = ?
            """,
            (
                totals["trades"],
                totals["blocked"],
                totals["warned"],
                totals["passed"],
                totals["skipped"],
                run_id,
            ),
        )


def _emit_verdict(
    db_path,
    run_id: int,
    trade_id: int,
    verdict: str,
    triggered_rules: list[str],
    outcomes: dict[str, float | None] | None,
    completeness: str,
) -> dict[str, Any]:
    outcome = outcomes or {
        "outcome_30d_usd_pct": None,
        "outcome_90d_usd_pct": None,
        "outcome_30d_krw_pct": None,
        "outcome_90d_krw_pct": None,
    }
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO backtest_verdict (
              run_id, trade_id, verdict, triggered_rules_json,
              outcome_30d_usd_pct, outcome_90d_usd_pct, outcome_30d_krw_pct, outcome_90d_krw_pct,
              context_completeness
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                trade_id,
                verdict,
                json.dumps(triggered_rules, ensure_ascii=False),
                outcome["outcome_30d_usd_pct"],
                outcome["outcome_90d_usd_pct"],
                outcome["outcome_30d_krw_pct"],
                outcome["outcome_90d_krw_pct"],
                completeness,
            ),
        )
    return {
        "trade_id": trade_id,
        "verdict": verdict,
        "triggered_rules": triggered_rules,
        **outcome,
        "context_completeness": completeness,
    }


def _triggered_rules(decision) -> list[str]:
    rules: list[str] = []
    if decision.post_drop_context and decision.post_drop_context.triggered:
        rules.append("post_drop_chase")
    for reason in decision.reason:
        if "실적" in reason:
            rules.append("earnings_d7")
        if "FOMO" in reason:
            rules.append("fomo")
        if "비중" in reason:
            rules.append("concentration")
        if "현금" in reason:
            rules.append("cash_floor")
        if "손실" in reason:
            rules.append("loss_position_add")
    return sorted(set(rules))


def _decision_to_verdict(decision, requested_amount_krw: int) -> str:
    if decision.action == Action.NO_TRADE:
        return "block"
    if decision.max_amount_krw < requested_amount_krw:
        return "warn"
    return "pass"


def _config_for_rule_version(config: AppConfig, rule_version: str) -> AppConfig:
    if rule_version in {"legacy_no_post_drop", "post_drop_off"}:
        return AppConfig(**{**config.__dict__, "post_drop_rule_enabled": False})
    return config

