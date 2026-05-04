from datetime import timedelta

from app.journal.trade_journal import TradeJournal
from app.models import Action, AlertDecision, TradeEntry


def test_trade_journal_saves_trade_and_alert(tmp_path, now):
    journal = TradeJournal(tmp_path / "test.sqlite3")
    trade_id = journal.add_trade(
        TradeEntry(
            timestamp=now - timedelta(days=7),
            ticker="AMD",
            account_key="ISA_KIWOOM",
            action="BUY",
            quantity=1,
            avg_price=170,
            reason_text="테스트 기록",
            fomo_score=5,
            friend_influence_score=1,
            price_at_entry=170,
        )
    )
    assert trade_id > 0
    reviews = journal.one_week_reviews(now)
    assert len(reviews) == 1
    assert reviews[0].account_key == "ISA_KIWOOM"

    alert_id = journal.log_alert(
        "test",
        "짧고 직설적인 메시지",
        AlertDecision(ticker="AMD", action=Action.NO_TRADE, reason=["테스트"]),
    )
    assert alert_id > 0
