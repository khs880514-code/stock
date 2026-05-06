# Stock Expert Friend v1 Implementation Log

## 2026-05-06 Automatic Candidate Shortlist

### Background

- User clarified that the candidate screen should not require manual financial input before useful candidates appear.
- Desired daily flow is to collect 10-30 review candidates from today's market/news context, then compare and review them before any buy-check.

### Cause

- The previous `3 Candidate Screener` screen still centered on manual/DART/market-summary input forms.
- That made the tool feel like a data-entry screen instead of a shortlist generator for a beginner user.

### Change

- Added `app/data/review_universe.py` with a curated 28-name review universe covering Korean large caps, US mega-cap tech, semiconductors, and ETF exposure.
- Added an automatic candidate collection action for 10, 20, or 30 names.
- The automatic action refreshes market/fundamental summaries through the existing market-data path and collects Google News RSS items for those tickers.
- Added `/auto-candidates` handling in the web UI.
- Moved the long manual financial-entry controls under an expandable `Direct input / advanced collection` panel.
- Kept candidate output as a review shortlist, not a buy recommendation.

### Arbitrary Decisions Not In Prior Spec

- Used a curated first-pass universe instead of a full KRX/Nasdaq market scan. Full-market screening needs a stable data provider, rate-limit policy, and better source metadata before it is safe for daily beginner use.
- Chose 20 names as the default because it sits inside the user's requested 10-30 range and is small enough to review manually.
- Continued using yfinance/Yahoo-style market data and Google News RSS. These are delayed/convenience sources, not broker-grade real-time quotes.
- Treated generated candidates as `review candidates`; they must still go through information freshness checks, portfolio exposure checks, and buy-check before action.

### Operating Rule

- The candidate tab should first help the user create a shortlist automatically.
- Manual financial entry remains available only as an advanced correction/enrichment path.
- A shortlist entry must never be interpreted as permission to buy.

### Verification

- Compile check passed: `py -3 -m compileall -q app tests`.
- Focused tests passed: `py -3 -m pytest tests\test_review_universe.py tests\test_fundamentals_screener.py tests\test_web_ui.py tests\test_file_size_guard.py -q -p no:cacheprovider` passed 9 tests.
- Full regression passed: `py -3 -m pytest -q -p no:cacheprovider` passed 94 tests.
- Restarted the local UI at `http://127.0.0.1:8770`; in-app browser checks confirmed the candidate tab shows automatic candidate collection, today candidate auto collect, 20-name default, and the advanced manual-entry disclosure.

## 2026-05-06 Beginner Candidate Explanation

### Background

- User agreed to proceed with making candidate results explain why a ticker appears instead of showing only raw metrics and scores.
- Beginner workflow needs immediate guidance on what to look at next after an automatic candidate list is generated.

### Cause

- Candidate rows had score, raw reason strings, missing fields, and linked counts, but did not translate them into a beginner-friendly interpretation.
- Users could still read `PASS` or high score as a buy signal unless the table itself explained the next step.

### Change

- Added `app/web/candidate_explainer.py` to convert existing screener output into:
  - one-line reason,
  - next action,
  - beginner review questions.
- Added a `One-line interpretation` column to the candidate result table.
- Added a `Beginner interpretation` box inside each candidate detail card.
- Kept the stock-screener scoring and rule-engine logic unchanged.

### Arbitrary Decisions Not In Prior Spec

- Explanations use broad categories such as valuation burden, profitability, debt burden, growth, and price trend instead of rewriting every metric formula in the table. This keeps the candidate screen readable.
- The next action always routes real decisions toward information refresh, external research, or `4 Buy-check`; it never says to buy.

### Operating Rule

- Candidate screens should explain what a row means and what the user should check next.
- Explanation text is display guidance only; it must not change scores, statuses, or rule-engine outcomes.

### Verification

- Compile check passed: `py -3 -m compileall -q app tests`.
- Focused tests passed: `py -3 -m pytest tests\test_candidate_explainer.py tests\test_fundamentals_screener.py tests\test_file_size_guard.py -q -p no:cacheprovider` passed 7 tests.
- Full regression passed: `py -3 -m pytest -q -p no:cacheprovider` passed 96 tests.
- Restarted the local UI at `http://127.0.0.1:8770`; in-app browser checks confirmed `one-line interpretation`, `next action`, `4 buy-check`, and detail-card beginner interpretation text render in the candidate tab.

## 2026-05-05 API Key Readiness

### Background

- User provided a DART API key and SEC User-Agent and asked whether those values are enough.

### Cause

- The app checked `os.environ`, but local `.env` values were not loaded automatically.
- `.env.example` still had older non-`SEF_` variable names for some data providers.

### Change

- Added a minimal standard-library `.env` loader in `app/config.py`.
- Updated `.env.example` to use the app's actual environment variable names:
  - `SEF_DART_API_KEY`
  - `SEF_SEC_USER_AGENT`
  - `SEF_ALPHA_VANTAGE_API_KEY`
  - `SEF_FRED_API_KEY`
  - `SEF_ECOS_API_KEY`
  - `SEF_FINNHUB_API_KEY`
- Stored the provided values only in local ignored `.env`.
- Updated `USER_INPUT_NEEDED.md` so DART and SEC readiness are no longer listed as missing.

### Operating Rule

- Never commit real API keys or email-bearing User-Agent values.
- Keep `.env` ignored and commit only `.env.example` placeholders.
- DART/SEC readiness means credentials are available; it does not mean DART financial statement ingestion has been implemented yet.

### Verification

- Local `.env` contains only key names when inspected for logging.
- `load_config()` loads `.env`; API readiness reports SEC and domestic disclosure as ready.
- Focused test passed: `py -3 -m pytest tests\test_data_status.py -q -p no:cacheprovider` passed 3 tests.

## 2026-05-05 Candidate Detail Review and User Inputs

### Background

- User asked Codex to proceed with whatever can be done and request only the parts the user must handle.
- The app already had candidate screening, but the candidate row did not yet provide a compact detail review surface.

### Cause

- A candidate list alone still forces the user to mentally combine valuation, profitability, growth, stability, momentum, news, filings, and research notes.
- API keys and final investment policy thresholds cannot be invented safely.

### Change

- Extended `후보 발굴 / Candidate Screener` with candidate detail cards.
- Each candidate now groups available metrics into:
  - value,
  - profitability,
  - growth,
  - stability / cash flow,
  - momentum / source.
- Added automatic "next check" questions when metrics, news, filings, or research notes are missing.
- Added `USER_INPUT_NEEDED.md` for user-owned decisions:
  - API/data source choice,
  - API keys,
  - screener preset preferences,
  - required manual fields,
  - future account-level holdings migration decision.

### Operating Rule

- Candidate detail cards are review aids, not buy recommendations.
- Missing data should produce questions, not hidden confidence.
- API connection work should wait for explicit provider/key decisions.

### Verification

- Focused tests passed: `py -3 -m pytest tests\test_fundamentals_screener.py tests\test_file_size_guard.py tests\test_web_ui.py -q -p no:cacheprovider` passed 6 tests.
- Full regression passed: `py -3 -m pytest -p no:cacheprovider` passed 81 tests.
- Compile check passed after restarting the local web process: `py -3 -m compileall -q app tests`.
- Restarted the local UI at `http://127.0.0.1:8770`.
- Browser smoke passed for the `후보/정보` tab and `Candidate Screener` visibility. The current local DB had no stored fundamentals, so candidate detail cards are verified through tests and will show once candidates exist.

## 2026-05-05 Inventory-Web Split Lesson Applied

### Background

- User asked whether this app was starting to repeat the inventory-management app's old problem: too many features in one file.
- Recent inventory-web improvement history showed the useful pattern:
  - keep the top-level app file as route/shell orchestration,
  - move feature-specific panels/helpers into feature modules,
  - split large inline style blocks,
  - add verification so the split does not silently break screens.

### Cause

- `app/web_ui.py` had grown to about 1100 lines after account, research, market-info, and candidate-screener features were added.
- `app/main.py` was also large enough to watch, but not yet as urgent as the web UI container.

### Change

- Split candidate-screener web behavior into `app/web/fundamental_screener.py`.
- Split inline web CSS into `app/web/styles.py`.
- Added functional dashboard tabs through `app/web/tabs.py`:
  - dashboard,
  - candidate/info,
  - buy review,
  - portfolio,
  - research,
  - journal.
- Left `app/web_ui.py` responsible for request routing, page assembly, and shared dashboard panels.
- Added `tests/test_file_size_guard.py`:
  - `app/web_ui.py` must stay under 1100 lines.
  - `app/main.py` must stay under 750 lines.
  - individual `app/web/*.py` feature modules must stay under 350 lines.

### Operating Rule

- Do not add a new feature directly into `app/web_ui.py` unless it is only a small orchestration hook.
- New web feature panels should live under `app/web/`.
- Long dashboard sections should be assigned to a functional tab rather than appended to the bottom of the page.
- If a feature module approaches the guard limit, split panel, form, and data-prep helpers before adding more behavior.
- Before adding another large CLI feature, split `app/main.py` into command modules.

### Verification

- Initial file-size guard correctly failed when the ceiling was too low for the current state.
- The guard was adjusted to a current-state ceiling that still prevents additional unchecked growth.
- Focused tests passed after tab work: `py -3 -m pytest tests\test_file_size_guard.py tests\test_fundamentals_screener.py tests\test_web_ui.py -q -p no:cacheprovider` passed 6 tests.
- Full regression passed after tab work: `py -3 -m pytest -p no:cacheprovider` passed 81 tests.
- Restarted local UI at `http://127.0.0.1:8770`.
- Browser smoke passed: 6 tab buttons rendered, `후보/정보` tab selected, and `Candidate Screener` became visible.
- Current largest files after split:
  - `app/web_ui.py`: 945 lines.
  - `app/main.py`: 623 lines.

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

## 2026-05-05 Account-Key Manual Portfolio Step

### Background

- User previously decided to use Toss Securities for general trading and Kiwoom Securities for ISA.
- User also noted that automatic broker synchronization is N/A and all portfolio input should remain manual.
- Today the user asked to proceed as much as safely possible.

### Cause

- The app had broker account routing preferences, but `holdings` and `trades` did not persist the selected account.
- Without an account field, later Toss/Kiwoom manual reconciliation would be ambiguous.

### Change

- Added `account_key` to:
  - `holdings`
  - `trades`
  - `holdings_snapshot`
  - `Holding`
  - `TradeEntry`
- Added migration guards for those columns.
- Updated manual CLI:
  - `--add-holding --account-key ...`
  - `--record-trade --account-key ...`
  - portfolio/trade listing shows account key.
- Updated web UI:
  - holding input account selector
  - trade input account selector
  - holdings table account column
  - trades table account column.
- Preserved account key when refreshing holding current prices.

### 사전 스펙에 없는 임의 결정

- Background: The user asked to add broker/account fields, but did not explicitly approve a risky primary-key migration.
- Cause: Supporting the same ticker in both Toss and Kiwoom would require changing `holdings` from ticker-primary to account+ticker-primary, which is a larger data migration.
- Change: This step adds `account_key` as a persisted field but keeps the existing `ticker` primary key.
- Operating rule: Manual records now keep account context, but same-ticker multi-account split remains a future migration.
- Verification: Focused tests verify account keys round-trip through holdings/trades and existing backtest snapshots still work.

### Verification

- `py -3 -m compileall -q app` passed.
- Focused tests passed: `py -3 -m pytest tests\test_operational_cli.py tests\test_journal.py tests\test_web_ui.py tests\backtest\test_replay.py -p no:cacheprovider` passed 12 tests.
- Full regression passed: `py -3 -m pytest -p no:cacheprovider` passed 76 tests.
- Restarted the local UI at `http://127.0.0.1:8770`; HTTP 200 confirmed and the rendered page contains `account_key`, `GENERAL_TOSS`, `ISA_KIWOOM`, and `계좌`.
## 2026-05-05 Candidate Discovery / Fundamental Screener Step

### Background

- User asked whether the app could consider many stock-selection methods such as PER, filter objectively, produce a pure candidate list, and then attach news so the user can choose.
- The user also asked that plans show what is being implemented, progress, and next steps.

### Cause

- The app could review a buy request and display recent news/disclosures, but it did not have a first-stage candidate discovery queue.
- Without a separate screener, the workflow jumped too quickly from "interesting ticker" to buy-check.

### Change

- Added `stock_fundamentals` schema for manual/source-based fundamental snapshots.
- Added `app/data/fundamentals_store.py`.
- Added `app/engines/stock_screener.py`.
- Added CLI:
  - `--fundamental-set`
  - `--fundamental-list`
  - `--screen-stocks`
- Added web UI section:
  - `후보 발굴 / Candidate Screener`
  - manual financial metric form
  - PASS/WATCH/REJECT table
  - linked latest news, SEC filing, and research-note counts.
- Added tests for store round-trip, screener status behavior, CLI flow, web form save, and dashboard rendering.

### 사전에 없는 임의 결정

- Default v1 thresholds were selected conservatively because the user asked for a practical first filter but no exact investment-factor spec exists yet:
  - PER <= 25
  - PBR <= 4
  - debt/equity <= 150%
  - ROE >= 8%
  - operating margin >= 5%
  - revenue growth >= -5%
- Missing metrics do not silently pass. If fewer than 5 core metrics are present, the candidate remains `WATCH`.
- `PASS` means "additional review candidate", not "buy".
- No automatic fundamental-data API was added in this step. Inputs remain manual/source-based until the user approves API/provider work.

### Operating Rule

- Use screener output as the top of the research funnel:
  1. collect/save candidate fundamentals,
  2. filter into PASS/WATCH/REJECT,
  3. inspect linked news/disclosures/research notes,
  4. only then run buy-check if the user wants to review an actual purchase.
- News/disclosures/research notes provide context and questions, not automatic recommendation changes.
- Toss/Kiwoom broker sync remains N/A; portfolio and fundamentals remain manual inputs.

### Verification

- `py -3 -m compileall -q app tests` passed.
- Focused tests passed: `py -3 -m pytest tests\test_fundamentals_screener.py tests\test_web_ui.py -q -p no:cacheprovider` passed 4 tests.
- Full regression passed: `py -3 -m pytest -p no:cacheprovider` passed 79 tests.
- Restarted the local UI at `http://127.0.0.1:8770`; HTTP 200 confirmed and the rendered page contains `Candidate Screener` and the fundamental input form.
- CLI smoke passed: `py -3 -m app.main --screen-stocks` returned an empty candidate list when no fundamentals are stored.
## 2026-05-05 OpenDART Fundamentals Adapter

### Background

- User provided the DART API key and SEC User-Agent and asked to proceed with the remaining API-connection work while leaving broker sync manual.
- The candidate screener needed a non-manual path for Korean financial-statement data without turning the tool into an auto-trading system.

### Cause

- The screener could filter saved fundamentals, but Korean fundamentals still required manual entry.
- OpenDART exposes corporation code lookup through `corpCode.xml` and single-company major accounts through `fnlttSinglAcnt`, which is enough for conservative first-pass statement-derived metrics.

### Change

- Added `app/data/opendart_fundamentals.py`.
- Added OpenDART corp-code lookup, single-company major-account fetch, account parsing, and `stock_fundamentals` upsert.
- Added a Candidate Screener UI form: `OpenDART fundamentals fetch`.
- Added tests for corp-code parsing, metric mapping, persistence, and the web POST path.
- Updated `README.md` and `USER_INPUT_NEEDED.md` to show DART is now the first implemented fundamentals source.

### 사전에 없는 임의 결정

- Raw six-digit Korean tickers entered without a suffix are stored as `.KS` by default. If KOSDAQ suffix distinction matters later, add a market suffix selector before broad use.
- OpenDART `fnlttSinglAcnt` rows are mapped only to direct statement-derived metrics: revenue growth, operating-income growth, operating/net margin, ROE/ROA, and debt/equity.
- PER, PBR, market cap, dividend yield, FCF yield, and momentum remain blank because they need market-price or separate summary data.
- Consolidated financial statements (`CFS`) are preferred over separate statements (`OFS`) when both are present.

### Operating Rule

- OpenDART fills candidate fundamentals for comparison and review only.
- The app must keep showing that `PASS` means "review candidate", not "buy".
- Toss/Kiwoom broker sync remains N/A; portfolio input stays manual.

### Verification

- Focused tests passed: `py -3 -m pytest tests\test_opendart_fundamentals.py tests\test_fundamentals_screener.py tests\test_web_ui.py tests\test_file_size_guard.py -q -p no:cacheprovider` passed 9 tests.
- Compile check passed: `py -3 -m compileall -q app tests`.
- Full regression passed: `py -3 -m pytest -q -p no:cacheprovider` passed 85 tests.
- Live OpenDART smoke passed for `005930.KS` and `000660.KS` using the local ignored `.env`; no key value was printed or committed.
- Restarted the local UI at `http://127.0.0.1:8770`; HTTP 200 confirmed and the in-app browser found `OpenDART fundamentals fetch`, `005930.KS`, and `000660.KS`.

## 2026-05-05 Market Summary Fundamentals Adapter

### Background

- User pointed at the API readiness table and asked to proceed with the next planned work.
- The next blocker after OpenDART was that PER, PBR, market cap, dividend yield, FCF yield, and momentum cannot be reliably derived from DART major accounts alone.

### Cause

- Existing yfinance/Yahoo support stored price history for buy-review and post-drop rules, but it did not enrich candidate fundamentals.
- The candidate screener still had missing valuation fields after OpenDART collection.

### Change

- Added `app/data/market_fundamentals.py`.
- Added yfinance market-summary enrichment for:
  - market cap,
  - PER / forward PER,
  - PBR / PSR / EV-EBITDA,
  - dividend yield,
  - FCF yield,
  - 3M and 12M price momentum.
- Added a Candidate Screener UI form: `Market PER/PBR/momentum fetch`.
- Updated API readiness copy from pending/partial to wired for price/market summary and OpenDART.
- Added tests for market-summary mapping, DART-preserving merge behavior, momentum calculation, and the web POST path.
- Updated `README.md` and `USER_INPUT_NEEDED.md`.

### 사전에 없는 임의 결정

- Market-summary values are treated as enrichment, not as final truth. They are labeled `yfinance:summary` and the note tells the user to verify provider values before final review.
- Existing statement-derived metrics are preserved when present; market summary fills only missing statement-like values.
- USD market caps are converted to KRW using `AppConfig.fx_usd_krw`; KRW market caps are stored as-is.
- yfinance price-history refresh failure does not block summary enrichment. Momentum stays blank if usable price history is unavailable.

### Operating Rule

- Use OpenDART first for Korean financial-statement fields, then use market summary to fill valuation and momentum.
- `PASS` remains a review candidate label only, not a buy instruction.
- Toss/Kiwoom broker sync remains N/A; portfolio input stays manual.

### Verification

- Focused tests passed: `py -3 -m pytest tests\test_market_fundamentals.py tests\test_opendart_fundamentals.py tests\test_fundamentals_screener.py tests\test_web_ui.py tests\test_data_status.py tests\test_file_size_guard.py -q -p no:cacheprovider` passed 14 tests.
- Installed `requirements.txt` into the local Python environment because `yfinance` was declared but missing at runtime.
- Live yfinance smoke passed for `005930.KS` and `000660.KS`; forward PER, market cap, dividend yield, and momentum fields were saved where the provider returned them.
- Compile check passed: `py -3 -m compileall -q app tests`.
- Full regression passed: `py -3 -m pytest -q -p no:cacheprovider` passed 87 tests.
- Restarted the local UI at `http://127.0.0.1:8770`; HTTP 200 and in-app browser checks found `Market PER/PBR/momentum fetch`, `가격/시장요약`, `005930.KS`, and `000660.KS`.

## 2026-05-05 Default Test Universe Seed

### Background

- User asked to add Samsung Electronics, SK Hynix, Pearl Abyss, QQQ, SMH, AAPL, and AMD as defaults.
- User then provided current holdings screenshots and stated remaining cash is 29,000,000 KRW.
- User also wanted around 10 companies to appear when the quality-stock screener is run, specifically for testing whether the workflow works.

### Cause

- The screener could work, but a fresh/local DB might not show enough candidates to verify the flow.
- The user's default holdings and Korean candidates needed to be present, and the previously seeded zero-quantity placeholders needed to be replaced with the user-reported current portfolio.

### Change

- Added `app/data/default_universe.py`.
- Added `Seed default test universe` form to the Candidate Screener.
- The seed sets cash to 29,000,000 KRW when the current value is empty or the old 30,000,000 KRW placeholder.
- The seed adds or replaces zero-quantity placeholder holdings with user-reported positions:
  - AAPL 11 shares,
  - AMD 5 shares,
  - MVST 110 shares,
  - SMH 1 share,
  - QQQ 2 shares.
- The seed adds missing watchlist rows for:
  - Samsung Electronics,
  - SK Hynix,
  - Pearl Abyss,
  - QQQ,
  - SMH,
  - AAPL,
  - AMD,
  - MVST.
- The seed adds missing synthetic screener candidates so the quality filter returns about 10 PASS rows for test verification.

### 사전에 없는 임의 결정

- Holding average/current prices are reverse-calculated from the KRW screenshots and converted to USD using `AppConfig.fx_usd_krw` so future price refreshes keep a consistent USD structure.
- AAPL, AMD, and MVST are assigned to `GENERAL_TOSS`; QQQ and SMH are assigned to `ISA_KIWOOM`.
- Cash is updated only when the old value is empty or the old default 30,000,000 KRW placeholder to avoid overwriting later manual edits.
- Pearl Abyss is stored as `263750.KQ`.
- Candidate fundamentals are synthetic test metrics with source `seed:test-universe`; they are explicitly not recommendations.
- Existing non-placeholder holdings, watchlist items, and fundamentals are not overwritten.

### Operating Rule

- Use seeded candidates only to verify the research-funnel UI and screener mechanics.
- Verify the reverse-calculated average prices against broker detail screens before relying on tax lots or exact realized/unrealized P&L.
- Continue to treat the app as an information, logging, and review aid, not an auto-buy recommender.

### Verification

- Focused tests passed: `py -3 -m pytest tests\test_default_universe.py tests\test_fundamentals_screener.py tests\test_web_ui.py tests\test_file_size_guard.py -q -p no:cacheprovider` passed 9 tests.
- Local DB seed smoke added missing defaults without overwriting existing Samsung/SK Hynix data; current local screener shows 10 candidates and 10 PASS rows.
- Compile check passed: `py -3 -m compileall -q app tests`.
- Full regression passed: `py -3 -m pytest -q -p no:cacheprovider` passed 90 tests.
- Restarted the local UI at `http://127.0.0.1:8770`; HTTP 200 and in-app browser checks found `Seed default test universe`, `263750.KQ`, `QQQ`, `SMH`, and PASS rows.
- Updated local DB from the user screenshots: cash 29,000,000 KRW; AAPL 11, AMD 5, MVST 110, SMH 1, QQQ 2; app total value is approximately 39,207,029 KRW using the configured FX rate.
- Restarted the local UI again; HTTP 200 confirmed the page contains cash 29,000,000, MVST, AAPL, and QQQ.

## 2026-05-05 User Workflow Guide / Worker Handoff

### Background

- User asked how to interpret the current app output and what to do when the US market is open and candidate names appear.
- User also asked for a file summarizing all completed work for another worker.

### Cause

- The app now has enough screens and data sources that the workflow needs an explicit operating guide.
- `PASS` rows can be misunderstood as recommendations unless the usage sequence is documented.

### Change

- Added `HANDOFF_FOR_NEXT_WORKER.md`.
- The handoff file includes:
  - project identity,
  - current portfolio snapshot,
  - implemented features,
  - data connections,
  - daily/US-market-open usage guide,
  - FOMO/outside-influence handling,
  - next engineering steps,
  - verification commands,
  - current known risks.
- Updated `README.md` to point other workers to the handoff file.

### 사전에 없는 임의 결정

- Kept this as one comprehensive handoff file instead of scattering the guidance across multiple docs, because the user asked for a file to show another worker.
- The user workflow explicitly states `PASS` is a research candidate label, not a buy instruction.

### Operating Rule

- Other workers should read `HANDOFF_FOR_NEXT_WORKER.md` before modifying the app.
- During live market hours, the app should be used to slow down decisions, refresh context, run buy-check, and log actions, not to chase candidate rows.

### Verification

- File added and README link added.

## 2026-05-05 Pre-Operation Priority Check and Safety Cleanup

### Background

- User brought three checkpoint concerns before real operation:
  - yfinance reliability metadata,
  - manual vs yfinance priority,
  - stale threshold,
  - synthetic test candidates appearing as `PASS`,
  - `web_ui.py` being close to the file-size guard.
- User also asked whether the proposed next-priority list was sensible.

### Cause

- The market-summary step had logged yfinance as secondary enrichment, but it did not explicitly record all three data-policy decisions that should have been user-confirmed.
- Synthetic `seed:test-universe` rows could be mistaken for real quality-screen `PASS` rows.
- `web_ui.py` remained close enough to the guard that another UI feature could push it over the line.

### Change

- Added `USER_INPUT_NEEDED.md` data-policy confirmation items:
  - yfinance reliability metadata,
  - manual/provider overwrite priority,
  - stale-data thresholds.
- Changed the screener so `seed:test-universe` rows render as `TEST`, not `PASS`.
- Added visual styling for `TEST` rows.
- Changed yfinance market enrichment priority:
  - manual/existing verified values win,
  - yfinance fills blanks,
  - yfinance may replace only `seed:test-universe` values.
- Split data-status rendering out of `app/web_ui.py` into `app/web/data_status_panel.py`.
- Updated `HANDOFF_FOR_NEXT_WORKER.md` priority recommendations to make one week of real operation the top priority after these safety fixes.

### 사전에 없는 임의 결정

- The following are now explicitly provisional and require user confirmation before deeper implementation:
  - yfinance reliability metadata: currently represented only through source/notes, no dedicated reliability column.
  - manual vs yfinance priority: current code uses manual/existing verified values over yfinance; yfinance fills blanks and replaces seed data only.
  - stale threshold: current data-status behavior is price <= 7 days good, <= 14 days normal, older/missing needs refresh.
- Synthetic candidates use `TEST` status instead of a separate table because this is the smallest UI change that removes `PASS` confusion before real operation.
- The data-status panel was chosen for the first web split because it is self-contained and reduces `web_ui.py` without changing dashboard behavior.

### Operating Rule

- After these safety fixes, do not add more features until the user has run the app for about a week and identified actual pain points.
- New large UI work must start in `app/web/`, not in `app/web_ui.py`.
- Test seed rows must never be presented as operating PASS rows.

### Verification

- Focused tests passed: `py -3 -m pytest tests\test_default_universe.py tests\test_market_fundamentals.py tests\test_fundamentals_screener.py tests\test_web_ui.py tests\test_file_size_guard.py -q -p no:cacheprovider` passed 12 tests.
- Compile check passed: `py -3 -m compileall -q app tests`.
- Full regression passed: `py -3 -m pytest -q -p no:cacheprovider` passed 91 tests.
- File-size check after split: `app/web_ui.py` 1048 lines, `app/main.py` 714 lines, `app/web/fundamental_screener.py` 285 lines, `app/web/data_status_panel.py` 47 lines.
- Restarted the local UI at `http://127.0.0.1:8770`; HTTP 200 and in-app browser checks found `Seed default test universe`, `TEST` labels, and the API data-status panel.

## 2026-05-06 Beginner Workflow UI Cleanup

### Background

- User said the app still felt difficult for a stock beginner because too much text was in English and the screen did not clearly show what to review first.
- User asked for the UI to follow the same practical order previously explained in conversation.

### Cause

- The tab labels were feature-oriented instead of workflow-oriented.
- Candidate status values such as `PASS`, `WATCH`, and `TEST` were visible without enough beginner-facing meaning.
- Candidate input buttons still used English labels such as `Seed default test universe` and `Market PER/PBR/momentum fetch`.

### Change

- Changed the top tabs to a step-by-step review flow:
  - `1 오늘 순서`,
  - `2 정보 확인`,
  - `3 후보 고르기`,
  - `4 매수 전 점검`,
  - `5 내 계좌`,
  - `6 기록/복기`,
  - `설정`.
- Added `app/web/beginner_guide.py` for reusable beginner-facing workflow guidance, keeping `web_ui.py` within the file-size guard.
- Added a first-screen guide explaining what to review in order.
- Added short tab intro boxes that explain what each tab is for and what to do next.
- Renamed the visible app title to `주식 판단 친구` while keeping `Stock Expert Friend` as a subtitle.
- Reworked the candidate screener display:
  - `PASS` renders as `검토 후보`,
  - `WATCH` renders as `관찰 필요`,
  - `REJECT` renders as `제외`,
  - `TEST` renders as `테스트 데이터`.
- Grouped candidate rows into beginner-facing sections: actual candidates, watch items, rejected items, and test data.
- Replaced several English form labels/buttons in the candidate screen with Korean labels.

### 사전에 없는 임의 결정

- Kept internal rule/status codes unchanged and changed only display labels, because the engine/tests/backtest logic should remain stable.
- Kept `Stock Expert Friend` visible as a subtitle for continuity with existing docs and tests, but made the primary title Korean.
- Added guide text as UI copy instead of a new settings option, because the user asked for a better default beginner experience.

### Operating Rule

- New user-facing UI labels should default to Korean first. Internal codes may remain English when needed for rule stability, but they should not be the only visible explanation.
- Workflow tabs should answer: what to check first, what to decide here, and where to go next.

### Verification

- Focused tests passed: `py -3 -m pytest tests\test_web_ui.py tests\test_default_universe.py tests\test_fundamentals_screener.py tests\test_file_size_guard.py -q -p no:cacheprovider` passed 9 tests.
- Compile check passed: `py -3 -m compileall -q app tests`.
- Full regression passed: `py -3 -m pytest -q -p no:cacheprovider` passed 91 tests.
- Restarted the local UI at `http://127.0.0.1:8770`; in-app browser checks found the Korean app title, workflow guide, step tabs, candidate guide, `테스트 데이터`, and the Korean seed button.

## 2026-05-06 Pre-Operation UI Reorder

### Background

- User reviewed the beginner UI and identified two red-priority issues to fix before the one-week live-use period:
  - trade journal entry was under `5 내 계좌` while journal review was under `6 기록/복기`,
  - `4 매수 전 점검` showed advanced sensitivity/blackout settings before the everyday buy-check form.

### Cause

- The first beginner UI pass improved labels and tabs, but some sections were still grouped by implementation history instead of daily user flow.
- Advanced protection inputs are useful, but they are not the first thing a beginner should see when deciding whether to buy.

### Change

- Moved `매매 일지 입력` from `5 내 계좌` to `6 기록/복기`.
- Kept `5 내 계좌` focused on cash, holdings, and watchlist management.
- Reordered `4 매수 전 점검`:
  - top: `매수 전 체크`,
  - middle: `현재 보유 상태`,
  - lower area: rule reference and an expandable advanced protection section.
- Wrapped `종목 민감도 / 연휴 갭` and `결정 보호` inside a collapsed `고급 보호장치` details panel.
- Did not add/remove input fields and did not change rule-engine behavior.

### 사전에 없는 임의 결정

- Kept the rule reference visible in the buy-check tab because it explains why the engine pauses or blocks, but moved advanced configuration into a collapsed panel to reduce first-screen pressure.

### Operating Rule

- Daily-action tabs should put the most frequent action first and move rare setup/advanced inputs lower or behind disclosure controls.
- Journal input and journal review should stay together unless a future dedicated journaling workflow is intentionally split.

### Verification

- Focused tests passed: `py -3 -m pytest tests\test_web_ui.py tests\test_file_size_guard.py -q -p no:cacheprovider` passed 3 tests.
- Compile check passed: `py -3 -m compileall -q app tests`.
- Full regression passed: `py -3 -m pytest -q -p no:cacheprovider` passed 91 tests.
- File-size check: `app/web_ui.py` 1062 lines, under the 1100-line guard.
- Restarted the local UI at `http://127.0.0.1:8770`; in-app browser checks confirmed the buy-check tab shows `매수 전 체크`, `현재 보유 상태`, and `고급 보호장치`, and the journal tab shows both `매매 일지 입력` and `최근 매매 일지`.

## 2026-05-06 Desktop Launcher

### Background

- User asked for a desktop executable so they do not have to ask Codex to open the local app each time.

### Change

- Created `C:\Users\kim\OneDrive\Desktop\주식판단친구 실행.cmd`.
- The launcher checks `F:\codex\stock_expert_friend`, starts `py -3 -B -m app.main --web --port 8770` if the local app is not already responding, then opens `http://127.0.0.1:8770/`.

### Operating Rule

- For daily local use, double-click the desktop launcher instead of manually running the web command.
- If the project folder moves, update the `APP_DIR` value inside the launcher.

### Verification

- Ran the desktop launcher through `cmd /c`.
- HTTP check passed for `http://127.0.0.1:8770/` with status 200 and confirmed the page contains `주식 판단 친구` and `1 오늘 순서`.

## 2026-05-06 Korean Ticker Search and Holding Usability

### Background

- User said ticker-code entry is too hard for a beginner and asked to type Korean names such as Samsung directly.
- User also said holding entry was uncomfortable because current price did not update automatically, share count was not obvious, and mistaken holdings could not be deleted or clearly edited.

### Cause

- Forms required exact ticker symbols such as `005930.KS`.
- Holding save used the manually entered current price, or fell back to average price, unless the user separately pressed price update.
- The holdings table showed quantity and price, but did not emphasize share count, KRW valuation, edit behavior, or delete actions.

### Change

- Added `app/web/ticker_search.py` with a shared Korean-name ticker datalist and submit-time conversion script.
- Applied Korean-name ticker input support to:
  - holdings,
  - watchlist,
  - sensitivity,
  - blackout,
  - conditional decisions,
  - earnings,
  - research notes,
  - trade journal,
  - buy-check,
  - DART fundamentals,
  - market fundamentals,
  - manual fundamentals.
- Added common aliases such as `삼성전자`, `삼전`, `하이닉스`, `펄어비스`, `애플`, `엔비디아`, `구글`, `마이크로소프트`, `QQQ`, and `SMH`.
- Added `app/web/portfolio_panel.py` and moved holdings table rendering out of `web_ui.py`.
- When saving a holding with an empty current-price field, the app now tries to refresh/cache recent yfinance/Yahoo price data and uses the latest cached close.
- The holdings table now shows:
  - `보유수량` as shares,
  - KRW valuation,
  - USD-to-KRW helper text,
  - edit guidance,
  - per-row delete button.
- Added `/delete-holding` route for mistaken holdings.
- Added the holdings edit/delete table to `5 내 계좌`, not only the buy-check tab.

### 사전에 없는 임의 결정

- Kept stored tickers as canonical ticker symbols and used Korean names only as input aliases, because data collectors and rules already depend on ticker symbols.
- Used a local curated alias list instead of a live search API to avoid adding unstable external dependencies before the one-week operation period.
- Current-price refresh uses latest cached/delayed provider data, not guaranteed real-time broker quotes.

### Operating Rule

- Users may type Korean names in ticker fields, but the app stores ticker symbols internally.
- If a holding is wrong, delete it from `5 내 계좌` or save the same ticker again to overwrite its fields.
- Current prices are convenience estimates from market data providers; final broker values still need manual confirmation for real decisions.

### Verification

- Focused tests passed: `py -3 -m pytest tests\test_web_ui.py tests\test_file_size_guard.py tests\test_fundamentals_screener.py -q -p no:cacheprovider` passed 7 tests.
- Compile check passed: `py -3 -m compileall -q app tests`.
- Full regression passed: `py -3 -m pytest -q -p no:cacheprovider` passed 92 tests.
- File-size check: `app/web_ui.py` 1090 lines, `app/web/ticker_search.py` 224 lines, `app/web/portfolio_panel.py` 46 lines.
- Restarted the local UI at `http://127.0.0.1:8770`; in-app browser checks confirmed Korean ticker-search help, Samsung alias options, holdings edit/delete title, share quantity, valuation, delete button, and edit guidance in `5 내 계좌`.
