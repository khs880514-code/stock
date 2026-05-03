from datetime import datetime, timedelta

from app.config import load_config
from app.db.database import init_db
from app.journal.monthly_report import build_monthly_report
from app.journal.trade_journal import TradeJournal


if __name__ == "__main__":
    config = load_config()
    init_db(config.db_path)
    journal = TradeJournal(config.db_path)
    now = datetime.now().astimezone()
    print(build_monthly_report(journal.recent_trades(now - timedelta(days=35)), now))

