# Agent Instructions for X Account Seed Discovery

This folder contains instructions for AI agents (Opencode, Claude Code, etc.) on how to execute the X Account Seed Discovery skill using Playwright with stealth mode.

## What's Here

| File | Purpose |
|------|---------|
| `PLAYWRIGHT_GUIDE.md` | Complete guide for using Playwright to search news and X.com |
| `QUICK_REFERENCE.md` | One-liners, common selectors, and quick tips |
| `EXAMPLE_WORKFLOW.md` | Step-by-step example showing exact agent execution |

## Quick Start for Agents

When a user asks to "run this skill with Playwright", follow these steps:

### 1. Check Prerequisites
```python
# Verify Playwright is available
try:
    from playwright.sync_api import sync_playwright
    from playwright_stealth import stealth_sync
    print("✓ Playwright ready")
except ImportError:
    print("Install: pip install playwright playwright-stealth")
    print("Then: playwright install chromium")
```

### 2. Load Skill Documentation
- Read `../SKILL.md` for workflow overview
- Read `../schemas/input.json` for parameters
- Read `../schemas/output.json` for expected output

### 3. Execute Workflow
Follow the steps in `EXAMPLE_WORKFLOW.md`:
1. Search news using Playwright
2. Extract keywords
3. Search X posts with stealth mode
4. Aggregate accounts
5. Get profile details
6. Apply filters
7. AI evaluation
8. Save to database
9. Return output

### 4. Key Principles

**Always use stealth mode:**
```python
from playwright_stealth import stealth_sync
stealth_sync(page)
```

**Add random delays:**
```python
import time, random
time.sleep(random.uniform(1, 3))
```

**Handle errors gracefully:**
```python
try:
    # Attempt operation
    result = search_x_posts(queries)
except Exception as e:
    print(f"Error: {e}")
    # Continue with partial results
```

**Respect rate limits:**
- Add delays between requests
- Don't hammer the site
- If rate limited, wait and retry

## Common Tasks

### Search News
See `PLAYWRIGHT_GUIDE.md` Section "Step 1: News Search with Playwright"

### Search X Posts
See `PLAYWRIGHT_GUIDE.md` Section "Step 3: Search X.com with Playwright"

### Get X Profile
See `PLAYWRIGHT_GUIDE.md` Section "Get X Profile Information"

### Extract Keywords
See `PLAYWRIGHT_GUIDE.md` Section "Step 2: Extract Keywords from News"

## Anti-Detection Checklist

Before running X searches:

- [ ] `playwright-stealth` imported and applied
- [ ] Realistic viewport (1920x1080)
- [ ] Common user agent string
- [ ] Random delays between actions (1-5 seconds)
- [ ] Human-like scrolling (not too fast)
- [ ] Error handling for timeouts
- [ ] Fallback strategies if blocked

## Troubleshooting

### "Rate limit exceeded"
- Wait 60 seconds
- Increase delays
- Reduce number of queries

### "Timeout waiting for selector"
- Page structure may have changed
- Try alternative selectors
- Check if login required

### "Playwright not found"
```bash
pip install playwright playwright-stealth
playwright install chromium
```

### X requires login
- Ask user for X credentials
- Or use alternative: reduce search scope
- Or skip X search and use news-only approach

## Example Agent Prompt

When user says: "Run X Account Seed Discovery for politics in Indonesia"

Agent should:
1. Read `../SKILL.md` to understand workflow
2. Read input parameters from user or use defaults
3. Follow `EXAMPLE_WORKFLOW.md` step-by-step
4. Use `PLAYWRIGHT_GUIDE.md` for code snippets
5. Reference `QUICK_REFERENCE.md` for selectors
6. Return output matching `../schemas/output.json`

## Integration with Skill

These instructions work with the existing skill structure:
- Uses same input/output schemas
- Follows same workflow (news → keywords → X → filter → evaluate)
- Saves to same SQLite database schema
- Supports all skill features (auto-loop, anti-wave, etc.)

The only difference: Instead of calling APIs, the agent uses Playwright to browse and extract data from websites directly.
