# Stock Expert Friend Handoff

Last updated: 2026-05-06

## Project Identity

Stock Expert Friend is an information, logging, review, and decision-support tool. It is not an auto-trading system, not a guaranteed recommendation engine, and not a replacement for the user's final judgment.

Core operating principle:

1. Collect candidate data.
2. Filter candidates conservatively.
3. Attach news, filings, research notes, and portfolio context.
4. Run buy-check only when the user is considering a real purchase.
5. Treat `PASS` as "research candidate", not "buy"; the current UI displays this as `검토 후보`.

## Current Local App

- Workspace: `F:\codex\stock_expert_friend`
- Local UI: `http://127.0.0.1:8770/`
- Main branch is pushed to GitHub: `https://github.com/khs880514-code/stock.git`
- Local DB: `stock_expert_friend.sqlite3`
- Local secrets: ignored `.env`
- Required local env keys currently provided:
  - `SEF_DART_API_KEY`
  - `SEF_SEC_USER_AGENT`

Do not print, commit, or copy the actual API key or user email into repo files.

## Current User Portfolio Snapshot

The user provided screenshots on 2026-05-05 and stated remaining cash is 29,000,000 KRW.

Current local DB has been updated to:

| Ticker | Account | Shares | App Current Value KRW | Notes |
|---|---:|---:|---:|---|
| AAPL | GENERAL_TOSS | 11 | 4,541,132 | Toss general account |
| AMD | GENERAL_TOSS | 5 | 2,560,177 | Toss general account |
| MVST | GENERAL_TOSS | 110 | 314,060 | Large loss position, keep visible |
| SMH | ISA_KIWOOM | 1 | 770,819 | Kiwoom ISA |
| QQQ | ISA_KIWOOM | 2 | 2,020,842 | Kiwoom ISA |
| Cash | Manual | - | 29,000,000 | User-stated remaining cash |

Approximate app total value using configured FX: 39,207,029 KRW.

Important caveat: average/current USD prices were reverse-calculated from KRW screenshots using `AppConfig.fx_usd_krw`. Exact broker tax lots should be checked against Toss/Kiwoom detail screens later.

## Implemented So Far

### Core

- SQLite schema and stores for:
  - holdings,
  - trades,
  - watchlist,
  - account settings,
  - price history,
  - news headlines,
  - filings,
  - earnings calendar,
  - research notes,
  - fundamentals,
  - buy-check logs,
  - ticker sensitivity,
  - conditional decisions and blackouts.

### Account/Broker Policy

- User decided: Toss general account + Kiwoom ISA.
- Broker auto-sync is intentionally N/A.
- Portfolio input remains manual.
- Holdings currently use ticker as the primary key, so the same ticker cannot be split across two accounts yet. Future migration needed: `(account_key, ticker)`.

### Rule Engine / Buy Check

Implemented guardrail-style rules include:

- FOMO and outside-influence scoring.
- Position sizing and cash guardrails.
- Existing position and theme exposure checks.
- Earnings D-7 event block when earnings calendar is entered.
- `post_drop_chase` behavior.
- Post-run decomposition behavior.
- Decision protection / blackout behavior.
- Ticker sensitivity and holiday gap behavior.

The rule engine can include recent price history, news headlines, filings, research notes, earnings dates, account route, and portfolio context in the review message.

### Candidate Screener

Candidate screener supports:

- Manual fundamental entry.
- OpenDART fundamentals fetch.
- yfinance/Yahoo market summary enrichment.
- Beginner-facing grouped result sections:
  - `검토 후보` for internal `PASS`,
  - `관찰 필요` for internal `WATCH`,
  - `제외` for internal `REJECT`,
  - `테스트 데이터` for internal `TEST`.
- Candidate detail cards.
- Linked counts for news, filings, and research notes.

Synthetic test candidates exist only to verify the screener. They are source-labeled `seed:test-universe`, displayed as `테스트 데이터` / internal `TEST` instead of `PASS`, and are not recommendations.

### Current Beginner UI Flow

The visible tabs are now ordered for daily use:

1. `1 오늘 순서`
2. `2 정보 확인`
3. `3 후보 고르기`
4. `4 매수 전 점검`
5. `5 내 계좌`
6. `6 기록/복기`
7. `설정`

The primary visible app title is `주식 판단 친구`; `Stock Expert Friend` remains as a subtitle for continuity.

Pre-operation UI cleanup on 2026-05-06 also made these daily-flow choices:

- `4 매수 전 점검` starts with the everyday buy-check form, then current holdings, while sensitivity/blackout settings sit in a collapsed advanced panel.
- `5 내 계좌` is for cash, holdings, and watchlist management only.
- `6 기록/복기` contains both trade-journal entry and recent trade-journal review.

### Data Connections

Currently wired:

- yfinance/Yahoo chart for price history.
- yfinance market summary for PER/forward PER, market cap, dividend yield, FCF yield, and momentum where available.
- Google News RSS for recent headlines.
- SEC EDGAR submissions for US filings, using the provided User-Agent.
- OpenDART `corpCode.xml` and `fnlttSinglAcnt` for Korean financial-statement-derived fundamentals.

Still optional/future:

- More reliable Korean PER/PBR provider such as a stable Naver/KRX/FnGuide-style source.
- Automatic earnings calendar provider.
- FRED/ECOS macro data.
- Broker sync.

## How The User Should Use The App

### Daily Routine Before Market Decisions

1. Open local UI.
2. Check `데이터 상태`.
3. Refresh prices/news/filings for tracked tickers if needed.
4. Check portfolio exposure and cash.
5. Look at Candidate Screener.
6. Treat candidates as a shortlist only.
7. For any ticker being considered, run buy-check.
8. If buy-check says `NO_TRADE`, pause unless there is a clearly logged reason to override.
9. If acting anyway, record the trade and reason immediately.

### If The US Market Is Open

Use this order:

1. Check whether the stock is already up sharply today or after-hours.
2. If the move is fast, use FOMO score honestly. Do not lower the FOMO score just to pass the rule.
3. Refresh prices so post-run/post-drop logic has recent context.
4. Check recent news and SEC filings. New information is context, not an automatic buy signal.
5. For a screener `PASS`, ask:
   - Is the valuation field real/live or test seed?
   - Is there a near earnings date?
   - Is this already represented by QQQ/SMH/AAPL/AMD exposure?
   - Does the purchase break cash or theme limits?
6. Run buy-check with the intended amount.
7. If allowed, consider only the planned size, not a larger impulse buy.
8. Log the decision.

Practical rule: during live US market hours, the app should slow the user down when a name is already running. It should not be used as a "buy quickly because PASS appeared" screen.

### How To Interpret Candidate Results

`PASS` means:

- enough metrics passed the conservative filter,
- worth reviewing further,
- not a buy order.

`WATCH` means:

- some metrics are attractive,
- data may be missing,
- review later or fill missing data.

`REJECT` means:

- one or more conservative thresholds failed,
- only revisit with a specific reason.

## FOMO / Outside Influence Handling

FOMO and outside influence matter because the user can rationalize a chase after seeing a fast move or hearing a strong outside opinion.

The scores are not moral judgments. They are friction. If the user lies to the score, the app cannot prevent it. The purpose is to force a visible pause and later review.

Suggested interpretation:

- FOMO 0-3: planned, calm, thesis-based.
- FOMO 4-6: some urgency, require one more evidence check.
- FOMO 7-8: wait or reduce size.
- FOMO 9-10: block unless there is a pre-written conditional plan.
- Outside influence 7+: require independent counter-point and source check.

## What To Do Next

Recommended next engineering steps:

1. Run the app in real trading/review use for one week before adding more features.
2. Confirm the remaining data-policy decisions:
   - yfinance reliability metadata,
   - manual vs provider overwrite behavior,
   - stale-data thresholds.
3. Add a better Korean valuation provider for PER/PBR if real use shows DART/yfinance are insufficient.
4. Split Candidate Screener controls into smaller sub-sections:
   - seed/test data,
   - DART,
   - market summary,
   - manual entry.
5. Add a portfolio detail screen that shows:
   - account,
   - current value,
   - gain/loss,
   - theme exposure,
   - whether a holding is actual or placeholder.
6. Add a safer "live market checklist" panel beside buy-check.
7. Add exact user-entered broker detail fields for:
   - cost total KRW,
   - current value KRW,
   - realized/unrealized P&L,
   - broker screenshot date.
8. Migrate holdings primary key from ticker to `(account_key, ticker)` before supporting duplicate tickers across Toss and Kiwoom.

## Verification Commands

Run focused tests:

```powershell
py -3 -m pytest tests\test_default_universe.py tests\test_web_ui.py tests\test_file_size_guard.py -q -p no:cacheprovider
```

Run full regression:

```powershell
py -3 -m pytest -q -p no:cacheprovider
```

Start local UI:

```powershell
py -3 -B -m app.main --web --port 8770
```

## Current Known Risks

- The app contains synthetic seed fundamentals for workflow testing; they should render as `TEST`, not `PASS`.
- yfinance does not reliably return all Korean valuation fields.
- yfinance reliability metadata, overwrite priority, and stale thresholds are provisional and still need user confirmation.
- Broker sync is intentionally not implemented.
- Current holdings are derived from screenshots, not exact broker-exported data.
- `PASS` can be misunderstood as a recommendation if the UI is not read carefully.
- `web_ui.py` has been partially split again, but large UI additions should still start in `app/web/`.
