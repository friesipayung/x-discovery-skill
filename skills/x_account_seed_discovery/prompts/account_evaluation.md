# X Account End-to-End Evaluation Prompt

## Task
Evaluate this X (Twitter) account as a quality seed candidate for monitoring "{{topic}}" in {{region}}. Process through ALL stages: anti-wave filter → deterministic prefilter → bio evaluation → final AI judgment → prepare for database upsert.

**You are a complete evaluation pipeline for ONE account. Execute all stages and return the final result.**

## Context

**Topic:** {{topic}}
**Region:** {{region}}
**Operator Constraints:** {{constraints}}

**News Keywords & Entities:**
{{news_keywords}}

## Account Data

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

---

## STAGE 1: Anti Riding-the-Waves Filter

Check for opportunistic accounts that hijack trending topics.

**Blocklist Keywords (case-insensitive):**
- slot, judi, casino, promo, onlyfans, bokep, open bo, pinjol, affiliate
- link alternatif, daftar gratis, bonus

**Spam Patterns:**
- Contact info spam: "wa", "whatsapp", "telegram", "dm" followed by numbers
- Clickbait: "click link", "tap link"
- Free signup spam: "free join", "gratis daftar"

**Scoring:**
- Bio match = +10 points (strong signal)
- Display name match = +8 points
- Profile URL match = +8 points
- Post content match = +5 points per post

**Anti-Wave Decision:**
- 0-14 points: PASS (low risk)
- 15-24 points: FLAG (moderate risk, note in evaluation)
- 25+ points: AUTO-REJECT (high risk, spam/opportunistic)

**Record your findings:**
- anti_wave_score: (0-100)
- anti_wave_flags: [list any matches found]
- anti_wave_decision: "pass" | "flag" | "reject"

---

## STAGE 2: Deterministic Prefilter

Apply hard constraints. If ANY check fails, mark as "filtered" and skip to final output.

**Checks:**
1. **Min Followers:** {{min_followers}} → Current: {{followers_count}} → Status: [PASS/FAIL]
2. **Max Followers:** {{max_followers}} → Current: {{followers_count}} → Status: [PASS/FAIL/N/A]
3. **Min Posts:** {{min_posts}} → Current: {{post_count}} → Status: [PASS/FAIL/N/A]
4. **Must Be Verified:** {{must_be_verified}} → Current: {{verified}} → Status: [PASS/FAIL/N/A]
5. **Anti-Wave Reject:** From Stage 1 → Status: [PASS/FAIL]

**Prefilter Decision:**
- If ALL checks PASS → Continue to Stage 3
- If ANY check FAILS → Mark as "filtered", note which constraint failed, prepare final output

---

## STAGE 3: Bio Evaluation (Internal)

Evaluate bio and profile metadata for individual account indicators and topic relevance.

**Individual Account Indicators (look for):**
- Personal display names (not institutional)
- First-person language in bio (I, my, me)
- Personal interests, hobbies, roles mentioned
- Handle doesn't contain: "official", "gov", "kemen", "bps", "kpu", "dpr", "news", "media"

**Organization/Government Indicators (reject):**
- Bio uses institutional language ("Official account of...", "Akses informasi resmi...")
- Handle contains government/org keywords
- Display name is organization, not person
- Bio describes entity mission, not personal identity

**Bio Relevance Signals:**
- Keywords related to {{topic}} in bio
- Professional role related to topic
- Location in {{region}}

**Record your findings:**
- bio_decision: "eligible" | "not_eligible" | "uncertain"
- bio_score: (0-100)
- bio_relevance_signals: [list of signals found]
- account_type_indicators: ["individual" indicators or "organization" indicators]
- bio_risk_flags: [any concerns]

---

## STAGE 4: Final AI Judgment

Make comprehensive evaluation considering ALL previous stages.

### Target: Individual Real Users Only
**Explicitly EXCLUDED:**
- Government accounts (presidents, ministries, official gov handles)
- Organization/Institution accounts (political parties, NGOs, companies)
- Media/News outlets (official news accounts)
- Corporate/Brand accounts

### Evaluation Criteria

**ELIGIBLE (Quality Seed Account):**
- Account is clearly relevant to "{{topic}}"
- Account is relevant to {{region}} or discusses issues applicable to the region
- Account represents an **individual person** (not government/org/brand)
- Sample posts demonstrate consistent topical relevance
- No significant spam/promo/porn/gambling signals (or minimal, explainable)
- Worthy of monitoring as a seed for ongoing crawling
- Bio evaluation supports individual status

**UNCERTAIN (Needs Review):**
- Weak relevance signals
- Too few sample posts for confident judgment
- Incomplete metadata
- Mixed signals (some relevance, some concerns)
- Bio evaluation unclear

**NOT_ELIGIBLE (Reject):**
- Government/Organization/Institution/Brand account (auto-reject regardless of relevance)
- Off-topic or irrelevant to "{{topic}}"
- Dominant spam/promo/porn/gambling/clickbait content
- Highly opportunistic (riding trends without genuine interest)
- Clear region mismatch
- Failed deterministic prefilter
- Anti-wave score 25+ (auto-reject)

### Critical Instructions

**DO NOT select just because:**
- Many followers
- Verified status
- Bio mentions topic keywords
- "Big name" account

**DO prioritize:**
- Sample posts over bio claims
- Consistency over one viral post
- Quality engagement over quantity
- Genuine discussion over keyword stuffing
- Individual status over institutional accounts

**Consider Previous Stages:**
- Anti-wave flags should heavily penalize opportunistic accounts
- Prefilter failures are hard stops
- Bio evaluation provides important context but sample posts matter more

---

## Output Format

Return ONLY a valid JSON object with this exact structure:

```json
{
  "handle": "{{handle}}",
  "evaluation_complete": true,
  "stages": {
    "anti_wave": {
      "score": 0-100,
      "flags": ["flag1", "flag2"],
      "decision": "pass|flag|reject"
    },
    "prefilter": {
      "passed": true|false,
      "failed_constraints": ["constraint1"],
      "decision": "continue|filtered"
    },
    "bio_evaluation": {
      "decision": "eligible|not_eligible|uncertain",
      "score": 0-100,
      "relevance_signals": ["signal1", "signal2"],
      "account_type_indicators": ["indicator1"],
      "risk_flags": ["flag1"]
    },
    "final_judgment": {
      "decision": "eligible|not_eligible|uncertain",
      "score": 0-100,
      "reason_short": "One clear sentence summarizing the decision",
      "reason_detailed": "Detailed explanation citing specific evidence from all stages",
      "matched_topic_signals": ["signal1", "signal2", "signal3"],
      "risk_flags": ["flag1", "flag2"],
      "suggested_tags": ["tag1", "tag2", "tag3"],
      "opportunistic_score": 0-100,
      "consistency_score": 0-100
    }
  },
  "database_record": {
    "account": {
      "handle": "{{handle}}",
      "handle_normalized": "{{handle}}",
      "display_name": "{{display_name}}",
      "bio": "{{bio}}",
      "followers_count": {{followers_count}},
      "following_count": {{following_count}},
      "post_count": {{post_count}},
      "verified": {{verified}},
      "location_text": "{{location_text}}",
      "profile_url": "{{profile_url}}",
      "joined_at": "{{joined_at}}"
    },
    "evaluation": {
      "decision": "eligible|not_eligible|uncertain",
      "score": 0-100,
      "reason_short": "...",
      "reason_detailed": "...",
      "suggested_tags_json": "[\"tag1\", \"tag2\"]",
      "opportunistic_score": 0-100,
      "consistency_score": 0-100
    },
    "topic_signals": {
      "matched_posts_count": {{matched_posts_count}},
      "distinct_keywords_matched": "[\"keyword1\", \"keyword2\"]",
      "matched_entities": "[\"entity1\", \"entity2\"]",
      "sample_posts_json": "...",
      "recent_topic_post_count": {{recent_topic_post_count}}
    }
  }
}
```

### Field Definitions:

**Stages Section:**
- `anti_wave.score`: Risk score from blocklist/pattern matching
- `anti_wave.flags`: List of specific flags triggered
- `anti_wave.decision`: "pass" (continue), "flag" (note but continue), "reject" (stop)
- `prefilter.passed`: Whether all hard constraints passed
- `prefilter.failed_constraints`: Which constraints failed (if any)
- `bio_evaluation`: Structured bio analysis results
- `final_judgment`: Complete evaluation with all fields from seed_judge.md

**Database Record Section:**
- `account`: All account metadata for SQLite upsert
- `evaluation`: Final judgment data for account_evaluations table
- `topic_signals`: Aggregated signals for account_topic_signals table

---

## Examples

### Example 1: Eligible Political Commentator (All Stages Pass)
```json
{
  "handle": "political_analyst_id",
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
      "relevance_signals": ["bio mentions 'political analyst'", "bio mentions 'Indonesian governance'"],
      "account_type_indicators": ["personal name in display name", "first-person bio language"],
      "risk_flags": []
    },
    "final_judgment": {
      "decision": "eligible",
      "score": 88,
      "reason_short": "Consistent political commentary with substantive policy analysis.",
      "reason_detailed": "Account regularly posts about Indonesian politics with original analysis. Bio confirms professional expertise. No spam or opportunistic signals. Anti-wave and prefilter passed. Individual account with genuine topical interest.",
      "matched_topic_signals": ["DPR legislation analysis", "policy commentary", "government news sharing"],
      "risk_flags": [],
      "suggested_tags": ["politics", "indonesia", "analyst", "policy"],
      "opportunistic_score": 5,
      "consistency_score": 85
    }
  },
  "database_record": {
    "account": {
      "handle": "political_analyst_id",
      "handle_normalized": "political_analyst_id",
      "display_name": "Budi Santoso",
      "bio": "Political analyst & writer. Focusing on Indonesian governance and policy.",
      "followers_count": 15000,
      "following_count": 1200,
      "post_count": 3500,
      "verified": false,
      "location_text": "Jakarta, Indonesia",
      "profile_url": "https://x.com/political_analyst_id",
      "joined_at": "2018-05-20"
    },
    "evaluation": {
      "decision": "eligible",
      "score": 88,
      "reason_short": "Consistent political commentary with substantive policy analysis.",
      "reason_detailed": "Account regularly posts about Indonesian politics with original analysis. Bio confirms professional expertise. No spam or opportunistic signals.",
      "suggested_tags_json": "[\"politics\", \"indonesia\", \"analyst\", \"policy\"]",
      "opportunistic_score": 5,
      "consistency_score": 85
    },
    "topic_signals": {
      "matched_posts_count": 12,
      "distinct_keywords_matched": "[\"DPR\", \"presiden\", \"politik\"]",
      "matched_entities": "[\"DPR\", \"Jokowi\"]",
      "sample_posts_json": "[{...}]",
      "recent_topic_post_count": 8
    }
  }
}
```

### Example 2: Not Eligible - Government Account (Prefilter or Bio Rejection)
```json
{
  "handle": "kemenkes_id",
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
      "decision": "not_eligible",
      "score": 5,
      "relevance_signals": ["bio mentions government policy"],
      "account_type_indicators": [],
      "risk_flags": ["government handle pattern", "institutional bio language", "official ministry account"]
    },
    "final_judgment": {
      "decision": "not_eligible",
      "score": 5,
      "reason_short": "Official government ministry account - institutional, not individual.",
      "reason_detailed": "Handle contains 'kemenkes' (Ministry of Health). Bio states 'Official account of Ministry of Health Indonesia'. This is a government institution account, explicitly excluded by criteria. Auto-rejected regardless of relevance.",
      "matched_topic_signals": ["government health policy mentions"],
      "risk_flags": ["government account", "institutional account", "not individual"],
      "suggested_tags": ["government", "institution", "health"],
      "opportunistic_score": 0,
      "consistency_score": 90
    }
  },
  "database_record": {
    "account": {
      "handle": "kemenkes_id",
      "handle_normalized": "kemenkes_id",
      "display_name": "Kementerian Kesehatan RI",
      "bio": "Official account of Ministry of Health Indonesia...",
      "followers_count": 2500000,
      "following_count": 50,
      "post_count": 12000,
      "verified": true,
      "location_text": "Jakarta",
      "profile_url": "https://x.com/kemenkes_id",
      "joined_at": "2015-01-10"
    },
    "evaluation": {
      "decision": "not_eligible",
      "score": 5,
      "reason_short": "Official government ministry account - institutional, not individual.",
      "reason_detailed": "Handle contains 'kemenkes' (Ministry of Health). Bio states 'Official account'. Government institution account, explicitly excluded.",
      "suggested_tags_json": "[\"government\", \"institution\", \"health\"]",
      "opportunistic_score": 0,
      "consistency_score": 90
    },
    "topic_signals": {
      "matched_posts_count": 3,
      "distinct_keywords_matched": "[\"kesehatan\", \"policy\"]",
      "matched_entities": "[\"Kemenkes\"]",
      "sample_posts_json": "[{...}]",
      "recent_topic_post_count": 2
    }
  }
}
```

### Example 3: Not Eligible - Spam Account (Anti-Wave Rejection)
```json
{
  "handle": "slot_gacor_99",
  "evaluation_complete": true,
  "stages": {
    "anti_wave": {
      "score": 45,
      "flags": ["spam_keywords_in_bio: slot", "spam_keywords_in_bio: link alternatif", "promotional language dominant"],
      "decision": "reject"
    },
    "prefilter": {
      "passed": false,
      "failed_constraints": ["anti_wave_reject"],
      "decision": "filtered"
    },
    "bio_evaluation": {
      "decision": "not_eligible",
      "score": 10,
      "relevance_signals": [],
      "account_type_indicators": [],
      "risk_flags": ["spam keywords in bio", "promotional language", "gambling references"]
    },
    "final_judgment": {
      "decision": "not_eligible",
      "score": 10,
      "reason_short": "Promotional gambling account with heavy spam signals.",
      "reason_detailed": "Anti-wave score 45 with multiple spam flags. Bio contains 'slot gacor', 'link alternatif', 'bonus 100%'. Clearly a promotional/gambling account. Auto-rejected by anti-wave filter.",
      "matched_topic_signals": [],
      "risk_flags": ["spam keywords", "promotional content", "gambling", "anti-wave auto-reject"],
      "suggested_tags": ["spam", "promotional", "gambling"],
      "opportunistic_score": 95,
      "consistency_score": 10
    }
  },
  "database_record": {
    "account": {
      "handle": "slot_gacor_99",
      "handle_normalized": "slot_gacor_99",
      "display_name": "SLOT GACOR 2024",
      "bio": "Link alternatif slot gacor terpercaya! Bonus 100%...",
      "followers_count": 500,
      "following_count": 10,
      "post_count": 50,
      "verified": false,
      "location_text": "",
      "profile_url": "https://x.com/slot_gacor_99",
      "joined_at": "2024-01-15"
    },
    "evaluation": {
      "decision": "not_eligible",
      "score": 10,
      "reason_short": "Promotional gambling account with heavy spam signals.",
      "reason_detailed": "Anti-wave score 45 with multiple spam flags. Promotional/gambling account. Auto-rejected.",
      "suggested_tags_json": "[\"spam\", \"promotional\", \"gambling\"]",
      "opportunistic_score": 95,
      "consistency_score": 10
    },
    "topic_signals": {
      "matched_posts_count": 1,
      "distinct_keywords_matched": "[]",
      "matched_entities": "[]",
      "sample_posts_json": "[{...}]",
      "recent_topic_post_count": 0
    }
  }
}
```

---

## Your Evaluation

Now process this account through ALL stages and return ONLY the complete JSON object:
