# Technical Design - X Account Seed Discovery Skill

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Skill Orchestrator                       │
│              (x_account_seed_discovery)                     │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ News Search  │    │ X Search     │    │ AI Judge     │
│ Provider     │    │ Provider     │    │ Runtime      │
│ (Pluggable)  │    │ (Pluggable)  │    │ (Built-in)   │
└──────────────┘    └──────────────┘    └──────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    SQLite Persistence                         │
│  runs │ news_articles │ run_keywords │ accounts │            │
│  account_topic_signals │ account_evaluations │ account_tags   │
└─────────────────────────────────────────────────────────────┘
```

## Component Design

### 1. Input Processing

**Validation:**
- JSON schema validation against `schemas/input.json`
- Type coercion for numeric fields
- Default value injection
- Constraint validation (min_followers < max_followers if both provided)

**Normalization:**
- Region defaults to `Indonesia` if not provided
- Language defaults based on region
- Boolean flags normalized

### 2. News Search Provider Interface

```typescript
interface NewsSearchProvider {
  search(params: NewsSearchParams): Promise<NewsArticle[]>;
}

interface NewsSearchParams {
  topic: string;
  region: string;
  maxArticles: number;
  language?: string;
}

interface NewsArticle {
  id: string;
  title: string;
  url: string;
  source: string;
  publishedAt: Date;
  snippet: string;
  contentExcerpt?: string;
}
```

**Default Implementation:**
- Web search via search tool (e.g., Brave, Serper, etc.)
- Query: `"{topic}" news {region} site:news OR site:berita`
- Filter by recency and relevance
- Deduplicate by URL

### 3. Keyword Extraction

**Hybrid Approach:**

**Rule-based (fast):**
- TF-IDF on article content
- Named entity recognition patterns
- N-gram extraction (2-4 words)
- Hashtag pattern detection

**AI-based (comprehensive):**
- Prompt: Extract keywords, entities, phrases, hashtags, negative keywords
- Context: topic + region + article content
- Output: Structured list with types

**Merging Strategy:**
- Combine rule-based and AI results
- Deduplicate with similarity threshold
- Prioritize by frequency across articles
- Limit to `max_keywords`

### 4. X Search Provider Interface

```typescript
interface XSearchProvider {
  searchPosts(params: XSearchParams): Promise<XPost[]>;
}

interface XSearchParams {
  queries: string[];
  maxPosts: number;
  language?: string;
  region?: string;
}

interface XPost {
  postId: string;
  text: string;
  createdAt: Date;
  matchedQuery: string;
  author: XAuthor;
  engagement?: EngagementMetrics;
  rawPost: any;
}

interface XAuthor {
  handle: string;
  displayName: string;
  profileUrl: string;
  bio: string;
  followersCount: number;
  followingCount?: number;
  postCount?: number;
  verified: boolean;
  locationText?: string;
  profileImageUrl?: string;
  joinedAt?: Date;
  rawProfile: any;
}
```

**Default Implementation:**
- X API v2 (if available with credentials)
- Web scraping fallback using Nitter instances (preferred - no auth required)
  - Primary: https://nitter.net (official)
  - Fallbacks: xcancel.com, nitter.privacyredirect.com, nitter.poast.org, nitter.tiekoetter.com
  - See https://github.com/zedeus/nitter/wiki/Instances for full list
- Query rotation to maximize coverage
- Rate limiting and retry logic with instance failover

### 5. Query Expansion Strategy

**Query Building:**
```
Base: {topic} {region}
+ Keywords: "{keyword1}" OR "{keyword2}"
+ Entities: "{entity1}" OR "{entity2}"
+ Phrases: "{phrase1}" OR "{phrase2}"
+ Hashtags: #{hashtag1} OR #{hashtag2}
+ Language: lang:{language}
- Negative: -{negative1} -{negative2}
```

**Query Variations:**
- Generate 5-10 diverse queries
- Mix broad and specific
- Include temporal qualifiers ("today", "this week")
- Rotate to avoid API limits

### 6. Account Aggregation

**Signal Aggregation per Account:**
```typescript
interface AccountSignals {
  handle: string;
  matchedPostsCount: number;
  distinctKeywordsMatched: string[];
  matchedEntities: string[];
  samplePosts: XPost[];  // Top 5-10 most relevant
  sourceQueries: string[];  // Which queries found this account
  recentTopicPostCount: number;  // Posts in last 30 days
  antiWaveFlags: AntiWaveFlag[];
}
```

**Aggregation Logic:**
- Group posts by author handle
- Count unique keywords matched
- Collect sample posts (most engaged, most recent)
- Track which queries found the account
- Stop aggregating when `max_accounts_to_aggregate` limit reached

### 7. Anti Riding-the-Waves Filter

**Blocklist Keywords (case-insensitive):**
```javascript
const BLOCKLIST_KEYWORDS = [
  'slot', 'judi', 'casino', 'promo', 'onlyfans', 
  'bokep', 'open bo', 'pinjol', 'affiliate',
  'link alternatif', 'daftar gratis', 'bonus'
];
```

**Pattern Detection:**
```javascript
const SPAM_PATTERNS = [
  /\b(wa|whatsapp|telegram|dm)\s*[:\d]/i,  // Contact info spam
  /\b(click|tap)\s*link/i,  // Clickbait
  /\b(free|gratis)\s*.*\b(join|daftar)/i,  // Free signup spam
];
```

**Scoring:**
- Each match adds risk score
- Bio match = +10 (strong signal)
- Display name match = +8
- Profile URL match = +8
- Post content match = +5 per post
- Threshold: 15+ = high risk, 25+ = auto-reject

### 8. Deterministic Prefilter

**Hard Filters (immediate skip):**
```javascript
if (followersCount < min_followers) skip;
if (max_followers && followersCount > max_followers) skip;
if (postCount < min_posts) skip;
if (must_be_verified && !verified) skip;
if (blocklist_keyword_in_bio) skip;
if (blocklist_keyword_in_display_name) skip;
if (blocklist_keyword_in_profile_url) skip;
if (clear_region_mismatch) skip;
```

**Duplicate Detection:**
- Normalize handle: lowercase, strip @
- Track seen handles in current batch
- Skip if already processed in this run

### 8.1 Minimum Accounts Check

After prefilter and anti-wave filtering, validate minimum requirements:

```javascript
if (accountsAfterFiltering < min_accounts_to_evaluate) {
  // Run fails or produces warning
  // Log insufficient accounts error
  // Still produce partial results if possible
}
```

- `min_accounts_to_evaluate` default: 1 (no minimum requirement)
- If set higher, run will trigger auto-loop or fail/warn if disabled
- Useful for ensuring sufficient sample size for meaningful results

### 8.2 Auto-Expansion Loop

When minimum accounts aren't met, the skill can automatically expand the search:

**Loop Algorithm:**

```javascript
async function executeLoop(loopNumber, previousKeywords, capturedAccounts) {
  // 1. Calculate expanded parameters
  const expandedNewsArticles = Math.floor(
    max_news_articles * Math.pow(loop_news_multiplier, loopNumber - 1)
  );
  const expandedKeywords = Math.floor(
    max_keywords * Math.pow(loop_keywords_multiplier, loopNumber - 1)
  );
  
  // 2. Search news with previous keywords as context
  const newsArticles = await searchNewsArticles({
    topic,
    region,
    maxArticles: expandedNewsArticles,
    excludeUrls: previouslyFetchedUrls,
    relatedToKeywords: previousKeywords
  });
  
  // 3. Extract new keywords
  const newKeywords = await extractKeywords(newsArticles, {
    excludeKeywords: previousKeywords,
    maxKeywords: expandedKeywords
  });
  
  // 4. Search X posts
  const xPosts = await searchXPosts({
    queries: buildQueries(topic, region, newKeywords),
    maxPosts: max_x_posts
  });
  
  // 5. Aggregate accounts
  const newAccounts = aggregateAccounts(xPosts);
  
  // 6. Calculate duplicates
  const duplicateCount = newAccounts.filter(acc => 
    capturedAccounts.has(acc.handle_normalized)
  ).length;
  const duplicatePercentage = (duplicateCount / newAccounts.length) * 100;
  
  // 7. Check stopping conditions
  if (duplicatePercentage > duplicate_threshold_percent) {
    return { stoppedReason: 'duplicate_threshold', loopNumber, duplicatePercentage };
  }
  
  // 8. Apply filters and evaluate
  const filteredAccounts = applyFilters(newAccounts);
  const evaluatedAccounts = await evaluateWithAI(filteredAccounts);
  
  // 9. Update captured accounts
  evaluatedAccounts.forEach(acc => capturedAccounts.add(acc.handle_normalized));
  
  // 10. Check if minimum met
  if (capturedAccounts.size >= min_accounts_to_evaluate) {
    return { stoppedReason: 'min_met', loopNumber, totalEvaluated: capturedAccounts.size };
  }
  
  // 11. Check max loops
  if (loopNumber >= max_loops) {
    return { stoppedReason: 'max_loops_reached', loopNumber };
  }
  
  // 12. Continue to next loop
  return executeLoop(loopNumber + 1, [...previousKeywords, ...newKeywords], capturedAccounts);
}
```

**Stopping Conditions:**

1. **min_met**: `totalEvaluated >= min_accounts_to_evaluate`
2. **max_loops_reached**: `loopNumber >= max_loops`
3. **duplicate_threshold**: `duplicatePercentage > duplicate_threshold_percent`
4. **error**: Unrecoverable error in any stage

**Prompt Structure:**
```markdown
# X Account Seed Evaluation

## Task
Evaluate if this X account is a quality seed for monitoring "{topic}" in {region}.

## Context
Topic: {topic}
Region: {region}
Constraints: {constraints}
News Keywords: {keywords}

## Account Profile
Handle: @{handle}
Display Name: {display_name}
Bio: {bio}
Followers: {followers_count}
Verified: {verified}
Location: {location_text}

## Topic Signals
Matched Posts: {matched_posts_count}
Keywords Found: {distinct_keywords_matched}
Entities: {matched_entities}
Sample Posts:
{sample_posts}

## Risk Flags
{anti_wave_flags}

## Evaluation Criteria
ELIGIBLE: Clearly relevant, consistent posts, no spam signals
UNCERTAIN: Weak signals, few posts, incomplete data
NOT_ELIGIBLE: Off-topic, spam, opportunistic, region mismatch

## Important
- Sample posts matter MORE than bio
- Don't select just because big or verified
- Opportunistic accounts get heavy penalty
- Be strict - quality over quantity

## Output Format
Return ONLY valid JSON:
{
  "decision": "eligible|not_eligible|uncertain",
  "score": 0-100,
  "reason_short": "One sentence summary",
  "reason_detailed": "Detailed explanation",
  "matched_topic_signals": ["signal1", "signal2"],
  "risk_flags": ["flag1"],
  "suggested_tags": ["tag1", "tag2"],
  "opportunistic_score": 0-100,
  "consistency_score": 0-100
}
```

**Response Handling:**
- Parse JSON from AI response
- Validate required fields
- Handle missing fields with defaults
- Retry on invalid JSON (max 3 attempts)
- Log errors per candidate

### 9. Per-Account Parallel Evaluation (Account Subagents)

After aggregating topic signals per account, the skill dispatches parallel subagents where EACH subagent handles ALL remaining stages for ONE account end-to-end.

**Architecture:**

```
┌─────────────────────────────────────────────────────────────┐
│              Account Aggregation Complete                   │
│         (Each account has topic signals aggregated)          │
└─────────────────────────────────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Account     │    │  Account     │    │  Account     │
│  Subagent 1  │    │  Subagent 2  │    │  Subagent N  │
│  (Handle A)  │    │  (Handle B)  │    │  (Handle N)  │
└──────────────┘    └──────────────┘    └──────────────┘
         │                     │                     │
    ┌────┴────┐           ┌────┴────┐           ┌────┴────┐
    ▼         ▼           ▼         ▼           ▼         ▼
 Anti-Wave  Prefilter  Anti-Wave  Prefilter  Anti-Wave  Prefilter
    │         │           │         │           │         │
    ▼         ▼           ▼         ▼           ▼         ▼
 Bio Eval   AI Judge   Bio Eval   AI Judge   Bio Eval   AI Judge
    │         │           │         │           │         │
    ▼         ▼           ▼         ▼           ▼         ▼
 Upsert    Result     Upsert    Result     Upsert    Result
    │                     │                     │
    └─────────────────────┼─────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Aggregate All Subagent Results                 │
│                    (eligible/not/uncertain)                 │
└─────────────────────────────────────────────────────────────┘
```

**Each Account Subagent Executes:**

1. **Anti-Wave Filter** - Check for opportunistic/spam signals
2. **Deterministic Prefilter** - Apply hard constraints (followers, posts, verified)
3. **Bio Evaluation** - Evaluate bio/profile metadata (if `use_bio_subagents: true`)
4. **AI Judge Eligibility** - Final comprehensive evaluation
5. **Prepare Database Record** - Format for SQLite upsert

**Process:**

```javascript
async function dispatchAccountSubagents(aggregatedAccounts, config) {
  // 1. Prepare input batch with all account data
  const inputBatch = {
    run_id: config.runId,
    topic: config.topic,
    region: config.region,
    constraints: config.constraints,
    news_keywords: config.news_keywords,
    use_bio_subagents: config.use_bio_subagents,
    accounts: aggregatedAccounts.map(acc => ({
      handle: acc.handle,
      display_name: acc.display_name,
      bio: acc.bio,
      followers_count: acc.followers_count,
      following_count: acc.following_count,
      post_count: acc.post_count,
      verified: acc.verified,
      location_text: acc.location_text,
      profile_url: acc.profile_url,
      joined_at: acc.joined_at,
      // Topic signals
      matched_posts_count: acc.matchedPostsCount,
      distinct_keywords_matched: acc.distinctKeywordsMatched,
      matched_entities: acc.matchedEntities,
      recent_topic_post_count: acc.recentTopicPostCount,
      sample_posts: acc.samplePosts,
      source_queries: acc.sourceQueries
    }))
  };
  
  // 2. Write batch to temp file
  const inputFile = `/tmp/account_batch_${config.runId}.json`;
  await writeJSON(inputFile, inputBatch);
  
  // 3. Dispatch account subagent dispatcher
  const outputFile = `/tmp/account_results_${config.runId}.json`;
  await runAccountDispatcher({
    input: inputFile,
    output: outputFile,
    parallel: config.account_subagent_parallel || 10
  });
  
  // 4. Read and parse results
  const results = await readJSON(outputFile);
  
  // 5. Perform database upserts
  for (const record of results.database_records) {
    await upsertAccount(record.account);
    await insertEvaluation(record.evaluation);
    await insertTopicSignals(record.topic_signals);
  }
  
  return results.summary;
}
```

**Account Evaluation Prompt:**

The account subagent uses `prompts/account_evaluation.md` which guides the AI through ALL stages:
- Stage 1: Anti-wave filter with scoring
- Stage 2: Deterministic prefilter with constraint checks
- Stage 3: Bio evaluation (if enabled)
- Stage 4: Final AI judgment considering all previous stages
- Database record preparation

**Output Schema:**

```json
{
  "handle": "example_user",
  "evaluation_complete": true,
  "stages": {
    "anti_wave": {
      "score": 0,
      "flags": [],
      "decision": "pass"
    },
    "prefilter": {
      "passed": true,
      "failed_constraints": [],
      "decision": "continue"
    },
    "bio_evaluation": {
      "decision": "eligible",
      "score": 85,
      "relevance_signals": ["signal1"],
      "account_type_indicators": ["individual"],
      "risk_flags": []
    },
    "final_judgment": {
      "decision": "eligible",
      "score": 88,
      "reason_short": "...",
      "reason_detailed": "...",
      "matched_topic_signals": ["..."],
      "risk_flags": [],
      "suggested_tags": ["..."],
      "opportunistic_score": 5,
      "consistency_score": 85
    }
  },
  "database_record": {
    "account": { /* SQLite accounts table data */ },
    "evaluation": { /* SQLite account_evaluations table data */ },
    "topic_signals": { /* SQLite account_topic_signals table data */ }
  }
}
```

**Performance:**

- Default parallelism: 10 concurrent account subagents
- Configurable: 1-50 parallel subagents via `account_subagent_parallel`
- Each subagent processes ONE account end-to-end
- Typical latency: 3-8 seconds per account
- Scales linearly with parallel count
- 100 accounts with parallel=10 completes in ~30-80 seconds

**Error Handling:**

- Individual subagent failures don't stop the batch
- Failed evaluations logged but don't block others
- Database upsert happens after all subagents complete
- Timeout per subagent: 60 seconds
- Partial results saved even if some accounts fail

**Benefits:**

- **True Parallelism** - Each account processed independently
- **End-to-End Isolation** - No shared state between accounts
- **Better Resource Utilization** - CPU/network used efficiently
- **Scalable** - Handle 50-100+ accounts simultaneously
- **Fault Tolerant** - One failure doesn't affect others

### 10. SQLite Persistence

**Connection Management:**
- Single connection per run
- WAL mode for better concurrency
- Foreign keys enabled

**Upsert Logic:**
```sql
-- Accounts: Insert or update
INSERT INTO accounts (handle, handle_normalized, ...)
VALUES (?, ?, ...)
ON CONFLICT(handle_normalized) DO UPDATE SET
  display_name = excluded.display_name,
  bio = excluded.bio,
  followers_count = excluded.followers_count,
  ...
  last_seen_at = CURRENT_TIMESTAMP;

-- Evaluations: Always insert new
INSERT INTO account_evaluations (...)
VALUES (...);
```

**Transaction Boundaries:**
- Each account evaluation = one transaction
- Run metadata update = separate transaction
- Batch inserts for keywords/articles

### 11. Export Functionality

**Query Patterns:**
```sql
-- Basic eligible export
SELECT a.handle, a.display_name, a.followers_count,
       ae.score, ae.reason_short, ae.suggested_tags_json
FROM accounts a
JOIN account_evaluations ae ON a.id = ae.account_id
WHERE ae.decision = 'eligible'
  AND ae.topic = ?
  AND ae.region = ?
  AND ae.score >= ?
ORDER BY ae.score DESC;

-- Full audit export
SELECT r.id as run_id, r.started_at, a.handle, 
       ae.decision, ae.score, ae.reason_detailed,
       ats.matched_posts_count, ats.sample_posts_json
FROM runs r
JOIN account_evaluations ae ON r.id = ae.run_id
JOIN accounts a ON ae.account_id = a.id
JOIN account_topic_signals ats ON a.id = ats.account_id AND r.id = ats.run_id
WHERE r.topic = ?;
```

## Error Handling Strategy

### Error Classification

**Fatal Errors (stop run):**
- Database connection failure
- Schema initialization failure
- Invalid input (schema validation fails)

**Recoverable Errors (log and continue):**
- Single news article fetch fails
- Single X post search fails
- Single AI evaluation fails (invalid JSON)
- Single account upsert fails

**Partial Success (produce summary):**
- Some stages complete, others fail
- Include completed stats in output
- List errors in `errors` array

### Retry Logic

**AI Evaluation:**
- Invalid JSON: Retry with "Return ONLY JSON" reminder
- Max 3 retries
- Backoff: immediate, 1s, 2s
- After retries: Mark as error, continue

**Provider Calls:**
- Rate limit: Exponential backoff (1s, 2s, 4s)
- Timeout: Retry once
- Auth failure: Fatal (config issue)

## Performance Considerations

### Database
- Indexes on: handle_normalized, run_id, decision, topic, region
- WAL mode for write performance
- Batch inserts for keywords/articles (100 at a time)

### API Calls
- Parallel where possible (news articles)
- Sequential for rate-limited APIs (X search)
- Connection pooling if supported

### Memory
- Stream large result sets
- Process accounts in batches (50-100 at a time)
- Clear sample posts after evaluation to free memory

## Security

### Credential Management
- No hardcoded credentials in skill
- Use environment variables
- Support runtime-specific credential stores

### Data Sanitization
- Handle normalization prevents injection
- JSON schema validation on input
- No raw SQL concatenation (parameterized only)

### Logging
- Never log credentials
- Log handles at INFO level
- Log full evaluation context at DEBUG level

## Playwright Scripts

### Overview

For environments with direct Playwright access, standalone scripts provide an alternative to API-based providers:

| Script | Purpose | Requirements |
|--------|---------|--------------|
| `search_news.py` | DuckDuckGo news search | requests, beautifulsoup4 |
| `search_nitter.py` | X/Twitter via Nitter | Playwright, playwright-stealth |
| `chrome_profile.py` | Chrome profile management | Chrome browser |

### search_nitter.py

**Purpose:** Search X/Twitter via Nitter instances using Playwright with Chrome profile.

**Nitter Instances Used:**
- Primary: https://nitter.net (official)
- Fallbacks: xcancel.com, nitter.privacyredirect.com, nitter.poast.org, nitter.tiekoetter.com
- See https://github.com/zedeus/nitter/wiki/Instances for status

**Key Features:**
- **Chrome Profile Support:** Uses persistent Chrome profile for authentication state
- **Stealth Mode:** playwright-stealth to avoid detection
- **Cloudflare Wait:** Detects and waits for verification challenges
- **Instance Failover:** Automatic retry on different instances
- **Rate Limiting:** Built-in delays and human-like behavior

**Usage:**
```bash
# Search posts
python search_nitter.py search --query "politics Indonesia" --max-results 50

# Get profile
python search_nitter.py profile prabowo --output profile.json

# Use specific instance
python search_nitter.py --instance xcancel.com search --query "test"
```

**Why Nitter over sotwe.com:**
- Open-source with multiple instances (better redundancy)
- Consistent API/layout across instances
- Active community maintenance
- Better documented and stable

### Chrome Profile Management

**Default Location:** `~/.x-discovery/chrome-profile`

**Benefits:**
- Persists cookies and login sessions
- Isolates automation from main Chrome
- Allows pre-authentication to sites
- Reduces detection risk

**Commands:**
```bash
python chrome_profile.py create  # Create profile
python chrome_profile.py test    # Test with Chrome
python chrome_profile.py info    # Show profile info
```

## Testing Strategy

### Unit Tests
- Input validation
- Handle normalization
- Blocklist pattern matching
- Query building

### Integration Tests
- End-to-end with mock providers
- SQLite operations
- AI prompt rendering

### Validation Tests
- Idempotency: Rerun produces no duplicates
- Anti-wave: Known spam accounts rejected
- Region handling: Default and override work

## Extension Points

### Adding New Provider
1. Implement `NewsSearchProvider` or `XSearchProvider` interface
2. Add provider configuration
3. Register in provider factory
4. Update input schema with provider-specific options

### Custom Anti-Wave Rules
1. Add patterns to blocklist
2. Implement custom `AntiWaveScorer`
3. Update risk threshold

### Custom AI Prompt
1. Copy `prompts/seed_judge.md`
2. Modify evaluation criteria
3. Pass via `custom_prompt_appendix` or override

## Monitoring & Observability

### Metrics to Track
- Run duration per stage
- Success rate by provider
- AI evaluation latency
- Duplicate rate
- Anti-wave rejection rate
- Eligible rate by topic

### Logging Levels
- ERROR: Fatal errors, unrecoverable failures
- WARN: Recoverable errors, retries
- INFO: Run start/end, stage completion, counts
- DEBUG: Individual account processing, AI prompts

## Deployment

### As Claude Code Skill
1. Place in `skills/x_account_seed_discovery/`
2. Reference via `@x_account_seed_discovery`
3. Pass parameters in natural language or JSON

### As Opencode Skill
1. Place in skills directory
2. Register in `opencode.yaml`
3. Run via `opencode run skill x_account_seed_discovery`

### As Standalone Tool
1. Import orchestrator function
2. Call with input object
3. Handle output and errors

## Version History

- v1.0: Initial release
  - News-first workflow
  - Anti-wave filtering
  - SQLite persistence
  - AI evaluation
  - Export functionality
