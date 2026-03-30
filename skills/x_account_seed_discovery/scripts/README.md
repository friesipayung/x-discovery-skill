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

### 2. search_nitter.py (Recommended)
Search X/Twitter via Nitter instances using Playwright with Chrome profile (headful mode).

**Usage:**
```bash
# Search for posts (uses default nitter.net instance)
python search_nitter.py search --query "politics Indonesia" --max-results 50

# Get profile info
python search_nitter.py profile prabowo --output profile.json

# Use different Nitter instance
python search_nitter.py --instance xcancel.com search --query "mining policy" --max-results 100

# With custom Chrome profile
python search_nitter.py --profile ~/.x-discovery/chrome-profile search --query "indonesia" --max-results 50
```

**Available Nitter instances:**
- nitter.net (official)
- xcancel.com
- nitter.privacyredirect.com
- nitter.poast.org
- nitter.tiekoetter.com
- nitter.catsarch.com

See https://github.com/zedeus/nitter/wiki/Instances for the full list.

**Features:**
- Uses Nitter instances as X/Twitter proxy (no X API needed)
- Playwright with stealth mode for anti-detection
- **Dedicated Chrome profile** - persists cookies and session data
- Multiple instance fallback support
- Automatic page load waiting with Cloudflare detection
- Parses posts, engagement metrics, and profile info

### 3. search_sotwe.py (Legacy)
Search X/Twitter via sotwe.com proxy (deprecated, use search_nitter.py instead).

## Installation

### 1. Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt

# Install Playwright browsers (for search_nitter.py only)
playwright install chromium
```

### 2. Chrome Profile (Recommended)

`search_nitter.py` uses a dedicated Chrome profile to persist cookies and session data:

**Default profile location:** `~/.x-discovery/chrome-profile`

**Create and manage the profile:**
```bash
# Create the X-Discovery Chrome profile
python chrome_profile.py create

# Test the profile (opens Chrome manually)
python chrome_profile.py test

# View profile info
python chrome_profile.py info
```

**Why use a dedicated profile:**
- Persists cookies and login sessions
- Isolates automation from your main Chrome
- Allows pre-logging into sites manually
- Maintains state between script runs

**Manual Chrome launch with profile:**
```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
    --user-data-dir="$HOME/.x-discovery/chrome-profile"

# Linux
google-chrome --user-data-dir="$HOME/.x-discovery/chrome-profile"
```

## Examples

### Search News and Extract Keywords

```bash
# Search news
python search_news.py --topic "government policy" --region "Indonesia" --output news.json

# Extract keywords (using jq)
cat news.json | jq -r '.articles[].title' | tr ' ' '\n' | sort | uniq -c | sort -rn | head -20
```

### Search X Posts via Nitter

```bash
# Search posts (default instance: nitter.net)
python search_nitter.py search --query "politics Indonesia" --max-results 50 --output posts.json

# Extract unique handles
cat posts.json | jq -r '.posts[].author_handle' | sort -u
```

### Get Profile Information

```bash
# Get single profile
python search_nitter.py profile prabowo --output prabowo.json

# Get multiple profiles
for handle in prabowo jokowi ganjar; do
    python search_nitter.py profile $handle --output ${handle}.json
    sleep 5
done
```

### Try Multiple Nitter Instances

```bash
# If one instance fails, try others
instances=("nitter.net" "xcancel.com" "nitter.privacyredirect.com")

for instance in "${instances[@]}"; do
    echo "Trying $instance..."
    python search_nitter.py --instance $instance search --query "test" --max-results 5 && break
done
```

## Integration with Skill Workflow

These scripts can be used as standalone tools or integrated into the X Account Seed Discovery workflow:

```python
# Example: Using in a custom orchestrator
from scripts.search_news import search_news
from scripts.search_nitter import NitterSearcher

# Step 1: Search news
articles = search_news(topic="politics", region="Indonesia", max_results=20)

# Step 2: Extract keywords (using your own NLP)
keywords = extract_keywords(articles)

# Step 3: Search X via Nitter
with NitterSearcher(base_url="https://nitter.net", headless=False) as searcher:
    posts = searcher.search_posts("politics Indonesia", max_results=100)
    
# Step 4: Aggregate accounts and continue workflow...
```

## Notes

- **search_news.py**: Does NOT require Playwright, uses HTTP requests only
- **search_nitter.py**: REQUIRES Playwright and runs in headful mode (visible browser)
- Both scripts include rate limiting to be respectful to the services
- Nitter instances are community-run - availability may vary
- Always check terms of service before scraping
- See https://github.com/zedeus/nitter/wiki/Instances for instance status

## Troubleshooting

### Connection Refused / Cannot Connect to Nitter

If you get connection errors when using `search_nitter.py`:

```
ERROR: Cannot connect to https://nitter.net
This may be due to:
  - Instance being temporarily down
  - Network restrictions
  - Geographic blocking
```

**Solutions:**
1. **Try a different instance**:
   ```bash
   python search_nitter.py --instance xcancel.com search --query "test"
   python search_nitter.py --instance nitter.privacyredirect.com search --query "test"
   ```
2. **Check instance status**: https://status.d420.de/
3. **Use a VPN** - Change your geographic location
4. **Try alternatives**:
   - X.com directly with Playwright (requires login)
   - Use the official X API v2

### Playwright Stealth Import Error

If you get import errors with `playwright-stealth`:

```python
# Old (incorrect)
from playwright_stealth import stealth_sync

# New (correct)
from playwright_stealth import Stealth
stealth = Stealth()
stealth.apply_stealth_sync(page)
```

The script has been updated to use the correct API.

### Chrome Profile Already in Use

If you get "ProcessSingleton" errors:

```bash
# Kill existing Chrome processes
pkill -9 "Google Chrome"

# Remove lock file
rm -f ~/.x-discovery/chrome-profile/SingletonLock

# Try again
python search_nitter.py search --query "test"
```
