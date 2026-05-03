from __future__ import annotations

from datetime import datetime

from app.models import TradeEntry


def build_monthly_report(trades: list[TradeEntry], now: datetime) -> str:
    month_label = now.strftime("%Y-%m")
    if not trades:
        return "\n".join(
            [
                f"■ {month_label} 월간 리포트",
                "- 기록된 매매가 없음",
                "- 다음 달도 매매 판단보다 기록률을 우선 확인",
            ]
        )

    avg_fomo = sum(trade.fomo_score for trade in trades) / len(trades)
    chase_count = sum(1 for trade in trades if trade.mistake_type.value == "FOMO_BUY")
    loss_avg_count = sum(1 for trade in trades if trade.mistake_type.value == "LOSS_AVERAGING")
    one_month_returns = [
        ((trade.price_1m - trade.price_at_entry) / trade.price_at_entry * 100)
        for trade in trades
        if trade.price_1m is not None and trade.price_at_entry
    ]
    returns_line = (
        f"- 1개월 후 평균 결과: {sum(one_month_returns) / len(one_month_returns):+.1f}%"
        if one_month_returns
        else "- 1개월 후 가격 데이터 부족"
    )
    return "\n".join(
        [
            f"■ {month_label} 월간 리포트",
            f"- 총 매매 기록: {len(trades)}건",
            f"- 평균 FOMO 점수: {avg_fomo:.1f}/10",
            f"- 추격매수 의심 기록: {chase_count}건",
            f"- 손실 종목 추가 투입 의심 기록: {loss_avg_count}건",
            returns_line,
            "- FOMO 점수와 1개월 결과를 함께 보고 다음 달 한도를 조정",
        ]
    )

