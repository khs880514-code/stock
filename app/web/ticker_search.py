from __future__ import annotations

import html


TICKER_OPTIONS = [
    {
        "ticker": "005930.KS",
        "label": "삼성전자",
        "aliases": ["삼성전자", "삼전", "삼성", "005930", "005930.KS"],
        "market": "KR",
        "currency": "KRW",
        "company": "삼성전자",
        "sector": "AI_SEMICONDUCTOR",
    },
    {
        "ticker": "000660.KS",
        "label": "SK하이닉스",
        "aliases": ["SK하이닉스", "하이닉스", "하닉", "000660", "000660.KS"],
        "market": "KR",
        "currency": "KRW",
        "company": "SK하이닉스",
        "sector": "AI_SEMICONDUCTOR",
    },
    {
        "ticker": "263750.KQ",
        "label": "펄어비스",
        "aliases": ["펄어비스", "263750", "263750.KQ"],
        "market": "KR",
        "currency": "KRW",
        "company": "펄어비스",
        "sector": "GAME",
    },
    {
        "ticker": "AAPL",
        "label": "애플",
        "aliases": ["애플", "Apple", "AAPL"],
        "market": "US",
        "currency": "USD",
        "company": "Apple",
        "sector": "BIG_TECH",
    },
    {
        "ticker": "AMD",
        "label": "AMD",
        "aliases": ["AMD", "에이엠디"],
        "market": "US",
        "currency": "USD",
        "company": "AMD",
        "sector": "AI_SEMICONDUCTOR",
    },
    {
        "ticker": "MVST",
        "label": "마이크로배스트",
        "aliases": ["마이크로배스트", "Microvast", "MVST"],
        "market": "US",
        "currency": "USD",
        "company": "Microvast",
        "sector": "BATTERY",
    },
    {
        "ticker": "QQQ",
        "label": "나스닥100 ETF",
        "aliases": ["QQQ", "나스닥100", "나스닥", "인베스코QQQ"],
        "market": "US",
        "currency": "USD",
        "company": "Invesco QQQ",
        "sector": "CORE_ETF",
    },
    {
        "ticker": "SMH",
        "label": "반도체 ETF",
        "aliases": ["SMH", "반도체ETF", "반도체 ETF"],
        "market": "US",
        "currency": "USD",
        "company": "VanEck Semiconductor ETF",
        "sector": "AI_SEMICONDUCTOR",
    },
    {
        "ticker": "NVDA",
        "label": "엔비디아",
        "aliases": ["엔비디아", "NVIDIA", "NVDA"],
        "market": "US",
        "currency": "USD",
        "company": "NVIDIA",
        "sector": "AI_SEMICONDUCTOR",
    },
    {
        "ticker": "MSFT",
        "label": "마이크로소프트",
        "aliases": ["마이크로소프트", "Microsoft", "MSFT"],
        "market": "US",
        "currency": "USD",
        "company": "Microsoft",
        "sector": "BIG_TECH",
    },
    {
        "ticker": "GOOGL",
        "label": "구글/알파벳",
        "aliases": ["구글", "알파벳", "Google", "Alphabet", "GOOGL"],
        "market": "US",
        "currency": "USD",
        "company": "Alphabet",
        "sector": "BIG_TECH",
    },
    {
        "ticker": "ASML",
        "label": "ASML",
        "aliases": ["ASML", "에이에스엠엘"],
        "market": "US",
        "currency": "USD",
        "company": "ASML Holding",
        "sector": "AI_SEMICONDUCTOR",
    },
]


def ticker_input(label: str, value: str, *, name: str = "ticker", required: bool = True) -> str:
    required_attr = " required" if required else ""
    return (
        f'<label>{_e(label)}<input name="{_e(name)}" class="ticker-input" list="ticker-options" '
        f'value="{_e(value)}"{required_attr}>'
        '<span class="input-help">한글명으로 검색 가능: 삼성전자, 하이닉스, 애플, 엔비디아</span></label>'
    )


def ticker_list_input(label: str, value: str, *, name: str = "tickers", required: bool = True) -> str:
    required_attr = " required" if required else ""
    return (
        f'<label>{_e(label)}<input name="{_e(name)}" class="ticker-list-input" list="ticker-options" '
        f'value="{_e(value)}"{required_attr}>'
        '<span class="input-help">여러 종목은 쉼표로 구분: AMD, 애플, 삼성전자</span></label>'
    )


def render_ticker_datalist() -> str:
    options = []
    for item in TICKER_OPTIONS:
        label = f"{item['ticker']} - {item['label']}"
        for alias in item["aliases"]:
            options.append(f'<option value="{_e(alias)}" label="{_e(label)}"></option>')
        options.append(f'<option value="{_e(item["ticker"])}" label="{_e(item["label"])}"></option>')
    return f'<datalist id="ticker-options">{"".join(dict.fromkeys(options))}</datalist>'


def render_ticker_script() -> str:
    items = ",".join(_js_item(item) for item in TICKER_OPTIONS)
    return f"""<script>
(() => {{
  const tickerItems = [{items}];
  const lookup = new Map();
  const normalize = (value) => String(value || "").trim().toLowerCase().replace(/\\s+/g, "");
  tickerItems.forEach((item) => {{
    [item.ticker, item.label, ...item.aliases].forEach((alias) => lookup.set(normalize(alias), item));
  }});
  const resolve = (token) => lookup.get(normalize(token));
  const setIfPresent = (form, name, value, overwriteDefault = false) => {{
    const field = form.querySelector(`[name="${{name}}"]`);
    if (!field || !value) return;
    if (field.tagName === "SELECT") {{
      const option = Array.from(field.options).find((item) => item.value === value || item.text === value);
      if (option) field.value = option.value;
      return;
    }}
    const current = String(field.value || "").trim();
    if (!current || overwriteDefault) field.value = value;
  }};
  const applySingle = (input) => {{
    const item = resolve(input.value);
    if (!item) return;
    input.value = item.ticker;
    const form = input.closest("form");
    if (!form) return;
    setIfPresent(form, "market", item.market, true);
    setIfPresent(form, "currency", item.currency, true);
    setIfPresent(form, "company_name", item.company, true);
    setIfPresent(form, "sector_tag", item.sector, false);
  }};
  const applyList = (input) => {{
    const parts = String(input.value || "").split(",").map((part) => part.trim()).filter(Boolean);
    input.value = parts.map((part) => {{
      const item = resolve(part);
      return item ? item.ticker : part;
    }}).join(",");
  }};
  document.querySelectorAll(".ticker-input").forEach((input) => {{
    input.addEventListener("change", () => applySingle(input));
    input.addEventListener("blur", () => applySingle(input));
  }});
  document.querySelectorAll(".ticker-list-input").forEach((input) => {{
    input.addEventListener("change", () => applyList(input));
    input.addEventListener("blur", () => applyList(input));
  }});
  document.querySelectorAll("form").forEach((form) => {{
    form.addEventListener("submit", () => {{
      form.querySelectorAll(".ticker-input").forEach(applySingle);
      form.querySelectorAll(".ticker-list-input").forEach(applyList);
    }});
  }});
}})();
</script>"""


def _js_item(item: dict[str, object]) -> str:
    aliases = ",".join(f'"{_js(str(alias))}"' for alias in item["aliases"])
    return (
        "{"
        f'ticker:"{_js(str(item["ticker"]))}",'
        f'label:"{_js(str(item["label"]))}",'
        f'aliases:[{aliases}],'
        f'market:"{_js(str(item["market"]))}",'
        f'currency:"{_js(str(item["currency"]))}",'
        f'company:"{_js(str(item["company"]))}",'
        f'sector:"{_js(str(item["sector"]))}"'
        "}"
    )


def _e(value: object) -> str:
    return html.escape(str(value), quote=True)


def _js(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
