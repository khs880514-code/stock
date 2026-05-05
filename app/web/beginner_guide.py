from __future__ import annotations


def render_workflow_guide() -> str:
    return """<div class="beginner-guide">
  <h2>오늘은 이 순서로 보세요</h2>
  <ol>
    <li><b>정보 확인</b><span>가격, 뉴스, 공시, 실적일이 오래되지 않았는지 먼저 봅니다.</span></li>
    <li><b>후보 고르기</b><span>재무지표로 걸러진 종목을 봅니다. 검토 후보는 매수 지시가 아닙니다.</span></li>
    <li><b>매수 전 점검</b><span>FOMO, 외부영향, 최근 매매, 보유 비중을 넣고 룰엔진으로 한번 멈춰 봅니다.</span></li>
    <li><b>내 계좌 확인</b><span>현금, 보유종목, 관심종목이 실제 Toss/Kiwoom 상황과 맞는지 확인합니다.</span></li>
    <li><b>기록/복기</b><span>매수·매도 이유를 남깁니다. 나중에 손실 방지 룰을 고치는 근거가 됩니다.</span></li>
  </ol>
</div>"""


def render_tab_intro(title: str, body: str, next_step: str = "") -> str:
    next_html = f"<p><b>다음:</b> {next_step}</p>" if next_step else ""
    return f"""<div class="tab-intro">
  <h2>{title}</h2>
  <p>{body}</p>
  {next_html}
</div>"""
