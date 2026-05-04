from datetime import date

from app.data.ticker_sensitivity import TickerSensitivityStore
from app.models import TickerSensitivitySnapshot


def test_ticker_sensitivity_store_round_trips_manual_snapshot(tmp_path):
    store = TickerSensitivityStore(tmp_path / "sensitivity.sqlite3")
    store.upsert(
        TickerSensitivitySnapshot(
            ticker="000660.KS",
            market="KR",
            sector_tag="AI_SEMICONDUCTOR",
            us_sector_proxy_symbol="SMH",
            foreign_ownership_pct=53.0,
            foreign_ownership_taken_at=date(2026, 5, 4),
            us_sector_corr_60d=0.78,
            beta_to_kospi_60d=1.2,
            corr_taken_at=date(2026, 5, 4),
            manual_override=True,
        )
    )

    snapshot = store.get("000660.ks")

    assert snapshot is not None
    assert snapshot.ticker == "000660.KS"
    assert snapshot.us_sector_proxy_symbol == "SMH"
    assert snapshot.foreign_ownership_pct == 53.0
    assert snapshot.manual_override is True


def test_seed_kr_semiconductor_defaults(tmp_path):
    store = TickerSensitivityStore(tmp_path / "seed.sqlite3")

    count = store.seed_kr_semiconductor_defaults(date(2026, 5, 4))

    assert count == 2
    samsung = store.get("005930.KS")
    hynix = store.get("000660.KS")
    assert samsung is not None
    assert samsung.us_sector_proxy_symbol == "SMH"
    assert hynix is not None
    assert hynix.us_sector_corr_60d == 0.78
