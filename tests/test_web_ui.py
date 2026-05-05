from app.config import AppConfig
from app.data.portfolio_store import PortfolioStore
from app.models import Holding
from app.web_ui import render_dashboard


def test_web_dashboard_renders_portfolio(tmp_path):
    config = AppConfig(db_path=tmp_path / "ui.sqlite3")
    store = PortfolioStore(config.db_path, config)
    store.set_cash(12_000_000)
    store.save_holding(
        Holding(
            ticker="AAPL",
            quantity=2,
            avg_price=150,
            current_price=180,
            currency="USD",
            sector_tag="BIG_TECH",
        )
    )
    html = render_dashboard(config)
    assert "주식 판단 친구" in html
    assert "Stock Expert Friend" in html
    assert 'data-tab-target="overview"' in html
    assert 'data-tab-target="data-check"' in html
    assert 'data-tab-target="candidate"' in html
    assert 'data-tab-target="buy-review"' in html
    assert 'data-tab-target="portfolio"' in html
    assert 'data-tab-target="journal"' in html
    assert "오늘은 이 순서로 보세요" in html
    assert "AAPL" in html
    assert "매수 전 체크" in html
    assert "고급 보호장치 펼치기" in html
    assert "점수 입력 기준" in html
    assert "FOMO 7 이상은 대기" in html
    assert "오늘 적용되는 안전 규칙" in html
    assert "룰엔진 판단 기준" in html
    assert "NO_TRADE" in html
    assert "post_drop_chase" in html
    assert "최근 정보" in html
    assert "정보 최신성" in html
    assert "API 연결 준비 상태" in html
    assert "계좌 설정" in html
    assert "일반 - 토스증권" in html
    assert "ISA - 키움증권" in html
    assert "가격 업데이트" in html
    assert "뉴스 업데이트" in html
    assert "공시 업데이트" in html
    assert "실적 일정" in html
    assert "외부 리서치 노트" in html
    assert "반대근거" in html
    assert "확인질문" in html
    assert "강제 장치가 아니라 자기기록" in html
    assert "불일치 경고나 대기" in html
    assert "뉴스/RSS" in html
    assert "SEC 공시" in html
    assert html.index("매수 전 체크") < html.index("현재 보유 상태")
    assert html.index("현재 보유 상태") < html.index("고급 보호장치 펼치기")
    assert html.index('data-tab-panel="journal"') < html.index("매매 일지 입력")
