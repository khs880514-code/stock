from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
from typing import Protocol

from app.data.fundamentals_store import FundamentalSnapshot, FundamentalsStore
from app.data.opendart_fundamentals import canonical_kr_ticker
from app.data.price_history import PriceHistoryStore


class MarketSummaryClient(Protocol):
    def summary(self, ticker: str) -> dict:
        pass


class YFinanceMarketSummaryClient:
    def summary(self, ticker: str) -> dict:
        try:
            import yfinance as yf
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise RuntimeError("yfinance is not installed") from exc
        return dict(yf.Ticker(ticker).get_info() or {})


def update_market_fundamentals(
    db_path: Path | str,
    ticker: str,
    sector_tag: str = "UNKNOWN",
    fx_usd_krw: float = 1350.0,
    today: date | None = None,
    client: MarketSummaryClient | None = None,
    refresh_prices: bool = True,
) -> FundamentalSnapshot:
    today = today or date.today()
    normalized_ticker = _normalize_ticker(ticker)
    store = FundamentalsStore(db_path)
    existing = store.get(normalized_ticker)
    summary = (client or YFinanceMarketSummaryClient()).summary(normalized_ticker)
    momentum_3m, momentum_12m = _update_price_history_and_momentum(
        db_path,
        normalized_ticker,
        today,
        refresh_prices=refresh_prices,
    )
    snapshot = _merge_market_summary(
        existing=existing,
        ticker=normalized_ticker,
        sector_tag=sector_tag,
        summary=summary,
        fx_usd_krw=fx_usd_krw,
        today=today,
        momentum_3m=momentum_3m,
        momentum_12m=momentum_12m,
    )
    store.upsert(snapshot)
    return snapshot


def _merge_market_summary(
    existing: FundamentalSnapshot | None,
    ticker: str,
    sector_tag: str,
    summary: dict,
    fx_usd_krw: float,
    today: date,
    momentum_3m: float | None,
    momentum_12m: float | None,
) -> FundamentalSnapshot:
    base = existing or FundamentalSnapshot(ticker=ticker)
    currency = str(summary.get("financialCurrency") or summary.get("currency") or base.currency or "KRW").upper()
    market = base.market if existing else ("KR" if ticker.endswith((".KS", ".KQ")) else "US")
    return replace(
        base,
        ticker=ticker,
        market=market,
        company_name=_pick_text(summary, "longName", "shortName") or base.company_name,
        sector_tag=(sector_tag if sector_tag != "UNKNOWN" else base.sector_tag) or "UNKNOWN",
        as_of_date=today,
        currency=currency,
        market_cap_krw=_market_cap_krw(_pick_number(summary, "marketCap"), currency, fx_usd_krw),
        per=_prefer(_pick_number(summary, "trailingPE"), base.per),
        forward_per=_prefer(_pick_number(summary, "forwardPE"), base.forward_per),
        pbr=_prefer(_pick_number(summary, "priceToBook"), base.pbr),
        psr=_prefer(_pick_number(summary, "priceToSalesTrailing12Months"), base.psr),
        ev_ebitda=_prefer(_pick_number(summary, "enterpriseToEbitda"), base.ev_ebitda),
        dividend_yield_pct=_prefer(_dividend_yield_pct(summary), base.dividend_yield_pct),
        roe_pct=_prefer(base.roe_pct, _pct(summary, "returnOnEquity")),
        roa_pct=_prefer(base.roa_pct, _pct(summary, "returnOnAssets")),
        operating_margin_pct=_prefer(base.operating_margin_pct, _pct(summary, "operatingMargins")),
        net_margin_pct=_prefer(base.net_margin_pct, _pct(summary, "profitMargins")),
        revenue_growth_pct=_prefer(base.revenue_growth_pct, _pct(summary, "revenueGrowth")),
        eps_growth_pct=_prefer(base.eps_growth_pct, _pct(summary, "earningsGrowth")),
        debt_to_equity_pct=_prefer(base.debt_to_equity_pct, _pick_number(summary, "debtToEquity")),
        current_ratio=_prefer(base.current_ratio, _pick_number(summary, "currentRatio")),
        fcf_yield_pct=_prefer(_fcf_yield(summary), base.fcf_yield_pct),
        price_momentum_3m_pct=_prefer(momentum_3m, base.price_momentum_3m_pct),
        price_momentum_12m_pct=_prefer(momentum_12m, base.price_momentum_12m_pct),
        source=_join_source(base.source, "yfinance:summary"),
        notes=_join_notes(
            base.notes,
            "Yahoo/yfinance market summary merged; verify provider values before using for final review.",
        ),
    )


def _update_price_history_and_momentum(
    db_path: Path | str,
    ticker: str,
    today: date,
    refresh_prices: bool = True,
) -> tuple[float | None, float | None]:
    store = PriceHistoryStore(db_path)
    if refresh_prices:
        try:
            store.fetch_yfinance_into_cache(ticker, today - timedelta(days=420), today)
        except Exception:
            pass
    bars = store.get_window(ticker, today - timedelta(days=420), today)
    if not bars:
        return None, None
    latest = bars[-1]
    return _momentum(bars, latest.date - timedelta(days=90), latest.close), _momentum(
        bars,
        latest.date - timedelta(days=365),
        latest.close,
    )


def _momentum(bars, target: date, latest_close: float) -> float | None:
    candidates = [bar for bar in bars if bar.date <= target and bar.close]
    if not candidates:
        return None
    base_close = candidates[-1].close
    if not base_close:
        return None
    return round((latest_close - base_close) / base_close * 100, 2)


def _normalize_ticker(ticker: str) -> str:
    raw = ticker.strip().upper()
    if raw[:6].isdigit() and ("." in raw or len(raw) == 6):
        return canonical_kr_ticker(raw)
    return raw


def _pick_text(summary: dict, *keys: str) -> str:
    for key in keys:
        value = summary.get(key)
        if value:
            return str(value)
    return ""


def _pick_number(summary: dict, key: str) -> float | None:
    value = summary.get(key)
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, str) and value.strip().upper() in {"", "N/A"}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pct(summary: dict, key: str) -> float | None:
    value = _pick_number(summary, key)
    if value is None:
        return None
    return round(value * 100, 2) if abs(value) <= 1 else round(value, 2)


def _dividend_yield_pct(summary: dict) -> float | None:
    value = _pick_number(summary, "dividendYield")
    if value is None:
        return None
    return round(value, 2) if value > 0.2 else round(value * 100, 2)


def _market_cap_krw(market_cap: float | None, currency: str, fx_usd_krw: float) -> float | None:
    if market_cap is None:
        return None
    if currency == "USD":
        return round(market_cap * fx_usd_krw, 0)
    return market_cap


def _fcf_yield(summary: dict) -> float | None:
    market_cap = _pick_number(summary, "marketCap")
    fcf = _pick_number(summary, "freeCashflow")
    if not market_cap or fcf is None:
        return None
    return round(fcf / market_cap * 100, 2)


def _prefer(new_value: float | None, existing_value: float | None) -> float | None:
    return new_value if new_value is not None else existing_value


def _join_source(existing: str, new_source: str) -> str:
    parts = [part for part in [existing, new_source] if part and part != "manual"]
    return ";".join(dict.fromkeys(parts)) or new_source


def _join_notes(existing: str, note: str) -> str:
    if not existing:
        return note
    if note in existing:
        return existing
    return f"{existing} | {note}"
