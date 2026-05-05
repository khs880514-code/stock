from __future__ import annotations

import html


def render_data_status_panel(data_status, api_status) -> str:
    return f"""<div class="data-status">
  <div>
    <h3>종목별 데이터 신선도</h3>
    {_ticker_status_table(data_status)}
  </div>
  <div>
    <h3>API 연결 준비 상태</h3>
    {_api_status_table(api_status)}
  </div>
</div>"""


def _ticker_status_table(items) -> str:
    if not items:
        return '<p class="empty">보유/관심 종목 없음</p>'
    rows = "".join(
        (
            f"<tr><td>{_e(item.ticker)}</td><td>{_e(item.latest_price_date or '-')}</td>"
            f"<td>{_e(item.latest_news_at or '-')}</td><td>{_e(item.latest_filing_date or '-')}</td>"
            f"<td>{_e(item.next_earnings_date or '-')}</td><td>{item.research_note_count}</td>"
            f"<td>{_e(item.freshness_label)}</td></tr>"
        )
        for item in items
    )
    return (
        "<table><thead><tr><th>종목</th><th>가격</th><th>뉴스</th><th>공시</th>"
        "<th>실적</th><th>노트</th><th>상태</th></tr></thead><tbody>"
        f"{rows}</tbody></table>"
    )


def _api_status_table(items) -> str:
    rows = "".join(
        f"<tr><td>{_e(item.name)}</td><td>{_e(item.status)}</td><td>{_e(item.next_step)}</td></tr>"
        for item in items
    )
    return f"<table><thead><tr><th>항목</th><th>상태</th><th>다음 작업</th></tr></thead><tbody>{rows}</tbody></table>"


def _e(value: object) -> str:
    return html.escape(str(value), quote=True)
