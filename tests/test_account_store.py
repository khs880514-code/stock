from app.data.account_store import AccountStore, BrokerAccount, account_route_note, default_accounts


def test_account_store_saves_toss_and_kiwoom_defaults(tmp_path):
    store = AccountStore(tmp_path / "accounts.sqlite3")
    for account in default_accounts():
        store.upsert(account)
    accounts = store.list_accounts()
    assert [account.account_key for account in accounts] == ["GENERAL_TOSS", "ISA_KIWOOM"]
    assert accounts[0].broker_name == "토스증권"
    assert accounts[1].broker_name == "키움증권"
    assert "키움증권" in account_route_note(store.get("ISA_KIWOOM"))


def test_account_route_note_handles_missing_account():
    assert "미설정" in account_route_note(None)


def test_account_store_updates_custom_account(tmp_path):
    store = AccountStore(tmp_path / "accounts.sqlite3")
    store.upsert(
        BrokerAccount(
            account_key="GENERAL_TOSS",
            account_type="GENERAL",
            broker_name="토스증권",
            default_for="일반",
            notes="초기",
        )
    )
    store.upsert(
        BrokerAccount(
            account_key="GENERAL_TOSS",
            account_type="GENERAL",
            broker_name="토스증권",
            default_for="해외주식",
            notes="수정",
        )
    )
    account = store.get("GENERAL_TOSS")
    assert account.default_for == "해외주식"
    assert account.notes == "수정"
