from __future__ import annotations

import argparse

from app.config import AppConfig
from app.main import (
    run_add_holding,
    run_list_portfolio,
    run_list_trades,
    run_record_trade,
    run_set_cash,
    run_snapshot_holdings,
    run_watch_add,
    run_watch_list,
)


def args(**kwargs):
    defaults = {
        "ticker": "AAPL",
        "market": "US",
        "account_key": "ISA_KIWOOM",
        "quantity": 2.0,
        "avg_price": 150.0,
        "current_price": 180.0,
        "currency": "USD",
        "asset_type": "EQUITY",
        "sector_tag": "BIG_TECH",
        "trade_action": "BUY",
        "timestamp": None,
        "reason": "운영 입력 테스트",
        "fomo": 3,
        "influence": 1,
        "price_1d": None,
        "price_1w": None,
        "price_1m": None,
        "outcome_note": "",
        "mistake_type": "NONE",
        "priority": 2,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_cash_holding_snapshot_flow(tmp_path):
    config = AppConfig(db_path=tmp_path / "ops.sqlite3")
    assert "완료" in run_set_cash(config, 12_000_000)
    assert "완료" in run_add_holding(config, args())
    listing = run_list_portfolio(config)
    assert "AAPL" in listing
    assert "ISA_KIWOOM" in listing
    assert "12,000,000원" in listing
    assert "1개 종목" in run_snapshot_holdings(config)


def test_record_trade_and_list(tmp_path):
    config = AppConfig(db_path=tmp_path / "ops.sqlite3")
    result = run_record_trade(config, args())
    assert "매매 일지 저장 완료" in result
    listing = run_list_trades(config)
    assert "AAPL" in listing
    assert "ISA_KIWOOM" in listing
    assert "운영 입력 테스트" in listing


def test_watchlist_add_and_list(tmp_path):
    config = AppConfig(db_path=tmp_path / "ops.sqlite3")
    assert "관심종목 저장 완료" in run_watch_add(config, args(ticker="AMD", reason="실적 후 확인"))
    listing = run_watch_list(config)
    assert "AMD" in listing
    assert "실적 후 확인" in listing
