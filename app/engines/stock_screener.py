from __future__ import annotations

from dataclasses import dataclass, field

from app.data.fundamentals_store import FundamentalSnapshot


@dataclass(frozen=True)
class ScreenerCriteria:
    max_per: float = 25.0
    max_pbr: float = 4.0
    max_debt_to_equity_pct: float = 150.0
    min_roe_pct: float = 8.0
    min_operating_margin_pct: float = 5.0
    min_revenue_growth_pct: float = -5.0
    min_fcf_yield_pct: float | None = None
    min_market_cap_krw: float | None = None
    min_data_points_for_pass: int = 5


@dataclass(frozen=True)
class ScreenerCandidate:
    ticker: str
    company_name: str
    market: str
    sector_tag: str
    status: str
    score: int
    data_points: int
    reasons: list[str] = field(default_factory=list)
    cautions: list[str] = field(default_factory=list)
    missing_metrics: list[str] = field(default_factory=list)


def screen(
    items: list[FundamentalSnapshot],
    criteria: ScreenerCriteria | None = None,
) -> list[ScreenerCandidate]:
    criteria = criteria or ScreenerCriteria()
    candidates = [_evaluate(item, criteria) for item in items]
    return sorted(
        candidates,
        key=lambda item: (
            _status_rank(item.status),
            -item.score,
            -item.data_points,
            item.ticker,
        ),
    )


def _evaluate(item: FundamentalSnapshot, criteria: ScreenerCriteria) -> ScreenerCandidate:
    score = 0
    reasons: list[str] = []
    cautions: list[str] = []
    missing: list[str] = []
    hard_fails: list[str] = []

    score += _low_is_good("PER", item.per, criteria.max_per, reasons, hard_fails, missing)
    score += _low_is_good("Forward PER", item.forward_per, criteria.max_per, reasons, hard_fails, missing)
    score += _low_is_good("PBR", item.pbr, criteria.max_pbr, reasons, hard_fails, missing)
    score += _low_is_good("Debt/Equity", item.debt_to_equity_pct, criteria.max_debt_to_equity_pct, reasons, hard_fails, missing)
    score += _high_is_good("ROE", item.roe_pct, criteria.min_roe_pct, reasons, hard_fails, missing)
    score += _high_is_good(
        "Operating margin",
        item.operating_margin_pct,
        criteria.min_operating_margin_pct,
        reasons,
        hard_fails,
        missing,
    )
    score += _high_is_good(
        "Revenue growth",
        item.revenue_growth_pct,
        criteria.min_revenue_growth_pct,
        reasons,
        hard_fails,
        missing,
    )
    if criteria.min_fcf_yield_pct is not None:
        score += _high_is_good(
            "FCF yield",
            item.fcf_yield_pct,
            criteria.min_fcf_yield_pct,
            reasons,
            hard_fails,
            missing,
        )
    if criteria.min_market_cap_krw is not None:
        score += _high_is_good(
            "Market cap",
            item.market_cap_krw,
            criteria.min_market_cap_krw,
            reasons,
            hard_fails,
            missing,
        )

    _optional_positive("ROIC", item.roic_pct, 8.0, reasons)
    _optional_positive("EPS growth", item.eps_growth_pct, 0.0, reasons)
    _optional_positive("Operating income growth", item.operating_income_growth_pct, 0.0, reasons)
    _optional_positive("3M momentum", item.price_momentum_3m_pct, 0.0, reasons)
    _optional_positive("12M momentum", item.price_momentum_12m_pct, 0.0, reasons)

    data_points = _data_points(item)
    if hard_fails:
        status = "REJECT"
        cautions.extend(hard_fails)
    elif data_points < criteria.min_data_points_for_pass:
        status = "WATCH"
        cautions.append(f"데이터 부족: 핵심 지표 {data_points}개만 입력됨")
    elif score >= 5:
        status = "PASS"
    else:
        status = "WATCH"
        cautions.append("통과 조건은 피했지만 강한 우위 점수가 부족함")

    return ScreenerCandidate(
        ticker=item.ticker,
        company_name=item.company_name,
        market=item.market,
        sector_tag=item.sector_tag,
        status=status,
        score=score,
        data_points=data_points,
        reasons=reasons[:6],
        cautions=cautions[:6],
        missing_metrics=missing[:8],
    )


def _low_is_good(
    label: str,
    value: float | None,
    threshold: float,
    reasons: list[str],
    hard_fails: list[str],
    missing: list[str],
) -> int:
    if value is None:
        missing.append(label)
        return 0
    if value <= threshold:
        reasons.append(f"{label} {value:g} <= {threshold:g}")
        return 1
    hard_fails.append(f"{label} {value:g} > {threshold:g}")
    return -1


def _high_is_good(
    label: str,
    value: float | None,
    threshold: float,
    reasons: list[str],
    hard_fails: list[str],
    missing: list[str],
) -> int:
    if value is None:
        missing.append(label)
        return 0
    if value >= threshold:
        reasons.append(f"{label} {value:g} >= {threshold:g}")
        return 1
    hard_fails.append(f"{label} {value:g} < {threshold:g}")
    return -1


def _optional_positive(label: str, value: float | None, threshold: float, reasons: list[str]) -> None:
    if value is not None and value >= threshold:
        reasons.append(f"{label} {value:g} >= {threshold:g}")


def _data_points(item: FundamentalSnapshot) -> int:
    values = [
        item.per,
        item.forward_per,
        item.pbr,
        item.debt_to_equity_pct,
        item.roe_pct,
        item.operating_margin_pct,
        item.revenue_growth_pct,
        item.fcf_yield_pct,
        item.market_cap_krw,
    ]
    return sum(value is not None for value in values)


def _status_rank(status: str) -> int:
    return {"PASS": 0, "WATCH": 1, "REJECT": 2}.get(status, 9)
