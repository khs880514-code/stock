from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.db.database import connect, init_db


KST = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class BrokerAccount:
    account_key: str
    account_type: str
    broker_name: str
    default_for: str
    notes: str = ""
    updated_at: str = ""


class AccountStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        init_db(self.db_path)

    def upsert(self, account: BrokerAccount) -> None:
        now = account.updated_at or datetime.now(tz=KST).isoformat()
        with connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO broker_accounts (
                  account_key, account_type, broker_name, default_for, notes, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_key) DO UPDATE SET
                  account_type=excluded.account_type,
                  broker_name=excluded.broker_name,
                  default_for=excluded.default_for,
                  notes=excluded.notes,
                  updated_at=excluded.updated_at
                """,
                (
                    account.account_key.upper(),
                    account.account_type.upper(),
                    account.broker_name,
                    account.default_for,
                    account.notes,
                    now,
                ),
            )

    def list_accounts(self) -> list[BrokerAccount]:
        with connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT account_key, account_type, broker_name, default_for, notes, updated_at
                FROM broker_accounts
                ORDER BY
                  CASE account_type WHEN 'GENERAL' THEN 1 WHEN 'ISA' THEN 2 ELSE 9 END,
                  account_key
                """
            ).fetchall()
        return [BrokerAccount(**dict(row)) for row in rows]

    def get(self, account_key: str) -> BrokerAccount | None:
        with connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT account_key, account_type, broker_name, default_for, notes, updated_at
                FROM broker_accounts
                WHERE account_key = ?
                """,
                (account_key.upper(),),
            ).fetchone()
        return BrokerAccount(**dict(row)) if row else None


def default_accounts() -> list[BrokerAccount]:
    return [
        BrokerAccount(
            account_key="GENERAL_TOSS",
            account_type="GENERAL",
            broker_name="토스증권",
            default_for="일반 매매/해외주식",
            notes="API 연결 전까지 수동 입력 기준",
        ),
        BrokerAccount(
            account_key="ISA_KIWOOM",
            account_type="ISA",
            broker_name="키움증권",
            default_for="ISA 계좌",
            notes="ISA 한도/세제 규칙은 별도 수동 확인",
        ),
    ]


def account_route_note(account: BrokerAccount | None) -> str:
    if account is None:
        return "계좌 라우팅: 미설정. 계좌 설정에서 토스/키움 ISA를 먼저 저장하세요."
    return (
        f"계좌 라우팅: {account.account_key} / {account.broker_name} "
        f"({account.account_type}, {account.default_for})"
    )
