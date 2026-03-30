# X Account Bio Evaluation Prompt

## Task
Evaluate whether this X (Twitter) account's bio and profile metadata indicate it could be a quality seed account for monitoring the topic "{{topic}}" in {{region}}.

**Focus:** This evaluation is based SOLELY on bio, profile metadata, and handle patterns. Sample posts are NOT provided - judge based on profile signals only.

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

## Risk Flags (from Anti-Wave Filter)

{{anti_wave_flags}}

## Evaluation Criteria

### Target: Individual Real Users Only
This skill focuses on discovering **individual human accounts** sharing personal perspectives and opinions.

**Explicitly EXCLUDED (reject these):**
- Government accounts (presidents, ministries, official gov handles like @jokowi, @kemenkes, @kpu_id, @dpr_ri, @bps_statistics)
- Organization/Institution accounts (political parties like @pdi_perjuangan, @gerindra, NGOs, companies)
- Media/News outlets (official news accounts like @kompascom, @detikcom, @tvOneNews)
- Corporate/Brand accounts
- Bot or automated accounts

**Look for indicators of INDIVIDUAL accounts:**
- Personal display names (not institutional)
- Bio describes a person, not an organization
- First-person language in bio
- Personal interests, hobbies, or roles mentioned
- Handle doesn't contain "official", "gov", "kemen", "bps", "kpu", "dpr", "news", "media", "tv", "radio"
- Location suggests personal residence, not office/headquarters

### ELIGIBLE (Quality Seed Candidate)
Use when ALL of these are true:
- Bio suggests account represents an **individual person** (not government, organization, institution, or brand)
- Bio contains signals of relevance to "{{topic}}" OR handle/display name suggests topical interest
- No strong indicators of being an organization, government, or brand account
- No significant spam, promotional, pornographic, gambling signals in bio
- Account appears to be a genuine person who might discuss this topic

**Bio relevance signals to look for:**
- Keywords related to {{topic}} in bio
- Professional role related to topic (e.g., "journalist", "analyst", "activist")
- Personal interests aligned with topic
- Location in {{region}} or connection to region

### NOT_ELIGIBLE - Government/Organization (Auto-reject)
Reject when account appears to be:
- **Government accounts:** Handles containing "gov", "kemen", "bps", "kpu", "dpr", "pemerintah", "official" government terms
- **Political party accounts:** Party names in handle or bio
- **Institutional accounts:** Universities, government agencies, official bodies
- **Media/News organization accounts:** News outlet names, "com", "news", "tv", "radio" in handle
- **Corporate/Brand accounts:** Company names, product mentions, brand language
- **NGO/Organization accounts:** Organization names, "foundation", "institute", "association"

**Key indicators:**
- Bio uses institutional language ("Official account of...", "Akses informasi resmi...", "Media partner...")
- Handle contains government/org keywords
- Display name is an organization name, not a person's name
- Bio describes an entity's mission, not a person's identity

### UNCERTAIN (Needs Review)
Use when:
- Bio is empty, minimal, or unclear
- Mixed signals - could be individual or could be organization
- Bio is private or contains only emojis/links
- Insufficient information to make confident judgment
- Account might be relevant but bio doesn't clearly indicate topical interest

### NOT_ELIGIBLE (Reject - General)
Use when ANY of these are true:
- Bio contains spam/promotional signals: "slot", "judi", "casino", "promo", "onlyfans", "bokep", "open bo", "pinjol", "affiliate", "link alternatif", "daftar gratis", "bonus"
- Bio is clearly off-topic with no relevance signals
- Account is clearly a bot or automated (indicated in bio)
- Strong region mismatch (bio explicitly states different region with no connection to {{region}})

## Critical Instructions

**DO NOT select an account just because:**
- It has many followers
- It is verified
- It has a professional-sounding bio

**DO prioritize:**
- Clear individual person indicators over ambiguous signals
- Bio relevance to topic over generic professional bios
- Personal language over institutional language

**Bio Analysis Tips:**
- Look for personal pronouns (I, my, me) as individual indicators
- Look for job titles that suggest topical expertise
- Check if location matches {{region}}
- Be skeptical of bios that only contain contact info or links
- Reject if bio contains multiple spam keywords

## Output Format

Return ONLY a valid JSON object with this exact structure:

```json
{
  "decision": "eligible|not_eligible|uncertain",
  "score": 0-100,
  "reason_short": "One clear sentence summarizing the decision based on bio analysis",
  "reason_detailed": "Detailed explanation citing specific bio elements and handle patterns",
  "bio_relevance_signals": ["signal1", "signal2", "signal3"],
  "account_type_indicators": ["individual_indicator1", "individual_indicator2"],
  "risk_flags": ["flag1", "flag2"],
  "suggested_tags": ["tag1", "tag2", "tag3"]
}
```

### Field Definitions:

- **decision**: Must be exactly "eligible", "not_eligible", or "uncertain"
- **score**: Overall quality score based on bio (0-100). Eligible accounts typically 70+, uncertain 40-69, not_eligible 0-39
- **reason_short**: One sentence summarizing the bio-based decision
- **reason_detailed**: 2-4 sentences explaining the reasoning with specific bio evidence
- **bio_relevance_signals**: Array of specific bio elements showing topic relevance (e.g., "bio mentions 'politics'", "handle contains 'analyst'")
- **account_type_indicators**: Array of indicators showing this is an individual (e.g., "personal name in display name", "first-person bio language")
- **risk_flags**: Array of concerns from bio analysis (e.g., "institutional language detected", "spam keywords in bio")
- **suggested_tags**: Array of tags for categorizing this account (e.g., "politics", "journalist", "activist")

## Examples

### Example 1: Eligible - Political Commentator
```json
{
  "decision": "eligible",
  "score": 82,
  "reason_short": "Individual political analyst with clear topical focus in bio.",
  "reason_detailed": "Bio identifies account holder as 'Political analyst & writer' with focus on Indonesian governance. Display name is a personal name. Handle suggests professional but individual identity. No institutional language detected. Location listed as Jakarta, Indonesia.",
  "bio_relevance_signals": ["bio mentions 'political analyst'", "bio mentions 'Indonesian governance'", "professional role related to topic"],
  "account_type_indicators": ["personal name in display name", "first-person bio language ('I write')", "individual professional role"],
  "risk_flags": [],
  "suggested_tags": ["politics", "indonesia", "analyst", "writer"]
}
```

### Example 2: Not Eligible - Government Account
```json
{
  "decision": "not_eligible",
  "score": 5,
  "reason_short": "Official government ministry account - institutional, not individual.",
  "reason_detailed": "Handle contains 'kemenkes' (Ministry of Health). Bio states 'Official account of Ministry of Health Indonesia' with institutional language. Display name is ministry name, not a person. This is clearly a government institution account, not an individual.",
  "bio_relevance_signals": ["bio mentions government policy"],
  "account_type_indicators": [],
  "risk_flags": ["government handle pattern detected", "institutional bio language", "organization name as display name", "official ministry account"],
  "suggested_tags": ["government", "institution"]
}
```

### Example 3: Not Eligible - Promotional Account
```json
{
  "decision": "not_eligible",
  "score": 10,
  "reason_short": "Promotional account with spam signals in bio.",
  "reason_detailed": "Bio contains multiple promotional keywords: 'slot gacor', 'link alternatif', 'bonus 100%'. Handle suggests gambling affiliation. No individual person indicators. Despite occasional political keyword mentions elsewhere, this is primarily a promotional/gambling account.",
  "bio_relevance_signals": [],
  "account_type_indicators": [],
  "risk_flags": ["spam keywords in bio: slot", "spam keywords in bio: link alternatif", "promotional language dominant", "gambling references"],
  "suggested_tags": ["promotional", "spam"]
}
```

### Example 4: Uncertain - Minimal Bio
```json
{
  "decision": "uncertain",
  "score": 45,
  "reason_short": "Minimal bio provides insufficient information for confident judgment.",
  "reason_detailed": "Bio contains only emoji and link to external site. No clear topical indicators. Display name appears to be a personal name suggesting individual account, but lack of bio content makes relevance assessment impossible. Handle is generic.",
 "bio_relevance_signals": [],
  "account_type_indicators": ["personal name in display name"],
  "risk_flags": ["minimal bio content", "no topical indicators in bio"],
  "suggested_tags": ["needs-review"]
}
```

## Your Evaluation

Now evaluate this account based SOLELY on its bio and profile metadata, and return ONLY the JSON object:
