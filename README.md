# X Discovery Skill

An agentic skill for discovering quality X.com (Twitter) seed accounts using a news-first approach. This skill finds accounts that genuinely discuss specific topics by grounding search in actual news articles, filtering opportunistic accounts, and using AI judgment with SQLite persistence.

**Quick Reference:**
- 🧑‍💻 **Using this skill?** → See [SKILL.md](skills/x_account_seed_discovery/SKILL.md) for complete usage guide
- 🔧 **Developing/contributing?** → See [AGENTS.md](AGENTS.md) for development guidelines

## 🎯 What This Does

Instead of searching X profiles by bio keywords (which often returns irrelevant accounts), this skill:

1. **Searches news articles** for your topic to find current, relevant issues
2. **Extracts keywords and entities** from those news articles
3. **Searches X posts** using those extracted keywords
4. **Extracts account authors** from matched posts (proven relevance)
5. **Filters opportunistic accounts** (spam, promo, porn, gambling, trend hijackers)
6. **AI evaluates** remaining accounts for quality and relevance
7. **Persists results** to SQLite with idempotent deduplication

**Result:** Higher quality seed accounts that actually post about your topic, not just have keywords in their bio.

## 📁 Repository Structure

```
x-discovery-skill/
├── skills/
│   └── x_account_seed_discovery/     # Main skill
│       ├── SKILL.md                  # Usage guide and reference
│       ├── prompts/
│       │   └── seed_judge.md          # AI evaluation prompt
│       ├── schemas/
│       │   ├── input.json             # Input validation
│       │   └── output.json            # Output validation
│       ├── sql/
│       │   └── schema.sql             # SQLite database schema
│       └── docs/
│           ├── PRD.md                 # Product requirements
│           └── TECHNICAL_DESIGN.md    # Architecture details
├── PRD_News_First_X_Seed_Discovery_Skill.md  # Original PRD
└── README.md                          # This file
```

## 📦 Installation

### Claude Code

1. **Clone the repository into your Claude Code skills directory:**
   ```bash
   # Navigate to your Claude Code skills directory (usually ~/.claude/skills/)
   cd ~/.claude/skills/
   
   # Clone the repository
   git clone https://github.com/friesipayung/x-discovery-skill.git
   
   # Or clone to a custom location and symlink
   git clone https://github.com/friesipayung/x-discovery-skill.git ~/tools/x-discovery-skill
   ln -s ~/tools/x-discovery-skill/skills/x_account_seed_discovery ~/.claude/skills/x_account_seed_discovery
   ```

2. **Verify installation:**
   ```
   @x_account_seed_discovery help
   ```

3. **Use the skill:**
   ```
   @x_account_seed_discovery with topic="politics" region="Indonesia"
   ```

### Opencode

1. **Clone the repository:**
   ```bash
   git clone https://github.com/friesipayung/x-discovery-skill.git ~/skills/x-discovery-skill
   ```

2. **Register the skill in your `opencode.yaml`:**
   ```yaml
   skills:
     - path: ~/skills/x-discovery-skill/skills/x_account_seed_discovery
       name: x_account_seed_discovery
   ```

3. **Run the skill:**
   ```bash
   opencode run skill x_account_seed_discovery --input '{
     "topic": "politics",
     "region": "Indonesia"
   }'
   ```

### Other Agentic Tools / Custom Implementation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/friesipayung/x-discovery-skill.git
   cd x-discovery-skill
   ```

2. **Copy the skill to your agent's skills directory:**
   ```bash
   # Example: Copy to your agent's skills folder
   cp -r skills/x_account_seed_discovery /path/to/your/agent/skills/
   ```

3. **Initialize the database:**
    ```bash
    # Create the config directory and initialize database
    mkdir -p ~/.x-discovery
    sqlite3 ~/.x-discovery/seed.sql < skills/x_account_seed_discovery/sql/schema.sql
    ```

4. **Set environment variables:**
    ```bash
    export SQLITE_PATH="$HOME/.x-discovery/seed.sql"
    export DEFAULT_REGION="Indonesia"
    ```

5. **Implement the orchestrator** (see [TECHNICAL_DESIGN.md](skills/x_account_seed_discovery/docs/TECHNICAL_DESIGN.md) for provider interfaces and implementation details)

## 🔄 Updating

To get the latest updates and improvements:

### Claude Code

If you cloned directly to the skills directory:
```bash
cd ~/.claude/skills/x-discovery-skill
git pull origin main
```

If you used a symlink:
```bash
cd ~/tools/x-discovery-skill  # or wherever you cloned it
git pull origin main
# The symlink at ~/.claude/skills/x_account_seed_discovery will automatically reflect changes
```

**Note:** Claude Code automatically detects skill changes - no restart needed. Just start using the updated skill with `@x_account_seed_discovery`.

### Opencode

```bash
cd ~/skills/x-discovery-skill  # or your custom path
git pull origin main
```

**Note:** Opencode loads skills at startup. To use the updated skill:
- **Option 1:** Restart Opencode
- **Option 2:** Run `opencode reload` if your version supports hot-reload

### Database Schema Updates

If the update includes database schema changes:

```bash
# Backup your existing database first
cp ~/.x-discovery/seed.sql ~/.x-discovery/seed.sql.backup.$(date +%Y%m%d)

# Apply schema updates (safe to run - uses IF NOT EXISTS)
sqlite3 ~/.x-discovery/seed.sql < skills/x_account_seed_discovery/sql/schema.sql
```

### Manual / Custom Implementation

```bash
cd /path/to/your/x-discovery-skill
git pull origin main

# Re-copy to your agent's skills directory if needed
cp -r skills/x_account_seed_discovery /path/to/your/agent/skills/
```

### Checking Your Version

To verify you're running the latest version:

```bash
cd /path/to/x-discovery-skill
git log --oneline -5
```

### Other Agentic Tools / Custom Implementation

You can also use the skill schemas and prompts directly:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/friesipayung/x-discovery-skill.git
   cd x-discovery-skill
   ```

2. **Use the schemas for validation:**
   - Input validation: [schemas/input.json](skills/x_account_seed_discovery/schemas/input.json)
   - Output validation: [schemas/output.json](skills/x_account_seed_discovery/schemas/output.json)

3. **Use the AI judge prompt:**
   - Prompt template: [prompts/seed_judge.md](skills/x_account_seed_discovery/prompts/seed_judge.md)
   - Customize by replacing `{{variables}}` with your data

4. **Set up the database:**
    ```bash
    mkdir -p ~/.x-discovery
    sqlite3 ~/.x-discovery/seed.sql < skills/x_account_seed_discovery/sql/schema.sql
    ```

## 🚀 Quick Start

**Skill users:** See [SKILL.md](skills/x_account_seed_discovery/SKILL.md#implementation-details) for detailed setup instructions.

**Quick summary:**
1. Initialize database: `sqlite3 ~/.x-discovery/seed.sql < skills/x_account_seed_discovery/sql/schema.sql`
2. Set environment: `export SQLITE_PATH="$HOME/.x-discovery/seed.sql"`
3. Run: `@x_account_seed_discovery with topic="politics" region="Indonesia"`

## 📊 Example Output

```json
{
  "run_id": "20260330T100000Z-abc123",
  "topic": "government",
  "region": "Indonesia",
  "total_news_articles": 16,
  "total_keywords": 28,
  "total_x_posts": 240,
  "total_accounts_aggregated": 97,
  "total_accounts_limited": 23,
  "total_prefiltered": 71,
  "total_anti_wave_rejected": 14,
  "total_ai_evaluated": 57,
  "total_eligible": 21,
  "total_not_eligible": 28,
  "total_uncertain": 8,
  "min_accounts_met": true,
  "min_accounts_required": 1,
  "eligible_accounts": [
    {
      "handle": "example",
      "display_name": "Example",
      "followers_count": 25000,
      "decision": "eligible",
      "score": 89,
      "reason_short": "Akun rutin membahas isu pemerintahan Indonesia."
    }
  ],
  "errors": []
}
```

## 🛡️ Anti Riding-the-Waves Filter

One of the key features is aggressive filtering of opportunistic accounts that hijack trending topics:

**Blocked Keywords:** `slot`, `judi`, `casino`, `promo`, `onlyfans`, `bokep`, `open bo`, `pinjol`, `affiliate`, and more.

**Detection Patterns:**
- Bio spam indicators
- Promotional display names
- Hashtag stuffing
- Engagement bait patterns
- Mixed serious/promotional content

Accounts passing the filter still get evaluated by AI with risk flags as context.

## 🗄️ Database Schema

The skill uses SQLite with 7 tables:

- **runs** - Run metadata and statistics
- **news_articles** - Fetched news articles per run
- **run_keywords** - Extracted keywords per run
- **accounts** - Master account records (unique by normalized handle)
- **account_topic_signals** - Aggregated signals per account per run
- **account_evaluations** - AI evaluation results per account per run
- **account_tags** - Tags for categorizing accounts

**Key Features:**
- Idempotent upserts (reruns don't create duplicates)
- Handle normalization (lowercase, strip @, URL extraction)
- Audit trail with run history
- Export views for eligible accounts

## 📖 Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| [SKILL.md](skills/x_account_seed_discovery/SKILL.md) | Complete usage guide for skill agents | **Skill users** (Claude Code, Opencode, etc.) |
| [AGENTS.md](AGENTS.md) | Development guidelines for contributors | **Developers** contributing to this repo |
| [TECHNICAL_DESIGN.md](skills/x_account_seed_discovery/docs/TECHNICAL_DESIGN.md) | Architecture and implementation details | Developers |
| [PRD.md](skills/x_account_seed_discovery/docs/PRD.md) | Full product requirements | Product/Stakeholders |
| [sql/schema.sql](skills/x_account_seed_discovery/sql/schema.sql) | Database schema | Developers |
| [prompts/seed_judge.md](skills/x_account_seed_discovery/prompts/seed_judge.md) | AI evaluation prompt | Developers |

## 🔧 Configuration Options

### Required
- `topic` - Topic to search for

### Common Optional Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| `region` | `Indonesia` | Geographic scope |
| `min_followers` | - | Minimum follower count |
| `max_news_articles` | 20 | News articles to fetch |
| `max_x_posts` | 300 | X posts to search |
| `max_accounts_to_aggregate` | 100 | Accounts to collect from X posts |
| `max_accounts_to_evaluate` | 100 | Accounts for AI evaluation |
| `min_accounts_to_evaluate` | 1 | Minimum accounts required (run fails if fewer) |
| `anti_wave_mode` | true | Filter opportunistic accounts |
| `save_mode` | `all` | `all` or `eligible_only` |
| `dry_run` | false | Preview without DB writes |

See [input.json](skills/x_account_seed_discovery/schemas/input.json) for all 20+ parameters.

## 📤 Exporting Results

```sql
-- Export eligible accounts
SELECT * FROM v_eligible_accounts 
WHERE topic = 'politics' 
  AND region = 'Indonesia'
ORDER BY score DESC;

-- Get run statistics
SELECT * FROM v_run_summary 
WHERE topic = 'politics' 
ORDER BY started_at DESC;

-- Review uncertain accounts
SELECT a.handle, ae.reason_short, ae.score
FROM accounts a
JOIN account_evaluations ae ON a.id = ae.account_id
WHERE ae.decision = 'uncertain'
ORDER BY ae.score DESC;
```

## 🎯 Use Cases

- **Policy Monitoring** - Find accounts discussing government policy, legislation, regulation
- **Issue Tracking** - Discover accounts talking about specific issues (mining, environment, economy)
- **Influencer Research** - Identify genuine topical influencers vs. opportunistic accounts
- **Media Intelligence** - Build seed lists for social listening and monitoring
- **Academic Research** - Create representative samples for analysis

## ⚠️ Limitations

- Requires external news and X search providers (not included)
- Quality depends on provider data quality
- AI judgment may drift with different runtimes/prompts
- SQLite may become bottleneck at very large volumes
- Some opportunistic accounts may slip through with limited samples

## 🤝 Contributing

This skill follows the [writing-skills TDD approach](https://github.com/anthropics/superpowers/blob/main/skills/writing-skills/SKILL.md):

1. Test before deploying
2. Document rationalizations and close loopholes
3. Keep skills focused and searchable
4. Use examples from real scenarios

## 📜 License

See [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built following the Anthropic Superpowers skill framework and TDD methodology for agentic documentation.
