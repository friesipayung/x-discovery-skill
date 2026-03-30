# Agent Instructions for x-discovery-skill

This repository contains agentic skills for discovering X.com seed accounts. It's a documentation-first project with JSON schemas, SQL schemas, and markdown prompts.

## Repository Structure

```
x-discovery-skill/
├── skills/
│   └── {skill_name}/              # Each skill is self-contained
│       ├── SKILL.md               # Usage guide and reference
│       ├── prompts/               # AI evaluation prompts
│       ├── schemas/               # JSON schemas for validation
│       ├── sql/                   # Database schemas
│       └── docs/                  # PRD, technical design
├── README.md                      # Main documentation
└── AGENTS.md                      # This file
```

## Build/Test Commands

This repository has no traditional build system. Validation is manual:

```bash
# Validate JSON schemas
python3 -c "import json; json.load(open('skills/x_account_seed_discovery/schemas/input.json'))"
python3 -c "import json; json.load(open('skills/x_account_seed_discovery/schemas/output.json'))"

# Validate SQL syntax (requires sqlite3)
sqlite3 :memory: < skills/x_account_seed_discovery/sql/schema.sql

# Check markdown links (if mdlink-check available)
# No automated link checker - verify manually
```

## Code Style Guidelines

### File Organization
- **One skill per directory** under `skills/{skill_name}/`
- **SKILL.md** is required - the entry point for agentic tools
- **schemas/** contain JSON Schema draft-07 files
- **prompts/** contain markdown templates with `{{variables}}`
- **sql/** contain SQLite-compatible schemas

### JSON Schema Conventions
- Use JSON Schema draft-07 (`$schema` header required)
- Include `title`, `description`, and `examples` for all properties
- Use `additionalProperties: false` to prevent typos
- Required fields explicitly listed in `required` array
- Use descriptive property names (e.g., `total_eligible` not `eligible`)

### SQL Conventions
- SQLite-compatible syntax only
- Use `IF NOT EXISTS` for all CREATE statements
- Enable foreign keys: `PRAGMA foreign_keys = ON;`
- Enable WAL mode: `PRAGMA journal_mode = WAL;`
- Snake_case for table/column names
- JSON columns named with `_json` suffix (e.g., `constraints_json`)
- Indexes named: `idx_{table}_{column}`
- Views named: `v_{description}`

### Markdown Conventions
- Use ATX headers (`#` not `===`)
- Code blocks specify language: ` ```json `, ` ```sql `, ` ```bash `
- Tables use standard markdown format with alignment
- Variables in prompts use `{{handle}}` syntax (double braces)
- Keep lines under 100 characters where possible

### Naming Conventions
- **Directories**: snake_case (e.g., `x_account_seed_discovery`)
- **Files**: snake_case (e.g., `seed_judge.md`)
- **Tables**: snake_case, plural (e.g., `account_evaluations`)
- **Columns**: snake_case (e.g., `followers_count`)
- **JSON keys**: snake_case (e.g., `total_eligible`)
- **Variables**: snake_case in braces (e.g., `{{followers_count}}`)

### Documentation Standards
- **SKILL.md**: Must include When to Use, Core Workflow, Quick Reference, Implementation
- **PRD.md**: Product requirements with user stories and acceptance criteria
- **TECHNICAL_DESIGN.md**: Architecture, interfaces, error handling, performance
- All docs must have version number in header or footer

### Error Handling Patterns
- Fatal errors: Database connection, schema init, invalid input
- Recoverable errors: Single item failures (log and continue)
- Partial success: Always produce summary with completed stats
- Error objects have: `stage`, `message`, optional `account_handle`, `details`

### Idempotency Requirements
- Handle normalization prevents duplicates (lowercase, strip @, URL extraction)
- Upsert pattern: `ON CONFLICT(handle_normalized) DO UPDATE`
- Reruns create new evaluation rows but don't duplicate account masters

## Environment Variables

Skills use these conventions:
- `SQLITE_PATH`: Database file location
- `DEFAULT_REGION`: Geographic default (e.g., "Indonesia")
- Provider credentials passed via runtime-specific mechanisms

## Testing Approach

No automated test suite. Manual validation:
1. Schema validation (JSON well-formed, SQL executes)
2. Prompt rendering (variables replaced correctly)
3. End-to-end with mock providers
4. Idempotency check (rerun produces no duplicates)

## Versioning

- Skills use semantic versioning in SKILL.md footer
- Schema changes require version bump
- Document breaking changes in PRD.md changelog

## Git Conventions

- `.gitignore`: `.env`, `venv/`, `.venv/`, `.DS_Store`, `*.db`
- Commit messages: Present tense, descriptive (e.g., "Add anti-wave filter documentation")
- No compiled artifacts to commit (this is source-only repo)
