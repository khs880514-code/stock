from __future__ import annotations

import html

from app.config import AppConfig
from app.data.portfolio_store import holding_value_krw


def render_holdings_table(holdings, config: AppConfig) -> str:
    if not holdings:
        return '<p class="empty">보유종목 없음</p>'
    rows = "".join(
        (
            f"<tr><td>{_e(h.ticker)}</td><td>{_e(h.account_key)}</td><td><b>{h.quantity:g}주</b></td>"
            f"<td>{h.avg_price:g} {_e(h.currency)}{_krw_hint(h.avg_price, h.currency, config.fx_usd_krw)}</td>"
            f"<td>{h.current_price:g} {_e(h.currency)}{_krw_hint(h.current_price, h.currency, config.fx_usd_krw)}</td>"
            f"<td><b>{int(holding_value_krw(h, config.fx_usd_krw)):,}원</b></td><td>{_e(h.sector_tag)}</td>"
            f"<td>{_delete_form(h.ticker)}</td></tr>"
        )
        for h in holdings
    )
    return (
        "<table><thead><tr><th>종목</th><th>계좌</th><th>보유수량</th><th>평단</th><th>현재가</th>"
        f"<th>평가금액</th><th>태그</th><th>수정/삭제</th></tr></thead><tbody>{rows}</tbody></table>"
        '<p class="form-note">수정은 같은 종목을 다시 저장하면 덮어씁니다. 잘못 넣은 종목은 표의 삭제 버튼으로 지우세요.</p>'
        '<p class="form-note">USD 원화 환산은 설정 환율 기준 보조 표시입니다. 무료 가격 데이터는 실시간 체결가가 아니라 지연/종가일 수 있습니다.</p>'
    )


def _krw_hint(value: float, currency: str, fx_usd_krw: float) -> str:
    if currency != "USD":
        return ""
    return f'<br><span class="subtle">약 {int(value * fx_usd_krw):,}원</span>'


def _delete_form(ticker: str) -> str:
    return (
        '<form class="inline-form" method="post" action="/delete-holding">'
        f'<input type="hidden" name="ticker" value="{_e(ticker)}">'
        '<button class="danger-button" type="submit">삭제</button>'
        "</form>"
    )


def _e(value: object) -> str:
    return html.escape(str(value), quote=True)
