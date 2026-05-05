# Stock Expert Friend v1

이 시스템은 개인 투자자의 자기 판단을 돕는 기록·알림·복기 도구입니다.
최종 투자 판단과 주문은 사용자 본인이 직접 수행합니다.
이 시스템은 투자일임, 투자자문, 유사투자자문 서비스를 제공하지 않습니다.
이 시스템은 수익률을 보장하지 않습니다.

## 목적

Stock Expert Friend v1은 자동매매 프로그램이 아닙니다. 사용자가 매수 충동을 느낄 때 보유 비중, FOMO 점수, 실적 일정, 손실 종목 물타기 위험, 매크로 이벤트를 확인해 한 번 더 멈추도록 돕는 정보 도구입니다.

## 구현 범위

- Python CLI 중심 v1
- SQLite 저장소
- Pydantic 데이터 모델
- 외부 데이터 소스 어댑터 구조와 mock 구현
- 06:00 미장 마감 후 브리핑
- 08:30 국장 시작 전 브리핑 및 1주일 매매 회고
- QQQ/SMH 코어 ETF 룰
- 실적 D-7, FOMO, 과신 언어, 비중, 현금, 손실 종목 추가 투입 차단
- 실적 후 급락 추격매수 감속 룰 `post_drop_chase`
- 매크로 이벤트 트리거 및 양방향 메커니즘 해설
- Trade Journal와 월간 리포트
- Trade Journal replay용 backtest harness
- Telegram 키가 없을 때 콘솔 출력 대체

## 빠른 실행

```bash
py -3 -m app.main --demo
py -3 -m pytest
```

Windows에서 `python` 명령이 Microsoft Store alias로 잡힌 경우 `py -3`을 사용하세요.

## DB 초기화

```bash
py -3 -m app.main --init-db
```

기본 DB 파일은 `stock_expert_friend.sqlite3`입니다. 데모 실행은 `demo_stock_expert_friend.sqlite3`을 사용합니다.

## 매수 검토 CLI

```bash
py -3 -m app.main --buy-check --ticker AMD --amount-krw 1200000 --reason "실적 전 조정 후 반등 검토" --fomo 8 --influence 2
```

결과의 `action`과 `max_amount_krw`는 룰엔진이 결정합니다. LLM 보조 텍스트는 이 값을 만들지 않습니다.

## 운영 입력 CLI

mock seed 없이 실제 입력 데이터로 운영하려면 먼저 현금과 보유종목을 넣습니다.

```bash
py -3 -m app.main --set-cash 12000000
py -3 -m app.main --add-holding --ticker AAPL --account-key GENERAL_TOSS --market US --quantity 2 --avg-price 150 --current-price 180 --currency USD --sector-tag BIG_TECH
py -3 -m app.main --list-portfolio
```

보유종목 스냅샷은 backtest context로 사용할 수 있습니다.

```bash
py -3 -m app.main --snapshot-holdings
```

매매 일지는 수동으로 기록합니다.

```bash
py -3 -m app.main --record-trade --ticker AAPL --account-key GENERAL_TOSS --trade-action BUY --quantity 2 --avg-price 180 --reason "분할 매수 기록" --fomo 3 --influence 1
py -3 -m app.main --list-trades
```

관심종목은 별도 watchlist에 기록합니다.

```bash
py -3 -m app.main --watch-add --ticker AMD --market US --reason "실적 발표 후 재검토" --priority 2 --sector-tag AI_SEMICONDUCTOR
py -3 -m app.main --watch-list
```

## 로컬 웹 UI

브라우저에서 한 화면으로 보려면 로컬 UI 서버를 실행합니다.

```bash
py -3 -m app.main --web --port 8765
```

그 다음 [http://127.0.0.1:8765](http://127.0.0.1:8765)을 엽니다. 이 UI는 로컬 SQLite DB를 읽고 쓰며, 주문 기능은 없습니다.

매수 검토와 매매 일지 입력 영역에는 `FOMO`와 `외부 영향` 점수 기준표가 함께 표시됩니다. 이 점수는 자동 산출값이 아니라 사용자가 자기 상태를 기록하기 위한 입력값입니다.

점수를 낮게 입력하면 기술적으로 통과할 수 있지만, 사유 문장에 `놓치면`, `후회`, `추천`, `유튜브`, `커뮤니티` 같은 표현이 있으면 룰엔진이 `입력 점수-사유 불일치` 경고를 붙이거나 24시간 대기를 걸 수 있습니다. 완전한 거짓말 방지 장치가 아니라, 매수 직전 자기기록과 마찰을 남기는 안전장치입니다.

UI의 `룰엔진이 보는 정보` 영역은 현재 판단에 쓰이는 데이터와 한도를 보여줍니다. 현재 단계에서는 포트폴리오, 매매기록, 수동 저장한 실적 일정, 가격 히스토리를 실제 DB 입력값으로 씁니다.

`최근 정보` 영역의 버튼으로 보유/관심 종목의 가격 히스토리, Google News RSS 헤드라인, SEC EDGAR 최근 제출 목록을 가져올 수 있습니다. 가격 업데이트 후 저장된 히스토리는 매수 검토의 `post_drop_chase` 룰에 연결되고, 뉴스 헤드라인은 실적/가이던스, 규제/소송, 애널리스트/목표가, 자금조달/희석, 모멘텀/과열 플래그로 분류되어 매수 검토 결과에 참고 문맥으로 붙습니다.

SEC 공시는 `8-K`, `10-Q`, `10-K`, `S-1`, `S-3`, `424B`, `424B5`, `DEF 14A` 같은 주요 제출 유형만 저장합니다. SEC 자동 접근 정책에 맞추려면 실제 사용 전 아래처럼 연락 가능한 User-Agent를 설정하세요.

```bash
set SEF_SEC_USER_AGENT=StockExpertFriend/1.0 your-email@example.com
```

뉴스와 공시는 룰엔진의 주문 판단을 직접 바꾸지 않습니다. 새 정보가 있어도 `NO_TRADE`나 `SMALL_BUY_CANDIDATE` 결정은 구조화된 룰이 만들고, 뉴스/공시는 출처 있는 확인 항목으로만 표시합니다.

`실적 일정` 영역에서는 종목별 실적일을 직접 저장할 수 있습니다. 저장된 실적일은 mock 이벤트가 아니라 실제 DB 데이터로 매수 검토의 `실적 D-7` 차단 룰에 연결됩니다. 자동 실적 캘린더 API는 제공자별 정확도, 유료/무료 제한, API key 이슈가 있어 v1에서는 수동/출처 기반 입력을 기본값으로 둡니다.

`외부 리서치 노트` 영역에는 NotebookLM 요약, 유튜브 영상 요약, 기사 요약, 사용자 메모를 선택 참고자료로 저장할 수 있습니다. 예를 들어 `김지윤의 지식플레이`처럼 신뢰하는 채널의 요약을 넣을 수 있습니다.

장점:
- 종목만 보다가 놓치는 거시·지정학·산업 맥락을 함께 볼 수 있습니다.
- NotebookLM처럼 여러 자료를 묶은 요약을 기록으로 남길 수 있습니다.
- 출처명, URL, 신뢰도, 요약을 함께 저장해 나중에 복기하기 쉽습니다.

주의점:
- 유튜브/요약 자료는 2차 해석이므로 원문 오독, 편향, 과장 가능성이 있습니다.
- 특정 채널을 신뢰하더라도 매수 근거가 아니라 확인할 질문 목록으로 써야 합니다.
- 그래서 이 노트는 룰엔진 결정을 직접 바꾸지 않고, 매수 검토 결과의 `외부 리서치 노트` 참고 항목으로만 표시합니다.

리서치 노트에는 `반대근거`와 `확인질문`도 함께 저장합니다. 좋은 자료일수록 바로 매수 근거로 쓰기보다, “이 주장이 틀릴 수 있는 이유”와 “내가 직접 확인할 질문”을 같이 남기는 방식으로 사용합니다.

`데이터 상태` 영역은 종목별로 가격, 뉴스, SEC 공시, 실적 일정, 리서치 노트가 얼마나 채워져 있는지 보여줍니다. `API 연결 준비 상태`는 내일 연결할 외부 API 키/환경변수의 준비 여부를 보여주는 체크리스트입니다. 오늘 단계에서는 API 연결 자체는 추가하지 않고, 내일 키를 넣고 수집기만 연결하면 되도록 상태판만 준비했습니다.

`계좌 설정` 영역에서는 사용할 증권사와 계좌 용도를 저장합니다. 기본값은 아래처럼 둘 수 있습니다.

- `GENERAL_TOSS`: 일반 매매/해외주식, 토스증권
- `ISA_KIWOOM`: ISA 계좌, 키움증권

매수 검토 폼에서 검토 계좌를 선택하면 결과 메시지에 계좌 라우팅이 함께 남습니다. 보유종목과 매매일지에도 `account_key`가 저장됩니다. 현재 `holdings`의 기본 키는 아직 `ticker`라서 같은 종목을 Toss와 Kiwoom ISA에 동시에 나눠 보유하는 정밀 포지션 분리는 다음 단계에서 확장합니다.

## post_drop_chase 룰

`post_drop_chase`는 최근 5거래일 안에 단일일 -7% 이하 하락 또는 누적 -10% 이하 하락이 있는 종목을 감지합니다. 실적일과 인접하면 high severity로 보고, FOMO 점수에 따라 차단 또는 금액 상한 축소를 적용합니다. QQQ, SMH 같은 코어 ETF는 기존 ETF 룰이 처리하므로 이 룰에서는 우회합니다.

## 삼성전자/하이닉스 오판 방지 룰

2026-05-04에 추가한 3개 룰은 “오른 종목을 무조건 막는” 장치가 아니라, 설명 가능한 상승과 후회 추격을 분리하기 위한 보조 룰입니다.

- `ticker_sensitivity`: 종목별 시장, 섹터 태그, 미국 프록시 ETF, 외국인 지분율, 미국 섹터 상관, KOSPI 베타를 저장합니다.
- `holiday_gap_setup`: 국내 휴장 중 미국 섹터가 크게 움직였고 외국인/섹터 민감도가 높은 종목이면 매수 상한을 낮춥니다.
- `post_run_decomposition`: 최근 급등을 KOSPI, 미국 섹터, 뉴스 설명분으로 나누고 설명되지 않은 잔여 급등만 추격 위험으로 봅니다.
- `decision_protection`: NO_TRADE/WATCH 직후 가격 급등을 보고 후회로 따라 사는 패턴을 감지하고, 관찰 블랙아웃/조건부 결정을 기록합니다.

민감도는 UI의 `종목 민감도 / 연휴 갭` 영역 또는 CLI로 수동 입력합니다.

```bash
py -3 -m app.main --sensitivity-set --ticker 000660.KS --market KR --sector-tag AI_SEMICONDUCTOR --proxy SMH --foreign-pct 53 --sector-corr 0.78 --beta-kospi 1.2
py -3 -m app.main --seed-kr-semiconductor-sensitivity
py -3 -m app.main --sensitivity-list
```

`--seed-kr-semiconductor-sensitivity`는 실제 관측값을 가져오는 기능이 아닙니다. 삼성전자/하이닉스 시뮬레이션을 바로 시작하기 위한 추정 출발점만 넣고, 외국인 지분/상관 관측일은 비워 둡니다. 실제 매수 판단 전에 외국인 지분율, 상관, 베타는 직접 확인한 값으로 덮어쓰는 운영을 기본값으로 둡니다.

후회 추격 방지를 위해 관찰 블랙아웃과 조건부 결정을 남길 수 있습니다.

```bash
py -3 -m app.main --blackout-set --ticker 005930.KS --until-date 2026-05-05 --reason "후회 추격 방지"
py -3 -m app.main --conditional-add --ticker 005930.KS --condition "외국인 순매수와 SMH 강세가 함께 확인되면 재검토" --planned-action WATCH
```

아직 자동 API 연결은 추가하지 않았습니다. 외국인 지분율, 섹터 상관, 미국 프록시 데이터는 오늘 단계에서 수동/캐시 기반이며, 실시간 DART/Naver/yfinance 자동 갱신은 API 연결 작업으로 남겨두었습니다.

한국 종목은 KRX 휴장일이면 투자 판단과 별개로 buy-check가 운영상 `NO_TRADE`를 냅니다. 예를 들어 2026-05-05 어린이날은 휴장으로 처리하고 다음 개장일 재검토를 안내합니다.

## 후보 발굴 / 재무 스크리너

PER, PBR, ROE, 영업이익률, 매출 성장률, 부채비율 같은 재무지표를 수동으로 저장하고, 보수적인 기본 필터로 후보 목록을 만들 수 있습니다. 이 기능은 매수 추천이나 자동 주문이 아니라 `후보 대기열`입니다.

```bash
py -3 -m app.main --fundamental-set --ticker 005930.KS --market KR --company-name "Samsung Electronics" --sector-tag AI_SEMICONDUCTOR --per 14 --forward-per 13 --pbr 1.3 --roe-pct 12 --operating-margin-pct 18 --revenue-growth-pct 7 --debt-to-equity-pct 35 --source manual
py -3 -m app.main --fundamental-list
py -3 -m app.main --screen-stocks
```

기본 필터는 다음처럼 동작합니다.

- `PASS`: 현재 입력값 기준으로 추가 검토 후보.
- `WATCH`: 일부 조건은 괜찮지만 데이터가 부족하거나 강한 우위가 부족한 상태.
- `REJECT`: 입력된 핵심 지표 중 보수적 기준을 명확히 벗어난 상태.

UI의 `후보 발굴 / Candidate Screener` 영역에서는 재무지표 입력 폼, 필터 결과, 종목별 최근 뉴스·공시·리서치 노트 개수를 함께 보여줍니다. 뉴스/공시/리서치는 결정을 자동으로 바꾸지 않고, 사용자가 후보를 비교할 때 볼 근거로만 붙습니다.

현재 단계에서는 재무지표 자동 수집 API를 붙이지 않았습니다. Toss/Kiwoom 포트폴리오 동기화도 N/A 유지이며, 재무지표·포트폴리오 입력은 수동 경로를 기본으로 둡니다.

## OpenDART Fundamentals

The candidate screener includes an `OpenDART fundamentals fetch` form. It reads `SEF_DART_API_KEY` from the ignored local `.env`, looks up the DART corp code through `corpCode.xml`, calls `fnlttSinglAcnt`, and stores only financial-statement-derived metrics such as revenue growth, operating margin, net margin, ROE/ROA, and debt/equity.

This does not fill PER/PBR, market cap, dividend yield, or price momentum. Those still require a market-price or summary provider. Toss/Kiwoom broker sync remains N/A, and portfolio input stays manual.

## Backtest Harness

과거 매수 기록을 현재 룰엔진으로 replay합니다.

```bash
py -3 -m app.main --backtest --since 2025-01-01 --until 2025-12-31 --mode strict
py -3 -m app.main --backtest --since 2025-01-01 --mode reconstruct --rule-version current
```

stdout에는 요약이 출력되고, 상세 결과는 `backtest_report_<timestamp>.json`으로 저장됩니다.

모드:
- `strict`: 스냅샷, 가격, 실적, 환율 컨텍스트 중 하나라도 없으면 skip
- `reconstruct`: 부족한 가격 데이터는 yfinance로 best-effort 복원하고, 포트폴리오 스냅샷이 없으면 빈 포트폴리오로 진행

## 실제 API 연결 상태

v1 데모와 테스트는 mock 데이터로 동작합니다. yfinance/Yahoo chart, Google News RSS, SEC EDGAR submissions는 선택적으로 사용할 수 있습니다. FRED, ECOS, DART, 실적 캘린더 API는 아직 credentialed production integration이 아니라 어댑터 경계 또는 내일 연결할 항목으로 남겨두었습니다. 토스/키움 브로커 자동 동기화는 사용하지 않고, 포트폴리오 입력은 수동 경로를 유지합니다.

## 구현 로그

구현 과정과 설계 결정은 `IMPLEMENTATION_LOG.md`에 남겼습니다.
사용자가 결정하거나 제공해야 하는 항목은 `USER_INPUT_NEEDED.md`에 따로 모았습니다.

## 구조 관리 원칙

재고관리웹에서 진행했던 큰 파일 분리 경험을 반영해, 이 프로젝트도 엔트리 파일이 기능을 계속 흡수하지 않도록 가드합니다.

- `app/web_ui.py`: 웹 요청 라우팅과 대시보드 조립만 담당합니다.
- `app/web/`: 후보 발굴, 탭, 스타일 같은 웹 기능별 panel/form/helper를 둡니다.
- 화면은 기능별 탭으로 나눕니다. 긴 섹션을 페이지 아래에 계속 붙이지 않습니다.
- `app/main.py`: CLI 오케스트레이션만 담당하고, 다음 큰 CLI 기능 전에는 command 모듈 분리를 우선합니다.
- `tests/test_file_size_guard.py`: 엔트리 파일과 웹 기능 모듈의 라인 수를 감시합니다.

## 법적 경계

- 타인 대상 유료 판매 금지
- 리딩방 운영 금지
- 1:1 투자자문 서비스 제공 금지
- 수익률 보장 금지
- 손실 보전 약속 금지
- 금융회사처럼 보이는 표시 금지
## Live API Status

The provided DART key and SEC User-Agent are sufficient for the currently wired disclosure paths. SEC EDGAR and Google News RSS do not need paid keys; SEC only needs the User-Agent. Optional future keys are only needed for macro data, automatic earnings calendars, paid news providers, or a separate market-summary provider.
