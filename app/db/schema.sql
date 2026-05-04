CREATE TABLE IF NOT EXISTS holdings (
  ticker TEXT PRIMARY KEY,
  account_key TEXT NOT NULL DEFAULT 'GENERAL_TOSS',
  market TEXT NOT NULL,
  quantity REAL NOT NULL,
  avg_price REAL NOT NULL,
  current_price REAL NOT NULL,
  currency TEXT NOT NULL,
  asset_type TEXT NOT NULL,
  sector_tag TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS portfolio_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS broker_accounts (
  account_key TEXT PRIMARY KEY,
  account_type TEXT NOT NULL,
  broker_name TEXT NOT NULL,
  default_for TEXT NOT NULL,
  notes TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS watchlist (
  ticker TEXT PRIMARY KEY,
  market TEXT NOT NULL,
  reason TEXT NOT NULL,
  priority INTEGER NOT NULL DEFAULT 3,
  sector_tag TEXT NOT NULL DEFAULT 'UNKNOWN',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  do_not_watch_until TEXT,
  blackout_reason TEXT,
  blackout_set_at TEXT
);

CREATE TABLE IF NOT EXISTS blackout_override_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticker TEXT NOT NULL,
  action TEXT NOT NULL,
  reason TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp TEXT NOT NULL,
  ticker TEXT NOT NULL,
  account_key TEXT NOT NULL DEFAULT 'GENERAL_TOSS',
  action TEXT NOT NULL,
  quantity REAL NOT NULL,
  avg_price REAL NOT NULL,
  reason_text TEXT NOT NULL,
  fomo_score INTEGER NOT NULL,
  friend_influence_score INTEGER NOT NULL,
  price_at_entry REAL NOT NULL,
  price_1d REAL,
  price_1w REAL,
  price_1m REAL,
  outcome_note TEXT NOT NULL DEFAULT '',
  mistake_type TEXT NOT NULL DEFAULT 'NONE'
);

CREATE TABLE IF NOT EXISTS collection_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_name TEXT NOT NULL,
  collected_at TEXT NOT NULL,
  ok INTEGER NOT NULL,
  message TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alert_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  alert_type TEXT NOT NULL,
  ticker TEXT,
  action TEXT,
  rule_id TEXT,
  severity TEXT,
  message TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rule_limit_changes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  changed_at TEXT NOT NULL,
  key TEXT NOT NULL,
  old_value TEXT NOT NULL,
  new_value TEXT NOT NULL,
  reason TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trigger_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  occurred_at TEXT NOT NULL,
  trigger_type TEXT NOT NULL,
  title TEXT NOT NULL,
  observed_value REAL NOT NULL,
  reason TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS llm_calls (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  purpose TEXT NOT NULL,
  input_text TEXT NOT NULL,
  output_text TEXT NOT NULL,
  estimated_cost_krw REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS holdings_snapshot (
  snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
  taken_at TEXT NOT NULL,
  trade_id INTEGER,
  ticker TEXT NOT NULL,
  account_key TEXT NOT NULL DEFAULT 'GENERAL_TOSS',
  shares REAL NOT NULL,
  avg_cost_usd REAL NOT NULL,
  fx_usdkrw REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS price_history (
  ticker TEXT NOT NULL,
  date TEXT NOT NULL,
  open REAL,
  high REAL,
  low REAL,
  close REAL,
  volume INTEGER,
  source TEXT NOT NULL,
  PRIMARY KEY (ticker, date)
);

CREATE TABLE IF NOT EXISTS ticker_sensitivity (
  ticker TEXT PRIMARY KEY,
  market TEXT NOT NULL,
  sector_tag TEXT NOT NULL,
  us_sector_proxy_symbol TEXT,
  foreign_ownership_pct REAL,
  foreign_ownership_taken_at TEXT,
  us_sector_corr_60d REAL,
  us_market_corr_60d REAL,
  fx_corr_60d REAL,
  beta_to_kospi_60d REAL,
  corr_taken_at TEXT,
  manual_override INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS foreign_ownership_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticker TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  foreign_ownership_pct REAL NOT NULL,
  source TEXT NOT NULL DEFAULT 'manual',
  UNIQUE(ticker, observed_at, source)
);

CREATE TABLE IF NOT EXISTS buy_check_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  decision_at TEXT NOT NULL,
  ticker TEXT NOT NULL,
  action TEXT NOT NULL,
  max_amount_krw INTEGER NOT NULL DEFAULT 0,
  price_at_decision REAL,
  reason_text TEXT NOT NULL DEFAULT '',
  fomo_score INTEGER NOT NULL DEFAULT 0,
  friend_influence_score INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS conditional_decisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  ticker TEXT NOT NULL,
  condition_text TEXT NOT NULL,
  planned_action TEXT NOT NULL DEFAULT 'WATCH',
  expires_at TEXT,
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  note TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS news_headlines (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticker TEXT NOT NULL,
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  source_name TEXT NOT NULL,
  published_at TEXT,
  collected_at TEXT NOT NULL,
  UNIQUE(ticker, url)
);

CREATE TABLE IF NOT EXISTS sec_filings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticker TEXT NOT NULL,
  cik TEXT NOT NULL,
  accession_number TEXT NOT NULL,
  form_type TEXT NOT NULL,
  filing_date TEXT NOT NULL,
  report_date TEXT,
  acceptance_datetime TEXT,
  primary_document TEXT,
  primary_doc_description TEXT,
  url TEXT NOT NULL,
  source_name TEXT NOT NULL,
  collected_at TEXT NOT NULL,
  UNIQUE(ticker, accession_number)
);

CREATE TABLE IF NOT EXISTS earnings_calendar_history (
  ticker TEXT NOT NULL,
  earnings_date TEXT NOT NULL,
  source TEXT NOT NULL,
  source_url TEXT NOT NULL DEFAULT '',
  note TEXT NOT NULL DEFAULT '',
  recorded_at TEXT NOT NULL,
  PRIMARY KEY (ticker, earnings_date, source)
);

CREATE TABLE IF NOT EXISTS external_research_notes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  tickers TEXT NOT NULL,
  source_type TEXT NOT NULL,
  source_name TEXT NOT NULL,
  source_url TEXT NOT NULL DEFAULT '',
  reliability TEXT NOT NULL DEFAULT 'MEDIUM',
  summary TEXT NOT NULL,
  counter_points TEXT NOT NULL DEFAULT '',
  check_questions TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS rule_version_log (
  version_id INTEGER PRIMARY KEY AUTOINCREMENT,
  rule_module TEXT NOT NULL,
  rule_name TEXT NOT NULL,
  rule_params_json TEXT NOT NULL,
  effective_from TEXT NOT NULL,
  effective_to TEXT
);

CREATE TABLE IF NOT EXISTS backtest_run (
  run_id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_at TEXT NOT NULL,
  rule_version TEXT NOT NULL,
  since_date TEXT NOT NULL,
  until_date TEXT NOT NULL,
  mode TEXT NOT NULL,
  total_trades INTEGER,
  blocked_count INTEGER,
  warned_count INTEGER,
  passed_count INTEGER,
  skipped_count INTEGER
);

CREATE TABLE IF NOT EXISTS backtest_verdict (
  verdict_id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER NOT NULL,
  trade_id INTEGER NOT NULL,
  verdict TEXT NOT NULL,
  triggered_rules_json TEXT,
  outcome_30d_usd_pct REAL,
  outcome_90d_usd_pct REAL,
  outcome_30d_krw_pct REAL,
  outcome_90d_krw_pct REAL,
  context_completeness TEXT NOT NULL
);
