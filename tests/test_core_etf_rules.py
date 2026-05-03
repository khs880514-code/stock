from datetime import datetime
from zoneinfo import ZoneInfo

from app.engines.core_etf_rules import evaluate_core_etf
from app.models import Action, MacroIndicator, MacroSnapshot, PriceSnapshot


def test_qqq_down_three_with_normal_vix_is_small_candidate():
    now = datetime(2026, 5, 3, tzinfo=ZoneInfo("Asia/Seoul"))
    price = PriceSnapshot(
        ticker="QQQ",
        current_price=660,
        previous_close=681,
        change_pct=-3.1,
        volume=1,
        volume_avg_30d=1,
        volume_ratio=1,
        timestamp=now,
    )
    macro = MacroSnapshot(timestamp=now, indicators={"VIX": MacroIndicator(name="VIX", value=18)})
    decision = evaluate_core_etf("QQQ", price, macro)
    assert decision.action == Action.SMALL_BUY_CANDIDATE


def test_smh_down_five_with_oil_jump_is_no_trade():
    now = datetime(2026, 5, 3, tzinfo=ZoneInfo("Asia/Seoul"))
    price = PriceSnapshot(
        ticker="SMH",
        current_price=247,
        previous_close=260,
        change_pct=-5.0,
        volume=1,
        volume_avg_30d=1,
        volume_ratio=1,
        timestamp=now,
    )
    macro = MacroSnapshot(
        timestamp=now,
        indicators={"WTI": MacroIndicator(name="WTI", value=83, change_pct=5.1)},
    )
    decision = evaluate_core_etf("SMH", price, macro)
    assert decision.action == Action.NO_TRADE

