from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.config import AppConfig
from app.data.market_calendar import krx_status
from app.engines.buy_check_mode import review_buy_request
from app.models import Action, BuyReviewRequest, PortfolioSnapshot


def test_krx_childrens_day_is_closed_with_next_open():
    status = krx_status(date(2026, 5, 5))

    assert status.is_open is False
    assert status.reason == "Children's Day"
    assert status.next_open_date == date(2026, 5, 6)


def test_kr_ticker_buy_check_blocks_on_market_holiday(tmp_path):
    decision = review_buy_request(
        BuyReviewRequest(
            ticker="005930.KS",
            market="KR",
            desired_amount_krw=1_000_000,
            reason_text="휴장일 테스트",
            fomo_score=5,
            friend_influence_score=1,
        ),
        portfolio=PortfolioSnapshot(cash_krw=20_000_000, holdings=[], total_value_krw=20_000_000),
        events=[],
        recent_trades=[],
        now=datetime(2026, 5, 5, 9, 0, tzinfo=ZoneInfo("Asia/Seoul")),
        config=AppConfig(db_path=tmp_path / "holiday.sqlite3"),
    )

    assert decision.action == Action.NO_TRADE
    assert any("market_calendar" in reason for reason in decision.reason)
    assert "다음 개장일" in decision.next_check
