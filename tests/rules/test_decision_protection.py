from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import AppConfig
from app.data.buy_check_log import BuyCheckLogStore
from app.data.price_history import PriceHistoryStore
from app.data.watchlist_store import WatchlistStore
from app.models import Action, AlertDecision, BuyReviewRequest, PriceHistoryBar
from app.rules.decision_protection import active_blackout, detect_regret_chase, suggest_blackout


KST = ZoneInfo("Asia/Seoul")


def test_active_blackout_is_read_from_watchlist(tmp_path):
    config = AppConfig(db_path=tmp_path / "blackout.sqlite3")
    WatchlistStore(config.db_path).set_blackout("005930.KS", date(2026, 5, 5), "후회 추격 방지")

    item = WatchlistStore(config.db_path).get("005930.KS")
    blackout = active_blackout(item, date(2026, 5, 4))

    assert blackout is not None
    assert blackout.active is True
    assert blackout.reason == "후회 추격 방지"


def test_regret_chase_detects_post_no_trade_jump(tmp_path):
    config = AppConfig(db_path=tmp_path / "regret.sqlite3")
    now = datetime(2026, 5, 4, 9, 0, tzinfo=KST)
    request = BuyReviewRequest(
        ticker="005930.KS",
        desired_amount_krw=1_000_000,
        reason_text="검토",
        fomo_score=5,
        friend_influence_score=1,
    )
    decision = AlertDecision(ticker="005930.KS", action=Action.NO_TRADE, reason=["FOMO 점검"])
    BuyCheckLogStore(config.db_path).add(
        decision_at=now - timedelta(days=2),
        request=request,
        decision=decision,
        price_at_decision=100,
    )
    PriceHistoryStore(config.db_path).upsert_many(
        [PriceHistoryBar(ticker="005930.KS", date=now.date(), close=110, source="manual")]
    )

    pattern = detect_regret_chase(
        ticker="005930.KS",
        now=now,
        db_path=config.db_path,
        config=config,
    )

    assert pattern.triggered is True
    assert pattern.gain_since_decision_pct == 0.10


def test_blackout_suggestion_follows_fomo_no_trade():
    now = datetime(2026, 5, 4, 9, 0, tzinfo=KST)
    decision = AlertDecision(ticker="005930.KS", action=Action.NO_TRADE, reason=["FOMO 점수 8/10"])

    suggested = suggest_blackout(decision, now, AppConfig())

    assert suggested is not None
    assert suggested.do_not_watch_until == date(2026, 5, 5)
