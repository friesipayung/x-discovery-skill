---
name: x-account-seed-discovery
description: Use when discovering X.com seed accounts for crawling based on news-grounded topics, filtering opportunistic accounts, and evaluating account eligibility with AI judgment
---

# X Account Seed Discovery

## Overview

Discover quality X.com seed accounts using a **news-first approach** that grounds account search in actual news topics rather than profile metadata alone. This skill extracts keywords from news articles, searches X posts using those keywords, and evaluates accounts based on their actual posting behavior with AI judgment.

**Core principle:** Post evidence > bio claims. Relevance is proven through what accounts actually post, not what they claim in their profile.

### What This Skill Does

1. **Searches news articles** for your topic to find current, relevant issues
2. **Extracts keywords and entities** from those articles
3. **Searches X posts** using those keywords to find accounts actually discussing the topic
4. **Filters out spam/promo/opportunistic accounts** with aggressive anti-wave filtering
5. **Uses AI to judge** which accounts are quality seed candidates
6. **Saves results to SQLite** with full audit trail and no duplicates

**Result:** A curated list of X accounts that genuinely discuss your topic, ready for monitoring or crawling.

## When to Use

**Use this skill when:**
- You need seed accounts for X.com crawling/monitoring
- You want accounts that genuinely discuss specific topics (not just have keywords in bio)
- You need to filter out opportunistic accounts, spam, promo, porn, gambling
- You want news-grounded discovery that follows actual current issues
- You need persistent, auditable results with SQLite storage

**Don't use when:**
- You just need random popular accounts
- You want real-time monitoring (this is discovery, not monitoring)
- You need deep engagement analytics
- You want automatic scheduled reruns

## Core Workflow

```
Input (topic + constraints)
  ↓
Search news articles for topic
  ↓
Extract keywords/entities from news
  ↓
Build X search queries
  ↓
Search X posts by keywords
  ↓
Extract accounts from matched posts
  ↓
Aggregate topic signals per account
  ↓
Anti riding-the-waves filter
  ↓
Deterministic prefilter
  ↓
AI judge eligibility
  ↓
Upsert to SQLite
  ↓
Export eligible accounts
```

## Quick Reference

### Required Input
```json
{
  "topic": "politics"
}
```

### Common Optional Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| `region` | `Indonesia` | Geographic scope |
| `min_followers` | - | Minimum follower count |
| `max_news_articles` | 20 | News articles to fetch |
| `max_x_posts` | 300 | X posts to search |
| `max_accounts_to_aggregate` | 100 | Accounts to collect from X posts |
| `max_accounts_to_evaluate` | 100 | Accounts for AI evaluation |
| `min_accounts_to_evaluate` | 1 | Minimum accounts required (triggers auto-loop if not met) |
| `enable_auto_loop` | true | Auto-expand search when minimum not met |
| `max_loops` | 3 | Maximum expansion loops |
| `duplicate_threshold_percent` | 90 | Stop if >90% accounts already captured |
| `anti_wave_mode` | true | Filter opportunistic accounts |
| `save_mode` | `all` | `all` or `eligible_only` |

### Output Decisions
- `eligible` - Quality seed account
- `not_eligible` - Rejected (spam/off-topic/opportunistic)
- `uncertain` - Needs human review

## Implementation

### Quick Start (5 minutes)

```bash
# 1. Setup database
sqlite3 seeds.db < skills/x_account_seed_discovery/sql/schema.sql

# 2. Set environment
export SQLITE_PATH="seeds.db"
export DEFAULT_REGION="Indonesia"

# 3. Run with Claude Code
@x_account_seed_discovery with topic="politics" region="Indonesia" min_followers=5000
```

### Prerequisites

Before using this skill, ensure you have:
- **SQLite 3.x** installed on your system
- **News search provider** access (e.g., web search API, Brave Search, Serper)
- **X/Twitter data provider** access (e.g., X API v2, or web scraping tools)
- **This skill repository** cloned or downloaded locally
- **Environment variables** configured (see below)

### 1. Setup SQLite Database

```sql
-- Run schema.sql to initialize tables
sqlite3 seeds.db < skills/x_account_seed_discovery/sql/schema.sql
```

### 2. Configure Environment

```bash
export SQLITE_PATH="seeds.db"
export DEFAULT_REGION="Indonesia"

# Provider credentials (depends on your runtime and providers):
# - News provider: BRAVE_API_KEY, SERPER_API_KEY, etc.
# - X/Twitter provider: X_API_KEY, X_API_SECRET, etc.
# See TECHNICAL_DESIGN.md for provider-specific setup
```

**Supported Runtimes:**
- **Claude Code** - Use `@x_account_seed_discovery` with natural language parameters
- **Opencode** - Use `opencode run skill x_account_seed_discovery` with JSON input
- **Custom agentic tools** - Import and call with structured input/output
- **Playwright Agent Mode** - Use agent instructions for direct browser control

### Using Playwright (Agent Mode)

For agents (Claude Code, Opencode) that can run Playwright directly, use the agent instructions in `agent-instructions/`:

**Agent Instructions Available:**
- `agent-instructions/PLAYWRIGHT_GUIDE.md` - Complete Playwright usage guide
- `agent-instructions/QUICK_REFERENCE.md` - One-liners and selectors
- `agent-instructions/EXAMPLE_WORKFLOW.md` - Step-by-step execution example

**Key Features:**
- **Stealth Mode**: Uses `playwright-stealth` to avoid detection on X.com
- **No API Keys**: Can use DuckDuckGo (free) instead of paid news APIs
- **Direct Browser Control**: Agent controls browser to search and extract data
- **Anti-Detection**: Random delays, human-like scrolling, custom user agents
- **AdGuard Extension**: Blocks ads and trackers for cleaner scraping (optional but recommended)
- **Sotwe.com Fallback**: Alternative proxy when X.com is inaccessible

**Recommended Setup:**
```bash
# Install Playwright and stealth mode
pip install playwright playwright-stealth
playwright install chromium

# Optional: Install AdGuard extension for better stealth
# Download: https://chromewebstore.google.com/detail/adguard-adblocker/bgnkhhnnamicmpeenaelnjfhikgbkllg
```

**When to Use Agent Mode:**
- You want to avoid API costs
- You need more control over the search process
- You're running in an environment with Playwright available
- You want to use stealth mode for X searches

**Quick Agent Command:**
```
@x_account_seed_discovery Use Playwright with stealth mode to search news 
and X profiles for topic="politics" region="Indonesia"
```

The agent will:
1. Read the agent instructions
2. Use Playwright to search Google News (or DuckDuckGo as fallback)
3. Extract keywords from articles
4. Use Playwright with stealth to search X.com
5. **Fallback to sotwe.com** if X.com requires login or is blocked
6. Aggregate accounts and evaluate with AI
7. Save results to SQLite

**X.com Fallback (Sotwe.com):**
If X.com is inaccessible (requires login, rate limited, or blocked), the agent automatically uses **sotwe.com** as a proxy:
- Search: `https://www.sotwe.com/search/{query}`
- Profile: `https://www.sotwe.com/{handle}`
- Example: `https://www.sotwe.com/prabowo`

Sotwe.com provides public access to X/Twitter content without authentication, making it a reliable fallback when direct X.com access fails.

### 3. Run Discovery

**Claude Code example:**
```
@x_account_seed_discovery with topic="government" region="Indonesia" min_followers=5000
```

**Opencode example:**
```bash
opencode run skill x_account_seed_discovery --input '{
  "topic": "mining policy",
  "region": "Indonesia",
  "min_followers": 10000,
  "anti_wave_mode": true
}'
```

**Direct JSON input:**
```json
{
  "topic": "politics",
  "region": "Indonesia",
  "min_followers": 5000,
  "min_posts": 50,
  "max_news_articles": 20,
  "max_keywords": 40,
  "max_x_posts": 300,
  "max_accounts_to_aggregate": 100,
  "max_accounts_to_evaluate": 100,
  "min_accounts_to_evaluate": 1,
  "anti_wave_mode": true,
  "save_mode": "all"
}
```

### Expected Output

The skill returns a JSON summary including:
- **Run metadata** - `run_id`, `topic`, `region`, timestamps
- **Statistics** - Articles fetched, keywords extracted, posts searched, accounts evaluated
- **Decision counts** - `total_eligible`, `total_not_eligible`, `total_uncertain`
- **Minimum check** - `min_accounts_met`, `min_accounts_required`
- **Eligible accounts** - Array of quality seed accounts with scores and reasons
- **Errors** - Any issues encountered (empty array if successful)

**Example output:**
```json
{
  "run_id": "20260330T100000Z-abc123",
  "topic": "politics",
  "region": "Indonesia",
  "total_eligible": 21,
  "total_not_eligible": 28,
  "total_uncertain": 8,
  "min_accounts_met": true,
  "min_accounts_required": 1,
  "eligible_accounts": [
    {
      "handle": "example",
      "display_name": "Example Account",
      "followers_count": 25000,
      "decision": "eligible",
      "score": 89,
      "reason_short": "Akun rutin membahas isu pemerintahan Indonesia."
    }
  ],
  "errors": []
}
```

**Full output schema:** See `schemas/output.json` for complete structure.

### 4. Export Results

All data is persisted to the SQLite database specified in `SQLITE_PATH`. Query it directly:

```bash
# Connect to your database
sqlite3 $SQLITE_PATH
```

**Export eligible accounts for a topic:**
```sql
SELECT a.handle, a.display_name, a.followers_count, 
       ae.decision, ae.score, ae.reason_short
FROM accounts a
JOIN account_evaluations ae ON a.id = ae.account_id
WHERE ae.decision = 'eligible'
  AND ae.topic = 'politics'
ORDER BY ae.score DESC;
```

**View run summary statistics:**
```sql
SELECT * FROM v_run_summary ORDER BY started_at DESC LIMIT 5;
```

**Export to CSV:**
```bash
sqlite3 $SQLITE_PATH -csv "SELECT * FROM v_eligible_accounts WHERE topic = 'politics'" > eligible_accounts.csv
```

## Anti Riding-the-Waves Filter

The skill aggressively filters opportunistic accounts that hijack trending topics:

**Strong rejection signals:**
- Bio contains: `slot`, `judi`, `casino`, `promo`, `onlyfans`, `bokep`, `open bo`, `pinjol`, `affiliate`
- Display name or URL indicates spam/promo/porn
- Matched posts are few and clearly opportunistic
- Sample posts show more noise/promo than topic relevance
- Hashtags are inconsistent with topic

**How it works:**
1. Rule-based deterministic filter runs before AI judgment
2. Flags are passed to AI judge as context
3. AI can reject even if account passes rule filter

## AI Evaluation Rubric

### Eligible
- Clearly relevant to topic AND region
- Sample posts show topic consistency
- No spam/promo/porn/gambling signals
- Worthy of seed monitoring

### Uncertain
- Weak relevance signals
- Too few sample posts
- Incomplete metadata
- Possible relevance but not strong enough

### Not Eligible
- Off-topic
- Dominant spam/promo/porn/gambling/clickbait
- Highly opportunistic
- Clear region mismatch
- Only riding keyword trends without substance

**AI instructions:**
- Don't select just because account is big or verified
- Don't select just because bio looks relevant
- Sample posts matter more than bio
- Opportunistic/trend hijackers get heavy penalty

## Data Persistence

### Tables
- `runs` - Run metadata and statistics
- `news_articles` - Fetched news articles
- `run_keywords` - Extracted keywords per run
- `accounts` - Master account records (unique by handle_normalized)
- `account_topic_signals` - Aggregated signals per run
- `account_evaluations` - AI evaluation results per run
- `account_tags` - Tags for accounts

### Idempotency
- Reruns don't create duplicate account master rows
- Same handle normalized → upsert existing account
- New evaluation row created for re-evaluations
- Run metadata always fresh

## Common Mistakes

### ❌ Wrong: Profile-only search
Searching X profiles by bio keywords misses accounts that actually post about the topic.

### ✅ Right: Post-first discovery
Search posts by topic keywords, then extract authors. Post evidence proves relevance.

### ❌ Wrong: Accepting all big accounts
Large follower count ≠ relevant to your topic.

### ✅ Right: AI judgment with context
AI evaluates based on sample posts, not just metrics.

### ❌ Wrong: No anti-wave filtering
Without filtering, 30-50% of results can be opportunistic spam/promo accounts.

### ✅ Right: Aggressive prefilter
Blocklist keywords and pattern matching catch most noise before AI evaluation.

## Error Handling

- **Partial failures OK:** One bad candidate doesn't stop the run
- **Invalid AI JSON:** Retry with prompt adjustment
- **Missing provider data:** Continue with available fields
- **DB errors:** Fatal only for persistence/init failures
- **Always produces:** Summary with partial results

## Auto-Expansion Loop

When `enable_auto_loop: true` (default), the skill automatically expands the search if `min_accounts_to_evaluate` is not met in the first pass.

### How It Works

```
Loop 1: Search with base parameters
  ↓
Check: accounts_evaluated >= min_accounts_to_evaluate?
  ↓ YES → Done
  ↓ NO → Continue to Loop 2
Loop 2: Search with expanded parameters (1.5x news, 1.5x keywords)
  ↓
Check: accounts_evaluated >= min_accounts_to_evaluate?
  ↓ YES → Done
  ↓ NO → Continue to Loop 3 (up to max_loops)
Loop 3+: Repeat until min_met or stopping condition reached
```

### Stopping Conditions

The loop stops when any of these conditions are met:

1. **Minimum met** (`min_met`): Enough accounts passed filters and were evaluated
2. **Max loops reached** (`max_loops_reached`): Executed `max_loops` iterations (default: 3)
3. **Duplicate threshold** (`duplicate_threshold`): >90% of accounts found were already captured in previous loops
4. **Error** (`error`): Unrecoverable error occurred during loop

### Loop Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_auto_loop` | `true` | Enable automatic expansion |
| `max_loops` | `3` | Maximum loop iterations |
| `duplicate_threshold_percent` | `90` | Stop if >90% duplicates |
| `loop_news_multiplier` | `1.5` | Multiply news articles each loop |
| `loop_keywords_multiplier` | `1.5` | Multiply keywords each loop |

### Example: Loop in Action

```json
{
  "topic": "mining policy",
  "region": "Indonesia",
  "min_accounts_to_evaluate": 20,
  "enable_auto_loop": true,
  "max_loops": 3,
  "max_news_articles": 20,
  "loop_news_multiplier": 1.5
}
```

**Loop 1:** 20 news articles → 35 keywords → 85 accounts found → 12 pass filters ❌ (need 20)
**Loop 2:** 30 news articles (+50%) → 52 keywords → 78 accounts found → 45 duplicates → 33 new → 28 total pass filters ✅ (exceeds 20)

**Result:** `loop_count: 2`, `loop_stopped_reason: "min_met"`, `accounts_duplicate_percentage: 57.7`

### Disabling Auto-Loop

To disable and fail fast when minimum isn't met:

```json
{
  "topic": "politics",
  "min_accounts_to_evaluate": 50,
  "enable_auto_loop": false
}
```

## Performance Tips

1. **Start small:** Use `max_accounts_to_evaluate=50` for testing
2. **Dry run:** Set `dry_run=true` to preview without DB writes
3. **Tight constraints:** Narrow `min_followers` and `region` to reduce noise
4. **Review uncertain:** Check `uncertain` decisions to tune prompts

## Updating the Skill

To get the latest updates:

```bash
# Navigate to your skill directory
cd ~/.claude/skills/x_account_seed_discovery  # or your custom path

# Pull latest changes
git pull origin main
```

**Claude Code:** Changes are detected automatically - no restart needed.

**Opencode:** Restart or run `opencode reload` to load updates.

See [README.md](../../README.md#updating) for detailed update instructions including database migrations.

## Files Reference

| File | Purpose |
|------|---------|
| `SKILL.md` | This file - usage guide |
| `docs/TECHNICAL_DESIGN.md` | Architecture and implementation details |
| `docs/PRD.md` | Full product requirements |
| `sql/schema.sql` | SQLite database schema |
| `prompts/seed_judge.md` | AI judge prompt template |
| `schemas/input.json` | Input validation schema |
| `schemas/output.json` | Output validation schema |

## Version

v1.0 - Initial release with news-first workflow, anti-wave filtering, and SQLite persistence.
