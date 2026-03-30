# Scripts for X Account Seed Discovery

This directory contains Python scripts for searching news and X/Twitter profiles.

## Scripts

### 1. search_news.py
Search news articles using DuckDuckGo (no Playwright required).

**Usage:**
```bash
python search_news.py --topic "politics" --region "Indonesia" --max-results 20
python search_news.py --topic "mining policy" --region "Indonesia" --output news.json
```

**Features:**
- Uses DuckDuckGo HTML interface (no API keys needed)
- Parses article titles, URLs, sources, and snippets
- Respects rate limits with configurable delays
- Outputs JSON for further processing

### 2. search_sotwe.py
Search X/Twitter via sotwe.com proxy using Playwright with AdGuard (headful mode).

**Usage:**
```bash
# Search for posts
python search_sotwe.py search --query "politics Indonesia" --max-results 50

# Get profile info
python search_sotwe.py profile prabowo --output profile.json

# With AdGuard extension
python search_sotwe.py search --query "mining policy" \
    --adguard-path /path/to/adguard-extension \
    --max-results 100
```

**Features:**
- Uses sotwe.com as X/Twitter proxy (no X API needed)
- Playwright with stealth mode for anti-detection
- AdGuard extension support for cleaner scraping (requires headful mode)
- Automatic scrolling to load more content
- Parses posts, engagement metrics, and profile info

## Installation

### 1. Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt

# Install Playwright browsers (for search_sotwe.py only)
playwright install chromium
```

### 2. Optional: Install AdGuard Extension

For cleaner scraping with `search_sotwe.py`:

1. Download AdGuard AdBlocker from Chrome Web Store:
   https://chromewebstore.google.com/detail/adguard-adblocker/bgnkhhnnamicmpeenaelnjfhikgbkllg

2. Extract the extension to a folder (or use the .crx file path)

3. Use with `--adguard-path` flag

## Examples

### Search News and Extract Keywords

```bash
# Search news
python search_news.py --topic "government policy" --region "Indonesia" --output news.json

# Extract keywords (using jq)
cat news.json | jq -r '.articles[].title' | tr ' ' '\n' | sort | uniq -c | sort -rn | head -20
```

### Search X Posts via Sotwe

```bash
# Search posts
python search_sotwe.py search --query "politics Indonesia" --max-results 50 --output posts.json

# Extract unique handles
cat posts.json | jq -r '.posts[].author_handle' | sort -u
```

### Get Profile Information

```bash
# Get single profile
python search_sotwe.py profile prabowo --output prabowo.json

# Get multiple profiles
for handle in prabowo jokowi ganjar; do
    python search_sotwe.py profile $handle --output ${handle}.json
    sleep 5
done
```

## Integration with Skill Workflow

These scripts can be used as standalone tools or integrated into the X Account Seed Discovery workflow:

```python
# Example: Using in a custom orchestrator
from scripts.search_news import search_news
from scripts.search_sotwe import SotweSearcher

# Step 1: Search news
articles = search_news(topic="politics", region="Indonesia", max_results=20)

# Step 2: Extract keywords (using your own NLP)
keywords = extract_keywords(articles)

# Step 3: Search X via sotwe
with SotweSearcher(headless=False) as searcher:
    posts = searcher.search_posts("politics Indonesia", max_results=100)
    
# Step 4: Aggregate accounts and continue workflow...
```

## Notes

- **search_news.py**: Does NOT require Playwright, uses HTTP requests only
- **search_sotwe.py**: REQUIRES Playwright and runs in headful mode for AdGuard support
- Both scripts include rate limiting to be respectful to the services
- Sotwe.com is a third-party proxy - availability and structure may change
- Always check terms of service before scraping
