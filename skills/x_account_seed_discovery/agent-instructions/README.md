# Agent Instructions for X Account Seed Discovery

This folder contains instructions for AI agents (Opencode, Claude Code, etc.) on how to execute the X Account Seed Discovery skill.

## Architecture Overview

**News Search (HTTP-based):**
- Uses DuckDuckGo HTML interface (free, no API key, no browser needed)
- Optional: SerpAPI for Google News (requires API key)
- Simple HTTP requests with `requests` library

**X/Twitter Access (Browser-based):**
- Uses Nitter instances via Playwright with Chrome profile
- Chrome profile stored at `~/.x-discovery/chrome-profile`
- Automatic instance rotation with rate limit awareness
- Stealth mode to avoid detection

## Quick Start for Agents

When a user asks to "run this skill", follow these steps:

### 1. Check Prerequisites

```python
# Verify required packages
import sys

def check_prerequisites():
    missing = []
    
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        missing.append("requests beautifulsoup4")
    
    try:
        from playwright.sync_api import sync_playwright
        from playwright_stealth import Stealth
    except ImportError:
        missing.append("playwright playwright-stealth")
    
    if missing:
        print(f"Install: pip install {' '.join(missing)}")
        if "playwright" in ' '.join(missing):
            print("Then: playwright install chromium")
        return False
    
    return True

check_prerequisites()
```

### 2. Setup Chrome Profile

```bash
# Create profile directory
mkdir -p ~/.x-discovery/chrome-profile
```

The profile will be populated automatically on first run.

### 3. Load Skill Documentation

- Read `../SKILL.md` for workflow overview
- Read `../schemas/input.json` for parameters
- Read `../schemas/output.json` for expected output

### 4. Execute Workflow

**Step 1: Search News (HTTP-based)**

Use the `search_news.py` script:

```python
# Using DuckDuckGo (free)
import subprocess

result = subprocess.run([
    "python", "skills/x_account_seed_discovery/scripts/search_news.py",
    "--topic", "politics",
    "--region", "Indonesia",
    "--max-results", "20"
], capture_output=True, text=True)

news_data = json.loads(result.stdout)
articles = news_data["articles"]
```

Or use SerpAPI for Google News:
```python
# Requires SERPAPI_KEY environment variable
result = subprocess.run([
    "python", "skills/x_account_seed_discovery/scripts/search_news.py",
    "--topic", "politics",
    "--region", "Indonesia",
    "--provider", "serpapi",
    "--max-results", "20"
], capture_output=True, text=True)
```

**Step 2: Extract Keywords**

Use AI to extract keywords from article titles and snippets.

**Step 3: Search X via Nitter (Playwright-based)**

Use the `search_nitter.py` script:

```python
result = subprocess.run([
    "python", "skills/x_account_seed_discovery/scripts/search_nitter.py",
    "search",
    "--query", "politics Indonesia",
    "--max-results", "50"
], capture_output=True, text=True)

posts_data = json.loads(result.stdout)
posts = posts_data["posts"]
```

**Step 4: Aggregate Accounts**

Extract unique handles from posts.

**Step 5: Get Profile Details**

```python
for handle in unique_handles[:10]:  # Limit to avoid rate limits
    result = subprocess.run([
        "python", "skills/x_account_seed_discovery/scripts/search_nitter.py",
        "profile", handle
    ], capture_output=True, text=True)
    # Parse profile data...
```

**Step 6: Apply Filters & AI Evaluation**

Follow the workflow in `../SKILL.md`.

**Step 7: Save to Database**

Use SQLite operations as documented.

## Key Principles

### News Search (HTTP)
- Simple, fast, no browser overhead
- DuckDuckGo: Free, no API key
- SerpAPI: Google News, requires API key

### X Search (Playwright + Nitter)
- Always use Chrome profile at `~/.x-discovery/chrome-profile`
- Automatic instance rotation
- Rate limit awareness
- Stealth mode enabled by default

### Error Handling
- Graceful degradation between Nitter instances
- Continue with partial results
- Log errors for debugging

## Common Tasks

### Search News
```bash
python scripts/search_news.py --topic "politics" --region "Indonesia" --max-results 20
```

### Search X Posts
```bash
python scripts/search_nitter.py search --query "politics Indonesia" --max-results 50
```

### Get X Profile
```bash
python scripts/search_nitter.py profile prabowo
```

## Rate Limiting & Best Practices

### Nitter Access
- Instances rotate automatically
- Delays built into the script (2-5 seconds)
- Chrome profile reduces detection
- Stealth mode enabled by default

### News Access
- DuckDuckGo: Be polite, don't hammer (1 second delay built-in)
- SerpAPI: Respect rate limits of your plan

## Troubleshooting

### "Chrome profile not found"
```bash
mkdir -p ~/.x-discovery/chrome-profile
```

### "No healthy Nitter instances"
- Check network connectivity
- Try again later (instances may be temporarily down)
- Check https://github.com/zedeus/nitter/wiki/Instances for status

### "Rate limit exceeded"
- The script handles this automatically by rotating instances
- If all instances fail, wait a few minutes and retry

### "Playwright not found"
```bash
pip install playwright playwright-stealth
playwright install chromium
```

## Integration with Skill

These instructions work with the existing skill structure:
- Uses same input/output schemas
- Follows same workflow (news → keywords → X → filter → evaluate)
- Saves to same SQLite database schema
- Supports all skill features (auto-loop, anti-wave, etc.)

The only difference: News uses HTTP requests instead of browser automation.

## Files Reference

| File | Purpose |
|------|---------|
| `../SKILL.md` | Main skill documentation |
| `../scripts/search_news.py` | News search (HTTP-based) |
| `../scripts/search_nitter.py` | X search (Playwright-based) |
| `../schemas/input.json` | Input validation |
| `../schemas/output.json` | Output validation |
