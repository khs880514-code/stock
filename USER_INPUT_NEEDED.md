# User Input Needed

Last updated: 2026-05-05

## API / Data Connections

- Provided on 2026-05-05:
  - DART key stored locally in ignored `.env` as `SEF_DART_API_KEY`.
  - SEC User-Agent stored locally in ignored `.env` as `SEF_SEC_USER_AGENT`.
- Decide which source to implement first for automatic fundamentals:
  - DART/OpenDART for Korean filings and financial statements.
  - Naver Finance-style summary data if a stable allowed path is chosen.
  - yfinance for US tickers and some market data.
- Optional macro/earnings keys if you want those connected later.

## Screener Policy

- Confirm whether the current conservative defaults are acceptable:
  - PER <= 25
  - PBR <= 4
  - debt/equity <= 150%
  - ROE >= 8%
  - operating margin >= 5%
  - revenue growth >= -5%
- Decide whether you want separate presets:
  - value,
  - growth,
  - dividend,
  - semiconductor/cyclical,
  - US big tech.

## Manual Data Entry

- For each serious candidate, enter or paste at least these fields:
  - PER or Forward PER,
  - PBR,
  - ROE,
  - operating margin,
  - revenue growth,
  - debt/equity,
  - source and 기준일.
- Add a research note when a candidate comes from YouTube/NotebookLM/other AI summary.
  - Include counter-points and check questions, not only bullish summary.

## Broker / Account

- Toss + Kiwoom automatic sync remains N/A.
- If the same ticker must be held in both Toss and Kiwoom ISA separately, approve a future holdings primary-key migration from `ticker` to `(account_key, ticker)`.
