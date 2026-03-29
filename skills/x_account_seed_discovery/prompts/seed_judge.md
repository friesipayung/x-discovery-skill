# X Account Seed Evaluation Prompt

## Task
Evaluate whether this X (Twitter) account is a quality seed account for monitoring the topic "{{topic}}" in {{region}}.

## Context

**Topic:** {{topic}}
**Region:** {{region}}
**Operator Constraints:** {{constraints}}

**News Keywords & Entities:**
{{news_keywords}}

## Account Profile

**Handle:** @{{handle}}
**Display Name:** {{display_name}}
**Bio:** {{bio}}
**Followers:** {{followers_count}}
**Following:** {{following_count}}
**Posts:** {{post_count}}
**Verified:** {{verified}}
**Location:** {{location_text}}
**Profile URL:** {{profile_url}}
**Joined:** {{joined_at}}

## Topic Signals

**Matched Posts Count:** {{matched_posts_count}}
**Distinct Keywords Matched:** {{distinct_keywords_matched}}
**Entities Found:** {{matched_entities}}
**Recent Topic Posts (30 days):** {{recent_topic_post_count}}

**Sample Posts:**
{{sample_posts}}

**Source Queries (how this account was found):**
{{source_queries}}

## Risk Flags (from Anti-Wave Filter)

{{anti_wave_flags}}

## Evaluation Criteria

### ELIGIBLE (Quality Seed Account)
Use when ALL of these are true:
- Account is clearly relevant to the topic "{{topic}}"
- Account is relevant to {{region}} or discusses national/global issues applicable to the region
- Sample posts demonstrate consistent topical relevance (not just one-off mentions)
- Account shows no significant spam, promotional, pornographic, gambling, or trend-hijacking signals
- Account appears to be a genuine content creator, news source, or relevant participant in the topic space
- Account is worth monitoring as a seed for ongoing crawling

### UNCERTAIN (Needs Review)
Use when:
- There are signals of relevance, but evidence is weak or ambiguous
- Sample posts are too few to make a confident judgment
- Account metadata is incomplete or suspicious
- Account might be relevant, but there's not enough proof to mark as eligible
- Mixed signals - some relevance, but also some noise or concerns

### NOT_ELIGIBLE (Reject)
Use when ANY of these are true:
- Account is clearly off-topic or irrelevant to "{{topic}}"
- Dominant content is spam, promotional, pornographic, gambling-related, or clickbait
- Account is highly opportunistic (only mentions topic to ride trending waves)
- Clear region mismatch (account is exclusively about another region with no relevance to {{region}})
- Account only uses topic keywords without substantive engagement with the subject
- Bio claims relevance but posts don't demonstrate it
- Account exists primarily for engagement farming, affiliate marketing, or lead generation

## Critical Instructions

**DO NOT select an account just because:**
- It has many followers
- It is verified
- Its bio mentions the topic keywords
- It is a "big name" account

**DO prioritize:**
- Sample posts over bio claims
- Consistency over one viral post
- Quality of engagement over quantity
- Genuine topical discussion over keyword stuffing

**Opportunistic/Trend Hijacker Penalty:**
Accounts that appear to be "riding the waves" - mentioning trending topics only for engagement without genuine interest - should receive a heavy penalty. Look for:
- Hashtag stuffing unrelated to account's normal content
- Sudden topic shifts to whatever is trending
- Promotional content mixed with serious topics
- Generic engagement-bait language

## Output Format

Return ONLY a valid JSON object with this exact structure:

```json
{
  "decision": "eligible|not_eligible|uncertain",
  "score": 0-100,
  "reason_short": "One clear sentence summarizing the decision",
  "reason_detailed": "Detailed explanation of the evaluation, citing specific evidence from sample posts and profile",
  "matched_topic_signals": ["signal1", "signal2", "signal3"],
  "risk_flags": ["flag1", "flag2"],
  "suggested_tags": ["tag1", "tag2", "tag3"],
  "opportunistic_score": 0-100,
  "consistency_score": 0-100
}
```

### Field Definitions:

- **decision**: Must be exactly "eligible", "not_eligible", or "uncertain"
- **score**: Overall quality score (0-100). Eligible accounts typically 70+, uncertain 40-69, not_eligible 0-39
- **reason_short**: One sentence that could be shown in a summary table
- **reason_detailed**: 2-4 sentences explaining the reasoning with specific evidence
- **matched_topic_signals**: Array of specific signals showing relevance (e.g., "discusses DPR legislation", "shares policy analysis")
- **risk_flags**: Array of any concerns or red flags (e.g., "mixes political content with product promos", "hashtag spam")
- **suggested_tags**: Array of tags for categorizing this account (e.g., "politics", "journalist", "activist")
- **opportunistic_score**: How opportunistic/trend-hijacking is this account? (0 = genuine, 100 = pure opportunist)
- **consistency_score**: How consistent is the account's topical relevance? (0 = random, 100 = consistently on-topic)

## Examples

### Example 1: Eligible Political Commentator
```json
{
  "decision": "eligible",
  "score": 88,
  "reason_short": "Consistent political commentary with substantive policy analysis.",
  "reason_detailed": "Account regularly posts about Indonesian politics, DPR legislation, and government policy. Sample posts show original analysis and engagement with current issues. No promotional content or spam signals detected. Bio and content align well.",
  "matched_topic_signals": ["DPR legislation analysis", "policy commentary", "government news sharing", "political debate participation"],
  "risk_flags": [],
  "suggested_tags": ["politics", "indonesia", "commentator", "policy"],
  "opportunistic_score": 5,
  "consistency_score": 85
}
```

### Example 2: Not Eligible - Opportunistic Promoter
```json
{
  "decision": "not_eligible",
  "score": 15,
  "reason_short": "Primarily promotional account opportunistically using political keywords.",
  "reason_detailed": "While account occasionally mentions political keywords, the dominant content is promotional posts for products and services. Political mentions appear to be hashtag stuffing for engagement rather than genuine interest. Bio contains promotional language and affiliate indicators.",
  "matched_topic_signals": ["occasional political keyword mention"],
  "risk_flags": ["dominant promotional content", "hashtag stuffing", "affiliate marketing bio", "engagement bait"],
  "suggested_tags": ["promotional", "spam"],
  "opportunistic_score": 85,
  "consistency_score": 10
}
```

### Example 3: Uncertain - Insufficient Data
```json
{
  "decision": "uncertain",
  "score": 55,
  "reason_short": "Some relevant posts but limited sample size and mixed signals.",
  "reason_detailed": "Account shows genuine interest in topic with a few substantive posts, but sample size is too small for confident judgment. Recent activity suggests possible relevance, but need more data to confirm consistency and rule out opportunistic behavior.",
  "matched_topic_signals": ["relevant post found", "topical engagement"],
  "risk_flags": ["limited sample size", "inconsistent posting pattern"],
  "suggested_tags": ["politics", "needs-review"],
  "opportunistic_score": 40,
  "consistency_score": 45
}
```

## Your Evaluation

Now evaluate this account and return ONLY the JSON object:
