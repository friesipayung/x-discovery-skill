-- SQLite Schema for X Account Seed Discovery Skill
-- Version: 1.0

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- Enable WAL mode for better concurrency
PRAGMA journal_mode = WAL;

-- Run metadata and statistics
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at DATETIME,
    topic TEXT NOT NULL,
    region TEXT NOT NULL DEFAULT 'Indonesia',
    provider_name TEXT,
    constraints_json TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    total_news_articles INTEGER DEFAULT 0,
    total_keywords INTEGER DEFAULT 0,
    total_x_posts INTEGER DEFAULT 0,
    total_accounts_aggregated INTEGER DEFAULT 0,
    total_prefiltered INTEGER DEFAULT 0,
    total_anti_wave_rejected INTEGER DEFAULT 0,
    total_ai_evaluated INTEGER DEFAULT 0,
    total_eligible INTEGER DEFAULT 0,
    total_not_eligible INTEGER DEFAULT 0,
    total_uncertain INTEGER DEFAULT 0,
    error_message TEXT
);

-- News articles fetched per run
CREATE TABLE IF NOT EXISTS news_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    source TEXT,
    published_at DATETIME,
    snippet TEXT,
    content_excerpt TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
);

-- Keywords extracted per run
CREATE TABLE IF NOT EXISTS run_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    keyword TEXT NOT NULL,
    keyword_type TEXT NOT NULL DEFAULT 'keyword', -- keyword, entity, phrase, hashtag, negative
    frequency INTEGER DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
);

-- Master account records (idempotent - unique by handle_normalized)
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    handle TEXT NOT NULL,
    handle_normalized TEXT NOT NULL UNIQUE,
    display_name TEXT,
    bio TEXT,
    followers_count INTEGER,
    following_count INTEGER,
    post_count INTEGER,
    verified BOOLEAN DEFAULT FALSE,
    profile_url TEXT,
    profile_image_url TEXT,
    location_text TEXT,
    joined_at DATETIME,
    primary_region TEXT,
    source_provider TEXT,
    first_seen_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    raw_profile_json TEXT
);

-- Topic signals aggregated per account per run
CREATE TABLE IF NOT EXISTS account_topic_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    run_id TEXT NOT NULL,
    matched_posts_count INTEGER DEFAULT 0,
    distinct_keywords_matched INTEGER DEFAULT 0,
    matched_entities_json TEXT,
    sample_posts_json TEXT,
    source_queries_json TEXT,
    recent_topic_post_count INTEGER,
    anti_wave_flags_json TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE,
    UNIQUE(account_id, run_id)
);

-- AI evaluation results per account per run
CREATE TABLE IF NOT EXISTS account_evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    account_id INTEGER NOT NULL,
    topic TEXT NOT NULL,
    region TEXT NOT NULL,
    decision TEXT NOT NULL, -- eligible, not_eligible, uncertain
    score INTEGER,
    reason_short TEXT,
    reason_detailed TEXT,
    matched_topic_signals_json TEXT,
    risk_flags_json TEXT,
    suggested_tags_json TEXT,
    opportunistic_score INTEGER,
    consistency_score INTEGER,
    runtime_name TEXT,
    prompt_version TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
);

-- Tags for accounts (many-to-many)
CREATE TABLE IF NOT EXISTS account_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    tag TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
    UNIQUE(account_id, tag)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_runs_topic ON runs(topic);
CREATE INDEX IF NOT EXISTS idx_runs_region ON runs(region);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at);

CREATE INDEX IF NOT EXISTS idx_news_articles_run_id ON news_articles(run_id);
CREATE INDEX IF NOT EXISTS idx_news_articles_url ON news_articles(url);

CREATE INDEX IF NOT EXISTS idx_run_keywords_run_id ON run_keywords(run_id);
CREATE INDEX IF NOT EXISTS idx_run_keywords_keyword ON run_keywords(keyword);

CREATE INDEX IF NOT EXISTS idx_accounts_handle_normalized ON accounts(handle_normalized);
CREATE INDEX IF NOT EXISTS idx_accounts_followers ON accounts(followers_count);
CREATE INDEX IF NOT EXISTS idx_accounts_last_seen ON accounts(last_seen_at);

CREATE INDEX IF NOT EXISTS idx_account_signals_account_id ON account_topic_signals(account_id);
CREATE INDEX IF NOT EXISTS idx_account_signals_run_id ON account_topic_signals(run_id);

CREATE INDEX IF NOT EXISTS idx_account_evaluations_run_id ON account_evaluations(run_id);
CREATE INDEX IF NOT EXISTS idx_account_evaluations_account_id ON account_evaluations(account_id);
CREATE INDEX IF NOT EXISTS idx_account_evaluations_decision ON account_evaluations(decision);
CREATE INDEX IF NOT EXISTS idx_account_evaluations_topic ON account_evaluations(topic);
CREATE INDEX IF NOT EXISTS idx_account_evaluations_region ON account_evaluations(region);
CREATE INDEX IF NOT EXISTS idx_account_evaluations_score ON account_evaluations(score);

CREATE INDEX IF NOT EXISTS idx_account_tags_account_id ON account_tags(account_id);
CREATE INDEX IF NOT EXISTS idx_account_tags_tag ON account_tags(tag);

-- Views for common queries

-- View: Latest evaluation per account per topic
CREATE VIEW IF NOT EXISTS v_account_latest_evaluation AS
SELECT 
    ae.*,
    a.handle,
    a.handle_normalized,
    a.display_name,
    a.followers_count,
    a.verified,
    a.bio
FROM account_evaluations ae
JOIN accounts a ON ae.account_id = a.id
JOIN (
    SELECT account_id, topic, MAX(created_at) as latest_eval_at
    FROM account_evaluations
    GROUP BY account_id, topic
) latest ON ae.account_id = latest.account_id 
    AND ae.topic = latest.topic 
    AND ae.created_at = latest.latest_eval_at;

-- View: Eligible accounts summary
CREATE VIEW IF NOT EXISTS v_eligible_accounts AS
SELECT 
    a.handle,
    a.handle_normalized,
    a.display_name,
    a.followers_count,
    a.verified,
    a.bio,
    a.profile_url,
    ae.topic,
    ae.region,
    ae.score,
    ae.reason_short,
    ae.suggested_tags_json,
    ats.matched_posts_count,
    ats.distinct_keywords_matched,
    r.started_at as evaluated_at
FROM accounts a
JOIN account_evaluations ae ON a.id = ae.account_id
JOIN account_topic_signals ats ON a.id = ats.account_id AND ae.run_id = ats.run_id
JOIN runs r ON ae.run_id = r.id
WHERE ae.decision = 'eligible'
ORDER BY ae.score DESC, a.followers_count DESC;

-- View: Run summary statistics
CREATE VIEW IF NOT EXISTS v_run_summary AS
SELECT 
    r.id,
    r.topic,
    r.region,
    r.started_at,
    r.finished_at,
    r.status,
    r.total_news_articles,
    r.total_keywords,
    r.total_x_posts,
    r.total_accounts_aggregated,
    r.total_prefiltered,
    r.total_anti_wave_rejected,
    r.total_ai_evaluated,
    r.total_eligible,
    r.total_not_eligible,
    r.total_uncertain,
    CASE 
        WHEN r.finished_at IS NOT NULL 
        THEN ROUND((julianday(r.finished_at) - julianday(r.started_at)) * 86400, 2)
        ELSE NULL 
    END as duration_seconds
FROM runs r
ORDER BY r.started_at DESC;

-- Helper function: Normalize handle
-- Usage: SELECT normalize_handle('@UserName') -> 'username'
-- Note: SQLite doesn't support custom functions natively, 
-- so this is documented for application implementation

/*
Handle normalization rules:
1. Convert to lowercase
2. Remove leading '@' if present
3. Extract handle from URL patterns:
   - x.com/username -> username
   - twitter.com/username -> username
4. Remove trailing slashes
5. Trim whitespace

Example implementations:

Python:
def normalize_handle(handle: str) -> str:
    handle = handle.lower().strip()
    handle = handle.lstrip('@')
    if 'x.com/' in handle or 'twitter.com/' in handle:
        handle = handle.split('/')[-1]
    handle = handle.rstrip('/')
    return handle

JavaScript:
function normalizeHandle(handle) {
    return handle
        .toLowerCase()
        .trim()
        .replace(/^@/, '')
        .replace(/^(https?:\/\/)?(www\.)?(x\.com|twitter\.com)\//, '')
        .replace(/\/$/, '');
}
*/

-- Sample queries for common operations

-- Get all eligible accounts for a topic
-- SELECT * FROM v_eligible_accounts WHERE topic = 'politics' AND region = 'Indonesia';

-- Get run statistics
-- SELECT * FROM v_run_summary WHERE topic = 'politics' ORDER BY started_at DESC LIMIT 10;

-- Get account evaluation history
-- SELECT * FROM account_evaluations WHERE account_id = 123 ORDER BY created_at DESC;

-- Get accounts with specific tag
-- SELECT a.* FROM accounts a
-- JOIN account_tags at ON a.id = at.account_id
-- WHERE at.tag = 'politics';

-- Count eligible accounts by topic
-- SELECT topic, region, COUNT(*) as eligible_count
-- FROM account_evaluations
-- WHERE decision = 'eligible'
-- GROUP BY topic, region;

-- Get accounts that were uncertain (need human review)
-- SELECT a.handle, a.display_name, ae.reason_short, ae.score
-- FROM accounts a
-- JOIN account_evaluations ae ON a.id = ae.account_id
-- WHERE ae.decision = 'uncertain'
-- ORDER BY ae.score DESC;
