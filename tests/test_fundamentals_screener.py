from __future__ import annotations

from argparse import Namespace

from app.config import AppConfig
from app.data.fundamentals_store import FundamentalSnapshot, FundamentalsStore
from app.engines.stock_screener import screen
from app.main import run_fundamental_list, run_fundamental_set, run_screen_stocks
from app.web_ui import handle_post, render_dashboard


def test_fundamentals_store_round_trip(tmp_path):
    store = FundamentalsStore(tmp_path / "fundamentals.sqlite3")
    store.upsert(
        FundamentalSnapshot(
            ticker="005930.KS",
            market="KR",
            company_name="Samsung Electronics",
            sector_tag="AI_SEMICONDUCTOR",
            per=14.2,
            pbr=1.3,
            roe_pct=12.0,
            debt_to_equity_pct=35.0,
            operating_margin_pct=18.0,
            revenue_growth_pct=7.5,
            source="manual-test",
        )
    )

    saved = store.get("005930.KS")
    assert saved is not None
    assert saved.company_name == "Samsung Electronics"
    assert saved.per == 14.2
    assert store.list_all()[0].source == "manual-test"


def test_stock_screener_pass_watch_reject():
    candidates = screen(
        [
            FundamentalSnapshot(
                ticker="PASS",
                per=12.0,
                forward_per=11.0,
                pbr=1.4,
                debt_to_equity_pct=40.0,
                roe_pct=16.0,
                operating_margin_pct=17.0,
                revenue_growth_pct=8.0,
            ),
            FundamentalSnapshot(ticker="WATCH", per=12.0, pbr=1.2),
            FundamentalSnapshot(
                ticker="REJECT",
                per=40.0,
                pbr=1.2,
                debt_to_equity_pct=30.0,
                roe_pct=15.0,
                operating_margin_pct=12.0,
                revenue_growth_pct=4.0,
            ),
        ]
    )

    statuses = {item.ticker: item.status for item in candidates}
    assert statuses["PASS"] == "PASS"
    assert statuses["WATCH"] == "WATCH"
    assert statuses["REJECT"] == "REJECT"


def test_fundamental_cli_and_web_flow(tmp_path):
    config = AppConfig(db_path=tmp_path / "cli-web.sqlite3")
    args = Namespace(
        ticker="000660.KS",
        market="KR",
        company_name="SK Hynix",
        sector_tag="AI_SEMICONDUCTOR",
        as_of_date=None,
        currency="KRW",
        market_cap_krw=100_000_000_000_000,
        per=10.0,
        forward_per=9.0,
        pbr=1.5,
        psr=None,
        ev_ebitda=None,
        dividend_yield_pct=None,
        roe_pct=18.0,
        roa_pct=None,
        roic_pct=12.0,
        operating_margin_pct=22.0,
        net_margin_pct=None,
        revenue_growth_pct=10.0,
        eps_growth_pct=8.0,
        operating_income_growth_pct=9.0,
        debt_to_equity_pct=35.0,
        current_ratio=None,
        interest_coverage=None,
        fcf_yield_pct=None,
        price_momentum_3m_pct=3.0,
        price_momentum_12m_pct=12.0,
        source="manual-test",
        notes="test",
        max_per=25.0,
        max_pbr=4.0,
        min_roe_pct=8.0,
        max_debt_to_equity_pct=150.0,
        min_operating_margin_pct=5.0,
        min_revenue_growth_pct=-5.0,
    )

    assert "000660.KS" in run_fundamental_set(config, args)
    assert "000660.KS" in run_fundamental_list(config)
    result = run_screen_stocks(config, args)
    assert "PASS" in result
    assert "000660.KS" in result

    notice, _ = handle_post(
        "/fundamental",
        config,
        {
            "ticker": "005930.KS",
            "market": "KR",
            "company_name": "Samsung Electronics",
            "sector_tag": "AI_SEMICONDUCTOR",
            "per": "12",
            "pbr": "1.2",
            "roe_pct": "11",
            "operating_margin_pct": "10",
            "revenue_growth_pct": "3",
            "debt_to_equity_pct": "40",
        },
    )
    assert "005930.KS" in notice

    html = render_dashboard(config)
    assert "후보 찾기" in html
    assert "오늘 후보 자동 수집" in html
    assert 'action="/auto-candidates"' in html
    assert "후보 판정 결과" in html
    assert "한줄 해석" in html
    assert "초보자 해석" in html
    assert "종목별 상세 검토" in html
    assert "다음 확인" in html
    assert "000660.KS" in html
    assert "005930.KS" in html
