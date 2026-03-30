---
name: x-account-seed-discovery
description: Use when discovering X.com seed accounts for crawling based on news-grounded topics, filtering opportunistic accounts, and evaluating account eligibility with AI judgment
---

# X Account Seed Discovery

## Overview

Discover quality **individual** X.com seed accounts using a **news-first approach** that grounds account search in actual news topics rather than profile metadata alone. This skill extracts keywords from news articles, searches X posts using those keywords, and evaluates **individual human accounts** (not government, organizations, or brands) based on their actual posting behavior with AI judgment.

**Core principle:** Post evidence > bio claims. Relevance is proven through what accounts actually post, not what they claim in their profile. **Focus:** Individual real users only - no government, organization, institution, or brand accounts.

### What This Skill Does

1. **Searches news articles** for your topic to find current, relevant issues
2. **Extracts keywords and entities** from those articles
3. **Searches X posts** via Nitter instances using those keywords
4. **Filters out spam/promo/opportunistic accounts** with aggressive anti-wave filtering
5. **Filters out government/organization/brand accounts** - keeping only individual users
6. **Uses AI to judge** which accounts are quality seed candidates
7. **Saves results to SQLite** with full audit trail and no duplicates

**Result:** A curated list of **individual X accounts** that genuinely discuss your topic, ready for monitoring or crawling.

## When to Use

**Use this skill when:**
- You need **individual user accounts** for X.com crawling/monitoring (not government/org/brand accounts)
- You want accounts that genuinely discuss specific topics (not just have keywords in bio)
- You need to filter out opportunistic accounts, spam, promo, porn, gambling
- You need to filter out government, organization, institution, and brand accounts
- You want news-grounded discovery that follows actual current issues
- You need persistent, auditable results with SQLite storage

**Don't use when:**
- You want government or official accounts
- You want organization/institution/brand accounts
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

## Nitter Instance Management

The skill uses multiple Nitter instances with automatic load balancing and rate limit awareness:

### Default Instances

```python
NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.privacyredirect.com",
    "https://w.twstalker.com",  # Alternative X viewer
]
```

✅ **Removed non-working instances:**
- ❌ `xcancel.com` (Cloudflare)
- ❌ `lightbrd.com` (Cloudflare)
- ❌ `nitter.space` (Cloudflare + Ads)
- ❌ `nuku.trabun.org` (Cloudflare)
- ❌ `nitter.poast.org` (Always returns 403)
- ❌ `nitter.tiekoetter.com` (Blocks automation/scraping)
- ❌ `nitter.catsarch.com` (Not working)

**Alternative X Viewers:**
- **TwStalker** (`w.twstalker.com`) - Often more reliable than Nitter, provides public profile viewing
- Can be added via `NITTER_INSTANCES` env var for automatic load balancing

See [Nitter Instances Wiki](https://github.com/zedeus/nitter/wiki/Instances) for the full list.

### Rate Limit Handling

- Tracks response times and error rates per instance
- Automatically rotates to healthy instances
- Exponential backoff for rate-limited instances
- Marks instances as unhealthy after consecutive failures

### Chrome Profile

Nitter access uses Playwright with a persistent Chrome profile:
- **Location:** `~/.x-discovery/chrome-profile`
- **Purpose:** Maintains cookies/session state across runs
- **Benefits:** Reduces detection, improves reliability
- **Creation:** Automatic on first run
- **DNS:** Uses Google DNS over HTTPS (DoH) by default to bypass regional blocks

## Implementation Details

### Quick Start (5 minutes)

```bash
# 1. Create config directory and setup database
mkdir -p ~/.x-discovery
sqlite3 ~/.x-discovery/seed.sql < skills/x_account_seed_discovery/sql/schema.sql

# 2. Set environment
export SQLITE_PATH="$HOME/.x-discovery/seed.sql"
export DEFAULT_REGION="Indonesia"

# 3. Run with Claude Code
@x_account_seed_discovery with topic="politics" region="Indonesia" min_followers=5000
```

### Prerequisites

Before using this skill, ensure you have:
- **SQLite 3.x** installed on your system
- **Serper API key** for news search (get from https://serper.dev)
- **Playwright** installed for Nitter access (`pip install playwright playwright-stealth`)
- **Chrome profile** created at `~/.x-discovery/chrome-profile`
- **This skill repository** cloned or downloaded locally
- **Environment variables** configured (see below)

### Architecture

**News Search (HTTP-based):**
- **Default:** Serper.dev for Google News (requires API key, get from https://serper.dev)
- Optional: SerpAPI for Google News (requires API key, more expensive)
- Optional: DuckDuckGo (free, no API key) - use `--provider duckduckgo` flag
- No browser automation needed

**X/Twitter Access (Browser-based):**
- Uses Nitter instances via Playwright with Chrome profile
- Chrome profile stored at `~/.x-discovery/chrome-profile`
- Automatic instance rotation with rate limit awareness
- Stealth mode to avoid detection

### 1. Setup SQLite Database

```bash
# Create the default config directory
mkdir -p ~/.x-discovery

# Run schema.sql to initialize tables
sqlite3 ~/.x-discovery/seed.sql < skills/x_account_seed_discovery/sql/schema.sql
```

### 2. Configure Environment

```bash
export SQLITE_PATH="$HOME/.x-discovery/seed.sql"
export DEFAULT_REGION="Indonesia"

# Required: For Serper.dev Google News (default provider, get key from https://serper.dev)
export SERPER_API_KEY="your_serper_key"

# Optional: For SerpAPI Google News (requires API key, more expensive)
export SERPAPI_KEY="your_serpapi_key"

# Optional: Custom Nitter instances (defaults provided)
export NITTER_INSTANCES="https://nitter.net,https://xcancel.com"
```

**Supported Runtimes:**
- **Claude Code** - Use `@x_account_seed_discovery` with natural language parameters
- **Opencode** - Use `opencode run skill x_account_seed_discovery` with JSON input
- **Custom agentic tools** - Import and call with structured input/output
- **Direct scripts** - Run Python scripts directly

### 3. Setup Chrome Profile

Create a Chrome profile for Nitter access:

```bash
# Create profile directory
mkdir -p ~/.x-discovery/chrome-profile

# The profile will be populated automatically on first run
# Or manually setup by opening Chrome with:
# google-chrome --user-data-dir="$HOME/.x-discovery/chrome-profile"
```

### 4. Run Discovery

**Claude Code example:**
```
@x_account_seed_discovery with topic="politics" region="Indonesia" min_followers=5000
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

**Direct script execution:**
```bash
# Search news with Serper.dev (default, requires API key)
python skills/x_account_seed_discovery/scripts/search_news.py \
  --topic "politics" \
  --region "Indonesia" \
  --max-results 20

# Search news with SerpAPI (requires API key, more expensive)
python skills/x_account_seed_discovery/scripts/search_news.py \
  --topic "politics" \
  --region "Indonesia" \
  --provider serpapi \
  --max-results 20

# Search news with DuckDuckGo (free, no API key)
python skills/x_account_seed_discovery/scripts/search_news.py \
  --topic "politics" \
  --region "Indonesia" \
  --provider duckduckgo \
  --max-results 20

# Search news with SSL verification disabled (if you get certificate errors with DuckDuckGo)
python skills/x_account_seed_discovery/scripts/search_news.py \
  --topic "politics" \
  --region "Indonesia" \
  --max-results 20 \
  --no-verify-ssl \
  --provider duckduckgo

# Search X via Nitter
# IMPORTANT: Global flags (--headless, --no-stealth, etc.) MUST come BEFORE the subcommand
python skills/x_account_seed_discovery/scripts/search_nitter.py \
  --headless \
  search \
  --query "politics Indonesia" \
  --max-results 50
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

All data is persisted to the SQLite database at `$HOME/.x-discovery/seed.sql` (or your configured `SQLITE_PATH`). Query it directly:

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

### Target: Individual Real Users Only
This skill focuses on discovering **individual human accounts** sharing personal perspectives and opinions.

**Explicitly EXCLUDED:**
- Government accounts (presidents, ministries, official gov handles)
- Organization/Institution accounts (political parties, NGOs, companies)
- Media/News outlets (official news accounts)
- Corporate/Brand accounts

**Look for:**
- Personal display names and bios
- First-person language and opinions
- Human variety in content (not just official statements)
- Individual perspectives on topics

### Eligible
- **Individual person** (not government/org/institution/brand)
- Clearly relevant to topic AND region
- Sample posts show topic consistency
- No spam/promo/porn/gambling signals
- Worthy of seed monitoring

### Uncertain
- Weak relevance signals
- Too few sample posts
- Incomplete metadata
- Unclear if individual or organization
- Possible relevance but not strong enough

### Not Eligible
- Government/Organization/Institution/Brand account
- Off-topic
- Dominant spam/promo/porn/gambling/clickbait
- Highly opportunistic
- Clear region mismatch
- Only riding keyword trends without substance

**AI instructions:**
- **PRIORITY #1:** Verify account is an INDIVIDUAL person, not government/org/brand
- Don't select just because account is big or verified
- Don't select just because bio looks relevant
- Sample posts matter more than bio
- Opportunistic/trend hijackers get heavy penalty
- Government/org accounts: REJECT regardless of relevance

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

### ❌ Wrong: Global flags after subcommand
```bash
# ❌ BROKEN: --headless placed AFTER search subcommand
python search_nitter.py search --query "test" --headless
```
Global flags (`--headless`, `--profile-dir`, `--no-stealth`) are defined on the root parser and **must come before** the `search`/`profile` subcommand. This is a standard argparse behavior.

### ✅ Right: Correct argument order
```bash
# ✅ WORKS: Global flags BEFORE subcommand
python search_nitter.py --headless search --query "test"
```

### ❌ Wrong: SSL certificate errors stop execution
If you get `SSLCertVerificationError` with DuckDuckGo news search, the script stops.

### ✅ Right: Use --no-verify-ssl for DuckDuckGo
```bash
python search_news.py --topic "test" --region "Indonesia" --no-verify-ssl
```
Note: This only affects the DuckDuckGo provider. SerpAPI doesn't need this flag.

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
| `scripts/search_news.py` | News search (DuckDuckGo/SerpAPI) |
| `scripts/search_nitter.py` | X/Twitter search via Nitter (Playwright) |

## Version

v1.0 - Initial release with news-first workflow, anti-wave filtering, and SQLite persistence.
