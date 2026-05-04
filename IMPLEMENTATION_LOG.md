# Stock Expert Friend v1 Implementation Log

## 2026-05-03

### Initial Scope

- Read `C:/Users/kim/Downloads/Stock_Expert_Friend_v1_FINAL_spec.md` with UTF-8 encoding because the first console read showed mojibake.
- Confirmed the project is an information, alert, journal, and reflection tool, not a trade execution system.
- Chose a Python CLI-first v1 with SQLite and mock data as the reliable baseline, matching the spec's `python -m app.main --demo` requirement.
- Created the project under `F:/codex/stock_expert_friend` to avoid touching unrelated work in `F:/codex`.

### Files Created So Far

- `app/config.py`: Runtime configuration and mandatory legal disclaimer text.
- `app/models.py`: Pydantic models for holdings, portfolio snapshots, prices, events, macro snapshots, decisions, LLM assist output, and trade journal entries.
- `app/db/schema.sql`: SQLite schema for holdings, trades, alert logs, collection logs, trigger events, rule-limit changes, and LLM call logs.
- `app/db/database.py`: Small SQLite connection and schema initialization helper.

### Design Notes

- LLM assist models intentionally do not include `action` or `max_amount_krw`; those fields live only on the rule-engine decision model.
- The buy-review input uses `price_type` rather than execution language, keeping the project away from trading-system semantics while still allowing the rule engine to block market-style requests.

### Adapter and Engine Implementation

- Added data adapter modules under `app/data`.
- Implemented mock prices, macro indicators, event calendar, news headlines, and filings placeholders.
- Added SQLite-backed portfolio storage and demo seeding for QQQ, SMH, AAPL, AMD, and MVST.
- Implemented rule engines for:
  - portfolio concentration and cash limits,
  - earnings-window checks,
  - overconfidence language detection,
  - QQQ/SMH core ETF rules,
  - deterministic red-team bear cases,
  - buy-review mode,
  - macro-event trigger detection and explanation.

### CLI and User-Facing Flow

- Added `app/main.py` with:
  - `--demo`,
  - `--init-db`,
  - `--buy-check`.
- The demo flow creates mock collection logs, seeds a portfolio, adds one 1-week-old demo trade, generates both daily briefings, runs QQQ/SMH rules, runs an AMD buy check, explains macro triggers, and prints a monthly report.
- Added `README.md`, `.env.example`, `requirements.txt`, and `pyproject.toml`.

### Safety Notes

- No trade-execution integration was implemented.
- Telegram support is notification-only. If no Telegram credentials are set, the same message is printed to console.
- KIS was initially present only as a read-adapter placeholder and was not used in the demo path.

### First Verification Pass

- `py -3 -m pytest` passed: 20 tests.
- First `py -3 -m app.main --demo` run correctly failed on the LLM-output source-link guard because the mock briefing tried to classify a high-volatility ticker with no sourced headline.
- Fixed `morning_briefing.py` so conditional headline classification only runs for tickers that have sourced mock headlines. This preserves the spec rule that sourced claims are required instead of filling gaps with unsourced text.
- Second demo run reached final printing, then failed on Windows console encoding for the warning symbol. Replaced the symbol with `[!]` and configured `stdout` as UTF-8 in the CLI entrypoint.

### Final Verification Pass

- Ran `py -3 -m pytest -p no:cacheprovider` with `PYTHONDONTWRITEBYTECODE=1`: 20 tests passed.
- Ran `py -3 -m app.main --demo` with `PYTHONDONTWRITEBYTECODE=1`: demo completed successfully.
- Removed generated runtime artifacts after verification: `__pycache__`, `.pytest_cache`, and `demo_stock_expert_friend.sqlite3`.

### Remaining Explicitly Mocked Areas

- FRED, ECOS, OpenDART, SEC EDGAR, RSS, and Telegram production paths are adapter boundaries or notification stubs, not fully credentialed integrations.
- APScheduler is listed in requirements for deployment scheduling, but the local v1 demo exposes script entrypoints instead of installing a long-running scheduler process.
- LLM calls are represented by `DeterministicAnalyst` and the output filter. This keeps tests deterministic and preserves the rule-engine/LLM separation until real API keys are configured.

## 2026-05-03 Addendum Specs

### Specs Applied

- Read `C:/Users/kim/Downloads/RULE_POST_DROP_CHASE_SPEC.md`.
- Read `C:/Users/kim/Downloads/BACKTEST_HARNESS_SPEC.md`.

### post_drop_chase Implementation

- Added conservative config defaults:
  - single buy cap lowered to 1,000,000 KRW,
  - daily buy cap lowered to 3,000,000 KRW,
  - theme cap lowered to 35%,
  - minimum cash raised to 10,000,000 KRW,
  - post-drop parameters from the spec.
- Added `app/rules/post_drop_chase.py` with `RULE_ID = "post_drop_chase"` and `RULE_VERSION = "post_drop_v1.0"`.
- Added `PriceHistoryBar` and `PostDropContext` models.
- Reused `CORE_ETF_WHITELIST` from `app/engines/core_etf_rules.py`.
- Integrated the post-drop rule into `review_buy_request`.
- Added `post_drop_context` to `AlertDecision`.
- Added rule/severity logging fields to `alert_logs`.
- Added 14 rule tests in `tests/rules/test_post_drop_chase.py`.

### Backtest Harness Implementation

- Added schema tables:
  - `holdings_snapshot`,
  - `price_history`,
  - `earnings_calendar_history`,
  - `rule_version_log`,
  - `backtest_run`,
  - `backtest_verdict`.
- Added `app/data/price_history.py` with cache-first price history access and yfinance best-effort reconstruction.
- Added `app/backtest/context.py`, `app/backtest/replay.py`, and `app/backtest/report.py`.
- Added CLI:
  - `py -3 -m app.main --backtest --since YYYY-MM-DD --until YYYY-MM-DD --mode strict|reconstruct --rule-version current`
- Added 7 replay tests in `tests/backtest/test_replay.py`.

### 사전에 없는 임의 결정

- 결정 항목: `BACKTEST_HARNESS_SPEC.md` assumes a `trade_journal` table with `decision_at`, `action_taken`, and `amount_krw`, while the existing v1 project stores journal rows in `trades` with `timestamp`, `action`, `quantity`, and `avg_price`.
  - 선택한 옵션: Backtest loader supports both schemas. If `trade_journal` exists, it uses that. Otherwise it maps existing `trades` rows into replay trades.
  - 검토한 다른 옵션: Rename or alter the existing `trades` table.
  - 선택 사유: Existing table modification would be riskier and conflict with the spec's "do not modify original tables" principle.
- 결정 항목: Existing `trades` rows do not store `amount_krw`.
  - 선택한 옵션: Compute `amount_krw = quantity * avg_price * config.fx_usd_krw` for the compatibility path.
  - 검토한 다른 옵션: Skip all existing `trades` rows during backtest.
  - 선택 사유: Skipping would make the harness unusable for data already collected by this v1 project.
- 결정 항목: `holdings_snapshot` does not include cash, while the live rule engine requires cash-floor context.
  - 선택한 옵션: Reconstructed snapshot portfolios assume cash equal to `min_cash_krw + trade.amount_krw`.
  - 검토한 다른 옵션: Treat cash as zero, which makes most historical replay verdicts cash-floor blocks.
  - 선택 사유: The snapshot schema cannot express cash; this conservative assumption prevents an unrelated cash rule from overwhelming the replay.
- 결정 항목: `rule_version` comparison behavior is specified but not mapped to concrete parameter sets.
  - 선택한 옵션: `current` uses all current rules; `legacy_no_post_drop` and `post_drop_off` disable only `post_drop_chase`.
  - 검토한 다른 옵션: Require populated `rule_version_log` before replay.
  - 선택 사유: The spec requires rule-version comparison tests in v1; this gives a deterministic baseline without inventing a full version-management UI.
- 결정 항목: yfinance retry library.
  - 선택한 옵션: Implemented five retry attempts directly and listed `tenacity` in requirements for later production hardening.
  - 검토한 다른 옵션: Import `tenacity` directly in runtime code.
  - 선택 사유: The local environment did not have all optional packages; direct retry keeps tests deterministic.

### Verification After Addendum

- `py -3 -m pytest -p no:cacheprovider` passed: 41 tests.
- `py -3 -m app.main --demo` completed successfully after the addendum changes.
- A previous parallel verification attempt timed out on the demo process while tests were also running; the same demo command passed when run alone.

## 2026-05-03 Operational Input Step

### Implemented

- Added `watchlist` table to SQLite schema.
- Added `WatchlistStore` for add/update, remove, and list operations.
- Extended `PortfolioStore`:
  - delete holding,
  - save current holdings snapshot into `holdings_snapshot`.
- Added operational CLI commands:
  - `--set-cash`,
  - `--add-holding`,
  - `--remove-holding`,
  - `--list-portfolio`,
  - `--snapshot-holdings`,
  - `--record-trade`,
  - `--list-trades`,
  - `--watch-add`,
  - `--watch-remove`,
  - `--watch-list`.
- Added tests in `tests/test_operational_cli.py`.
- Updated README with operational input examples.

### Verification

- `py -3 -m pytest -p no:cacheprovider` passed: 44 tests.
- Initial smoke run sent three CLI commands to the same SQLite file in parallel and one process hit `database is locked`.
- Increased SQLite connection timeout and `busy_timeout` to 30 seconds. Normal CLI usage is sequential, but this makes brief concurrent access less brittle.
- Sequential smoke run completed:
  - set cash,
  - add holding,
  - add watch item,
  - list portfolio,
  - list watchlist,
  - record trade,
  - list trades,
  - snapshot holdings.
- Final `py -3 -m pytest -p no:cacheprovider` passed: 44 tests.

## 2026-05-03 Local Web UI Step

### Implemented

- Added `app/web_ui.py`, a Python standard-library local web UI using `ThreadingHTTPServer`.
- Added `--web`, `--host`, and `--port` CLI flags.
- UI supports:
  - portfolio overview,
  - cash entry,
  - holding entry,
  - watchlist entry,
  - trade journal entry,
  - buy-check rule review,
  - recent journal display.
- Added `tests/test_web_ui.py`.
- Updated README with local UI instructions.

### Verification

- `py -3 -m pytest -p no:cacheprovider` passed: 45 tests.

## 2026-05-03 Score Guide UI Step

### Instruction Check

- Read `F:/codex/AGENTS.md` and `F:/codex/agents.md` before continuing this step.
- Confirmed the relevant workspace rules: keep changes minimal, check worktree, preserve unrelated changes, and verify focused tests before broader checks.

### Implemented

- Added an on-screen score guide next to the buy-check form.
- Added the same guide below the trade journal form.
- The guide explains how to choose `FOMO` and external influence scores from 0 to 10.
- Added responsive CSS so the guide appears to the right on desktop and below the form on narrow screens.

### Verification

- Updated `tests/test_web_ui.py` to assert the score guide renders.
- `py -3 -m pytest -p no:cacheprovider tests/test_web_ui.py` passed.
- `py -3 -m pytest -p no:cacheprovider` passed: 45 tests.
- Restarted the local web UI at `http://127.0.0.1:8766`; HTTP 200 confirmed and rendered HTML contains `점수 입력 기준`.

## 2026-05-03 Rule Engine Explainability UI Step

### User Request

- User said the rule engine meaning was not clear and the UI should show information/context.
- User also requested future plans include:
  - what we are implementing,
  - progress,
  - next steps.

### Implemented

- Added `룰엔진이 보는 정보` panel to the dashboard.
- Added current input data summary:
  - manual portfolio source,
  - recent BUY trade count,
  - mock event-calendar note,
  - price-history limitation note,
  - news/filings limitation note.
- Added conservative limit table:
  - single buy cap,
  - daily buy cap,
  - cash floor,
  - single-position cap,
  - theme cap.
- Added rule-engine flow explanation.
- Added `룰엔진 판단 기준` table with action meanings and main rules.
- Added result-reading note below buy-check output.

### Verification

- `py -3 -m pytest -p no:cacheprovider tests/test_web_ui.py` passed.
- `py -3 -m pytest -p no:cacheprovider` passed: 45 tests.
- Restarted local UI at `http://127.0.0.1:8766`; HTTP 200 confirmed and rendered HTML contains both `룰엔진이 보는 정보` and `룰엔진 판단 기준`.

### News Integration Note

- User asked whether the rule engine can reflect newly released news.
- Current answer: not yet. The current rule engine uses structured inputs only: portfolio, cash, recent trades, mock events, FOMO, external influence, and optional price history.
- Recommended next implementation: collect news as sourced context and warning flags, not as direct buy/sell decision authority.

## 2026-05-03 Recent Info Update Step

### Implemented

- Added `news_headlines` table.
- Added `NewsStore` and `GoogleNewsRssCollector`.
- Added Yahoo chart API fallback in `PriceHistoryStore` when `yfinance` is not installed.
- Added `최근 정보` panel to the web UI.
- Added web buttons:
  - `가격 업데이트`,
  - `뉴스 업데이트`.
- Price update fetches recent history for holdings/watchlist tickers, stores it in `price_history`, and refreshes holding current prices from the latest close.
- News update fetches Google News RSS for holdings/watchlist tickers and stores sourced headlines.
- Updated FOMO/external influence guide to state that these are self-recording fields, not foolproof enforcement.

### Safety Design

- News is not allowed to directly decide buy/sell actions.
- News is displayed as sourced context only; rule-engine decisions remain structured and conservative.

### Verification

- `py -3 -m pytest -p no:cacheprovider tests/test_web_ui.py tests/test_market_info_update.py` passed.
- `py -3 -m pytest -p no:cacheprovider` passed: 47 tests.
- Restarted local UI at `http://127.0.0.1:8770`; HTTP 200 confirmed and rendered HTML contains `최근 정보` and `뉴스 업데이트`.

### 사전에 없는 임의 결정

- 결정 항목: 관심종목 schema details were not specified in the original v1 spec.
  - 선택한 옵션: `watchlist(ticker, market, reason, priority, sector_tag, created_at, updated_at)`.
  - 검토한 다른 옵션: Reuse holdings table for watch items.
  - 선택 사유: Watchlist items are not positions and should not affect portfolio risk calculations.
- 결정 항목: Backtest snapshot creation from current holdings.
  - 선택한 옵션: `--snapshot-holdings` stores one row per holding in `holdings_snapshot`.
  - 검토한 다른 옵션: Automatically snapshot on every holding edit.
  - 선택 사유: Manual snapshot avoids clutter and makes the user choose meaningful baseline points.

## 2026-05-03 Self-Report Guard and News Context Step

### User Request

- User asked why `FOMO` and external influence matter if the user can simply lie and enter a lower score.
- User also asked that future progress always show:
  - what is being implemented,
  - implementation progress,
  - next process.

### Implemented

- Added `app/engines/self_report_check.py`.
- Added `입력 점수-사유 불일치` detection to the buy-check rule engine.
- If `FOMO` is low but the reason includes urgent language such as `놓치`, `후회`, `오늘`, or `지금 안`, the rule engine can add a 24-hour wait blocker.
- If external influence is low but the reason includes external-source cues such as `유튜브`, `커뮤니티`, `추천`, `친구`, or `텔레그램`, the rule engine can require score re-entry and review.
- Added `app/engines/news_flags.py`.
- Added headline flagging for:
  - earnings/guidance,
  - legal/regulatory,
  - analyst/price target,
  - financing/dilution,
  - momentum/overheating.
- Connected cached `price_history` to web buy-check calls so `post_drop_chase` can use stored price data.
- Connected cached news headlines to web buy-check result messages under `[최근 정보]`.
- Updated the UI score guide and rule context panel to explain:
  - score fields are self-recording fields,
  - mismatch warnings exist,
  - price history and news context are now connected,
  - public filings automation is still not implemented.

### Verification

- `py -3 -m py_compile app\engines\self_report_check.py app\engines\news_flags.py app\engines\buy_check_mode.py app\web_ui.py` passed.
- `py -3 -m pytest -p no:cacheprovider tests\test_buy_check_mode.py tests\test_news_flags.py tests\test_market_info_update.py tests\test_web_ui.py` passed: 13 tests.
- Full regression after this step passed: `py -3 -m pytest -p no:cacheprovider -vv` passed 52 tests.
- Restarted the local UI at `http://127.0.0.1:8770`; HTTP 200 confirmed.
- Rendered HTML now contains `최근 정보`, `뉴스/RSS`, `주의 플래그`, and `불일치 경고나 대기`.

### Design Boundary

- This does not make self-reporting tamper-proof.
- The design intentionally creates friction, accountability, and reviewable records instead of pretending the program can read the user's mind.
- News remains context, not a direct buy/sell decision authority.

## 2026-05-03 SEC Filing Context Step

### Implemented

- Added `sec_filings` table.
- Expanded `app/data/filings_collector.py` with:
  - `FilingStore`,
  - `SecFilingsCollector`,
  - ticker-to-CIK lookup from SEC's company ticker JSON,
  - submissions JSON parsing from `data.sec.gov/submissions/CIK##########.json`,
  - archive document URL generation.
- The collector stores only major filing types for v1:
  - `8-K`,
  - `10-Q`,
  - `10-K`,
  - `S-1`,
  - `S-3`,
  - `424B`,
  - `424B5`,
  - `DEF 14A`.
- Added the web UI `공시 업데이트` button.
- Added `최근 SEC 공시` to the `최근 정보` panel.
- Added ticker-specific SEC filing context to the web buy-check result message.
- Updated README with `SEF_SEC_USER_AGENT` guidance.

### Official Source Check

- Used SEC's EDGAR API documentation as the source for the submissions endpoint and no-auth JSON API behavior.
- Used SEC's EDGAR data access page as the source for `company_tickers.json`.

### Verification

- `py -3 -m pytest -p no:cacheprovider tests\test_filings_collector.py tests\test_market_info_update.py tests\test_web_ui.py` passed: 6 tests.
- Full regression after this step passed: `py -3 -m pytest -p no:cacheprovider -vv` passed 54 tests.
- Restarted the local UI at `http://127.0.0.1:8770`; HTTP 200 confirmed.
- Rendered HTML now contains `공시 업데이트`, `최근 SEC 공시`, `SEC 공시`, and `최근 정보`.

### Design Boundary

- SEC filings are used as context, not a direct trade decision input.
- The UI does not parse full filing content yet; it lists recent filing types, dates, descriptions, and SEC links.
- Real earnings calendar automation is still separate and not implemented in this step.

## 2026-05-03 Earnings Calendar and Optional Research Notes Step

### User Request

- User approved continuing to the next step.
- User asked whether NotebookLM or trusted YouTube channels such as `김지윤의 지식플레이` can be included as analysis data, and asked to consider pros/cons and make it optional if ambiguous.

### Implemented

- Added DB columns to `earnings_calendar_history`:
  - `source_url`,
  - `note`.
- Added `external_research_notes` table.
- Added `app/data/earnings_calendar_store.py`.
- Added `app/data/research_notes_store.py`.
- Changed web buy-check to use DB-backed earnings events instead of `MockEventCalendar`.
- Changed CLI buy-check to use DB-backed earnings events.
- Added UI section `실적 일정`:
  - ticker,
  - earnings date,
  - source,
  - source URL,
  - note.
- Added UI section `외부 리서치 노트`:
  - tickers,
  - source type (`NOTEBOOKLM`, `YOUTUBE`, `ARTICLE`, `USER_NOTE`),
  - reliability,
  - source name,
  - source URL,
  - summary.
- Added ticker-specific research notes to web buy-check result messages.

### Design Decision

- NotebookLM/YouTube/article summaries are allowed only as optional research context.
- They do not modify `NO_TRADE`, `WATCH`, or `SMALL_BUY_CANDIDATE`.
- Rationale:
  - Pros: useful for macro, geopolitics, industry context, and reviewable notes.
  - Cons: second-hand interpretation can be biased, stale, or overconfident.
  - Therefore they are saved and displayed, but not treated as rule-engine evidence.

### Verification

- `py -3 -m py_compile app\data\earnings_calendar_store.py app\data\research_notes_store.py app\web_ui.py app\main.py` passed.
- `py -3 -m pytest -p no:cacheprovider tests\test_earnings_calendar_store.py tests\test_research_notes_store.py tests\test_market_info_update.py tests\test_web_ui.py` passed: 7 tests.
- Full regression after this step passed: `py -3 -m pytest -p no:cacheprovider -vv` passed 57 tests.
- Restarted the local UI at `http://127.0.0.1:8770`; HTTP 200 confirmed.
- Rendered HTML now contains `실적 일정`, `외부 리서치 노트`, `NOTEBOOKLM`, and `DB에 저장한 실적일`.

## 2026-05-03 Non-API Completion Prep Step

### User Request

- User asked to keep progressing and leave only API connection work for tomorrow.

### Implemented

- Added `app/data/data_status.py`.
- Added `데이터 상태` panel to the web UI:
  - latest price date,
  - latest news collection date,
  - latest SEC filing date,
  - next stored earnings date,
  - research note count,
  - freshness label.
- Added `API 연결 준비 상태` panel to the web UI:
  - price,
  - news,
  - SEC filings,
  - earnings calendar,
  - macro indicators,
  - domestic filings,
  - broker synchronization.
- Added `counter_points` and `check_questions` columns to `external_research_notes`.
- Added migration guards for those new research-note columns.
- Updated the research note UI to collect:
  - summary,
  - counterpoints,
  - verification questions.
- Updated buy-check result context to include:
  - research counterpoints,
  - research verification questions,
  - ticker data status.

### Design Boundary

- No new credentialed API connection was added in this step.
- API readiness checks only inspect local environment variables and display next steps.
- This keeps tomorrow's work focused on adding keys/providers rather than changing UI/data structure.

### Verification

- `py -3 -m py_compile app\data\data_status.py app\data\research_notes_store.py app\web_ui.py app\db\database.py` passed.
- `py -3 -m pytest -p no:cacheprovider tests\test_data_status.py tests\test_research_notes_store.py tests\test_market_info_update.py tests\test_web_ui.py` passed: 8 tests.
- Full regression after this step passed: `py -3 -m pytest -p no:cacheprovider -vv` passed 59 tests.
- Restarted the local UI at `http://127.0.0.1:8770`; HTTP 200 confirmed.
- Rendered HTML now contains `데이터 상태`, `API 연결 준비 상태`, `반대근거`, `확인질문`, and `내일 연결`.

## 2026-05-03 Broker Account Routing Step

### User Request

- User said they will use Toss for normal investing and Kiwoom for ISA, and asked whether that can be reflected.

### Implemented

- Added `broker_accounts` table.
- Added `app/data/account_store.py`.
- Added default local account preferences:
  - `GENERAL_TOSS`: `토스증권`, general trading/US stocks,
  - `ISA_KIWOOM`: `키움증권`, ISA account.
- Added web UI `계좌 설정` section.
- Added `기본값 저장: 일반 토스 / ISA 키움` button.
- Added buy-check account selector:
  - `일반 - 토스증권`,
  - `ISA - 키움증권`.
- Added account-routing text to buy-check result messages.
- Seeded the current local DB with `GENERAL_TOSS` and `ISA_KIWOOM`.

### Design Boundary

- This is not a broker API integration.
- The current holdings table is still ticker-level, so the same ticker cannot yet be split across Toss and Kiwoom ISA as separate position rows.
- Next account-aware portfolio step should introduce account-level holding lots before connecting broker APIs.

### Verification

- `py -3 -m py_compile app\data\account_store.py app\web_ui.py` passed.
- `py -3 -m pytest -p no:cacheprovider tests\test_account_store.py tests\test_market_info_update.py tests\test_web_ui.py` passed: 8 tests.
- Full regression after this step passed: `py -3 -m pytest -p no:cacheprovider -vv` passed 62 tests.
- Restarted the local UI at `http://127.0.0.1:8770`; HTTP 200 confirmed.
- Rendered HTML now contains `계좌 설정`, `토스증권`, `키움증권`, and `ISA - 키움증권`.

## 2026-05-03 Broker Decision Checkpoint

### User Decision Confirmed

- Use Toss Securities for the normal/general account.
- Use Kiwoom Securities for the ISA account.
- Remove or disable the KIS adapter.
- Automatic broker synchronization is N/A.
- Portfolio inputs remain manual.
- Need to add account-aware fields to `holdings` and `trades` tomorrow after confirming schema impact.

### Confirmed Current State

- Removed `app/data/kis_price_provider.py`.
- Updated API readiness text from `브로커/KIS` to `브로커 동기화: N/A`.
- No runtime code imports or calls KIS after this cleanup.
- `broker_accounts` exists and currently stores account routing preferences.
- `holdings` currently has no `broker`, `account_type`, or `account_key` field.
- `trades` currently has no `broker`, `account_type`, or `account_key` field.
- Full regression after this checkpoint passed: `py -3 -m pytest -p no:cacheprovider -vv` passed 62 tests.

### Tomorrow Work

- Add `account_key` to `holdings` and `trades`.
- Consider changing `holdings` primary key from `ticker` to `(account_key, ticker)` or introducing a new account-aware holdings table.
- Keep all portfolio updates manual; do not add Toss/Kiwoom automatic sync.

## 2026-05-04 Samsung/Hynix False-Block Prevention Rules

### User Request

- User said today's rules told them not to buy Samsung Electronics and SK Hynix and they felt roughly 10% opportunity loss.
- User provided three specs:
  - `RULE_POST_RUN_DECOMPOSITION_SPEC.md`
  - `RULE_DECISION_PROTECTION_SPEC.md`
  - `RULE_TICKER_SENSITIVITY_AND_HOLIDAY_GAP_SPEC.md`
- Goal: prevent a future AI/rule engine from over-blocking explainable semiconductor moves, while still protecting against FOMO and regret chasing.

### Assumptions / Ambiguity Check

- `CLAUDE.md` was requested by the spec but not found under `F:\codex` or the project folder, so the active `AGENTS.md` harness was used.
- The user previously asked to leave API connection work for tomorrow, so this step did not add credentialed live API connections.
- Naver foreign ownership crawling, DART automation, and live yfinance correlation refresh are left as API/provider work.
- The current implementation uses manual or cached local DB data for sensitivity, price, news, and market proxies.

### Implemented

- Added `ticker_sensitivity` and `foreign_ownership_history` schema.
- Added `app/data/ticker_sensitivity.py`.
- Added `app/rules/holiday_gap_setup.py`.
  - High-risk example covered: Hynix-like foreign ownership 53%, US sector correlation 0.78, US accumulated gain 2% over a 3-day domestic gap => high severity, 70% cap.
  - Low-risk example covered: low foreign ownership and low US sector correlation => no cap.
- Added `app/rules/post_run_decomposition.py`.
  - Decomposes recent runs into KOSPI beta, US sector relative move, and news-explained return.
  - Caps only the unexplained residual run-up.
- Added `app/rules/post_run_news_mapping.py`.
  - Conservative keyword mapping for earnings surprise, policy, large contract, deregulation, competitor bad news, analyst target upgrade.
- Added `app/rules/decision_protection.py`.
  - Observation blackout lookup and suggestion.
  - Regret-chase detection from buy-check logs and latest cached price.
- Added `buy_check_log` and `conditional_decisions` schema.
- Added `app/data/buy_check_log.py`.
- Added `app/data/conditional_orders.py`.
- Extended `watchlist` with `do_not_watch_until`, `blackout_reason`, and `blackout_set_at`.
- Integrated new contexts into `AlertDecision`:
  - `ticker_sensitivity_used`
  - `holiday_gap_signal`
  - `relative_weakness_signal`
  - `post_run_decomposition`
  - `blackout_suggested`
  - `regret_pattern`
- Integrated new rules into `review_buy_request`.
  - Active blackout blocks a buy-check and hides price-based rule details.
  - Holiday gap and post-run decomposition adjust max buy amount by cap ratio instead of blindly blocking.
  - Regret-chase pattern blocks a new buy-check when a recent NO_TRADE/WATCH was followed by a large price jump.
- Added buy-check logging from CLI and web UI.
- Added CLI:
  - `--sensitivity-set`
  - `--sensitivity-list`
  - `--blackout-set`
  - `--blackout-clear`
  - `--conditional-add`
  - `--conditional-list`
- Added web UI panels:
  - `종목 민감도 / 연휴 갭`
  - `결정 보호`
  - sensitivity form/table
  - blackout form
  - conditional decision form/table
- Updated decision messages to show sensitivity, holiday gap, relative weakness, post-run decomposition, regret chase, and blackout suggestion context.

### Operating Rule

- These three new rules must not turn every missed rally into permission to chase.
- They exist to separate:
  - explainable market/sector/news repricing,
  - unexplained momentum chasing,
  - and user regret after a previous no-trade decision.
- If sensitivity/news/market data is missing, the system marks completeness as partial instead of pretending the signal is complete.

### Verification

- `py -3 -m compileall -q app` passed.
- New focused tests passed: `py -3 -m pytest tests\rules\test_holiday_gap_setup.py tests\rules\test_post_run_decomposition.py tests\rules\test_decision_protection.py tests\test_ticker_sensitivity_store.py -p no:cacheprovider` passed 11 tests.
- Full regression passed: `py -3 -m pytest -p no:cacheprovider` passed 73 tests.

## 2026-05-04 KR Holiday Guard and Semiconductor Estimates

### User Request

- User asked to continue after the Samsung Electronics / SK Hynix rule simulation.
- The simulation showed a gap: May 5, 2026 is a Korean market holiday, but buy-check did not clearly separate "market closed" from investment risk.

### Implemented

- Added `app/data/market_calendar.py`.
- Added KRX 2026 holiday guard for buy-check.
- KR tickers ending in `.KS` or `.KQ` are treated as Korean market tickers even if the request market is omitted.
- If a KR buy-check is run on a KRX holiday or weekend, the result is operational `NO_TRADE` with a next-open-date note.
- Added CLI seed:
  - `py -3 -m app.main --seed-kr-semiconductor-sensitivity`
- Added web UI button:
  - `삼성전자/하이닉스 추정 민감도 저장`
- Added Samsung Electronics and SK Hynix estimated sensitivity starter rows:
  - `005930.KS`: SMH proxy, foreign ownership 55%, sector correlation 0.65, KOSPI beta 1.0
  - `000660.KS`: SMH proxy, foreign ownership 53%, sector correlation 0.78, KOSPI beta 1.2

### 사전 스펙에 없는 임의 결정

- Background: The user asked for a quick Samsung Electronics / SK Hynix simulation and then asked to continue.
- Cause: No live foreign-ownership/correlation API is connected yet, but the UI needed a convenient way to start simulation.
- Change: The seed command/button now stores these rows as estimated starter values, not observed values. `foreign_ownership_taken_at` and `corr_taken_at` stay empty.
- Operating rule: Treat seeded values as conservative simulation inputs only. Replace them with checked values before treating holiday-gap output as complete.
- Verification: Tests assert that seeded semiconductor estimates are not marked observed.

### Operating Rule

- Market-closed `NO_TRADE` is not a bearish signal.
- It only means the rule engine should not present the result as an actionable same-day trade.
- On the next open date, run buy-check again with updated price/news/foreign-ownership data.

### Verification

- Added focused tests for KRX Children's Day closure and KR buy-check holiday blocking.
- Added test for Samsung/Hynix estimated sensitivity seeding.
- Focused tests passed: `py -3 -m pytest tests\test_market_calendar.py tests\test_ticker_sensitivity_store.py tests\test_buy_check_mode.py tests\test_web_ui.py -p no:cacheprovider` passed 12 tests.
- Full regression passed: `py -3 -m pytest -p no:cacheprovider` passed 76 tests.
- Seeded the current local DB with Samsung Electronics and SK Hynix estimated sensitivity rows.
- Restarted the local UI at `http://127.0.0.1:8770`; HTTP 200 confirmed and the page contains the seed button plus `005930.KS` / `000660.KS`.
