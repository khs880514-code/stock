from datetime import timedelta

from app.engines.buy_check_mode import review_buy_request
from app.models import Action, BuyReviewRequest, Event, Holding, PortfolioSnapshot, TradeEntry


def test_high_fomo_blocks_or_slows_new_buy(config, portfolio, now):
    decision = review_buy_request(
        BuyReviewRequest(
            ticker="QQQ",
            desired_amount_krw=1_000_000,
            reason_text="많이 빠져서 지금 놓치면 아쉬움",
            fomo_score=8,
            friend_influence_score=1,
        ),
        portfolio,
        events=[],
        recent_trades=[],
        now=now,
        config=config,
    )
    assert decision.action == Action.NO_TRADE
    assert any("24시간" in reason for reason in decision.reason)


def test_assertive_language_blocks_new_buy(config, portfolio, now):
    decision = review_buy_request(
        BuyReviewRequest(
            ticker="AAPL",
            desired_amount_krw=1_000_000,
            reason_text="메타 실적날 무조건 폭등한다",
            fomo_score=5,
            friend_influence_score=1,
        ),
        portfolio,
        events=[],
        recent_trades=[],
        now=now,
        config=config,
    )
    assert decision.action == Action.NO_TRADE
    assert any("과신 언어 HIGH" in reason for reason in decision.reason)


def test_amd_earnings_24h_before_blocks(config, portfolio, now):
    decision = review_buy_request(
        BuyReviewRequest(
            ticker="AMD",
            desired_amount_krw=1_000_000,
            reason_text="실적 전에 확인",
            fomo_score=5,
            friend_influence_score=1,
        ),
        portfolio,
        events=[
            Event(
                ticker="AMD",
                event_type="EARNINGS",
                event_time=now + timedelta(hours=24),
                importance="HIGH",
            )
        ],
        recent_trades=[],
        now=now,
        config=config,
    )
    assert decision.action == Action.NO_TRADE
    assert any("실적" in reason for reason in decision.reason)


def test_mvst_loss_averaging_is_blocked(config, now):
    mvst_portfolio = PortfolioSnapshot(
        cash_krw=20_000_000,
        total_value_krw=22_000_000,
        holdings=[
            Holding(
                ticker="MVST",
                market="US",
                quantity=400,
                avg_price=10,
                current_price=0.52,
                currency="USD",
                asset_type="EQUITY",
                sector_tag="SPECULATIVE_LOSS",
            )
        ],
    )
    decision = review_buy_request(
        BuyReviewRequest(
            ticker="MVST",
            desired_amount_krw=1_000_000,
            reason_text="반등해서 평단을 낮출지 검토",
            fomo_score=5,
            friend_influence_score=1,
        ),
        mvst_portfolio,
        events=[],
        recent_trades=[],
        now=now,
        config=config,
    )
    assert decision.action == Action.NO_TRADE
    assert any("손실" in reason for reason in decision.reason)


def test_same_ticker_within_week_blocks(config, portfolio, now):
    trade = TradeEntry(
        timestamp=now - timedelta(days=3),
        ticker="QQQ",
        action="BUY",
        quantity=1,
        avg_price=660,
        reason_text="기록",
        fomo_score=3,
        friend_influence_score=1,
        price_at_entry=660,
    )
    decision = review_buy_request(
        BuyReviewRequest(
            ticker="QQQ",
            desired_amount_krw=1_000_000,
            reason_text="다시 검토",
            fomo_score=3,
            friend_influence_score=1,
        ),
        portfolio,
        events=[],
        recent_trades=[trade],
        now=now,
        config=config,
    )
    assert decision.action == Action.NO_TRADE
    assert any("1주일" in reason for reason in decision.reason)


def test_low_fomo_score_with_urgent_reason_blocks_for_mismatch(config, portfolio, now):
    decision = review_buy_request(
        BuyReviewRequest(
            ticker="AAPL",
            desired_amount_krw=1_000_000,
            reason_text="오늘 놓치면 후회할 것 같아서 지금 검토",
            fomo_score=2,
            friend_influence_score=1,
        ),
        portfolio,
        events=[],
        recent_trades=[],
        now=now,
        config=config,
    )
    assert decision.action == Action.NO_TRADE
    assert any("입력 점수-사유 불일치" in reason and "FOMO" in reason for reason in decision.reason)


def test_low_external_score_with_recommendation_reason_blocks_for_mismatch(config, portfolio, now):
    decision = review_buy_request(
        BuyReviewRequest(
            ticker="AAPL",
            desired_amount_krw=1_000_000,
            reason_text="유튜브 추천이랑 커뮤니티에서 좋다고 해서 검토",
            fomo_score=3,
            friend_influence_score=1,
        ),
        portfolio,
        events=[],
        recent_trades=[],
        now=now,
        config=config,
    )
    assert decision.action == Action.NO_TRADE
    assert any("외부 영향 점수" in reason and "불일치" in reason for reason in decision.reason)
