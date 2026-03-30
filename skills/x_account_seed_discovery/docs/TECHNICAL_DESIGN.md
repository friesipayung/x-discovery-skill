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
- X API v2 (if available)
- Web scraping fallback (Nitter, etc.)
- Query rotation to maximize coverage
- Rate limiting and retry logic

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
- If set higher, run will fail/warn if fewer accounts pass all filters
- Useful for ensuring sufficient sample size for meaningful results

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
