# Scripts for X Account Seed Discovery

This directory contains Python scripts for searching news and X/Twitter profiles.

## Architecture

**News Search (HTTP-based):**
- `search_news.py` - Uses DuckDuckGo (free) or SerpAPI (Google News, requires API key)
- No browser automation needed

**X/Twitter Access (Browser-based):**
- `search_nitter.py` - Uses Nitter instances via Playwright with Chrome profile
- Automatic instance load balancing
- Rate limit awareness

## Scripts

### 1. search_news.py
Search news articles using DuckDuckGo (free) or SerpAPI (Google News).

**Usage:**
```bash
# DuckDuckGo (free, no API key)
python search_news.py --topic "politics" --region "Indonesia" --max-results 20

# SerpAPI Google News (requires API key)
export SERPAPI_KEY="your_key_here"
python search_news.py --topic "politics" --region "Indonesia" --provider serpapi --max-results 20

# Save to file
python search_news.py --topic "mining policy" --region "Indonesia" --output news.json
```

**Features:**
- DuckDuckGo: Free, no API keys needed
- SerpAPI: Google News access (requires API key from https://serpapi.com)
- Parses article titles, URLs, sources, and snippets
- Respects rate limits with configurable delays
- Outputs JSON for further processing

### 2. search_nitter.py
Search X/Twitter via Nitter instances using Playwright with Chrome profile and automatic load balancing.

**Usage:**
```bash
# Search for posts (automatic instance rotation)
python search_nitter.py search --query "politics Indonesia" --max-results 50

# Get profile info
python search_nitter.py profile prabowo --output profile.json

# With custom Chrome profile
python search_nitter.py --profile-dir ~/.x-discovery/chrome-profile search --query "indonesia" --max-results 50

# Run headless (not recommended - may trigger detection)
python search_nitter.py --headless search --query "test" --max-results 10
```

**Features:**
- **Automatic load balancing** across multiple Nitter instances
- **Rate limit awareness** - tracks instance health and rotates on failures
- **Chrome profile** - persists cookies and session data at `~/.x-discovery/chrome-profile`
- **Stealth mode** - enabled by default to avoid detection
- **Instance health tracking** - marks unhealthy instances, retries with healthy ones

**Default Nitter instances:**
- nitter.net (official)
- xcancel.com
- nitter.privacyredirect.com
- nitter.poast.org
- nitter.tiekoetter.com
- nitter.catsarch.com

See https://github.com/zedeus/nitter/wiki/Instances for the full list.

**Environment variables:**
- `NITTER_INSTANCES` - Comma-separated list of custom instances (optional)

## Installation

### 1. Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt

# Install Playwright browsers (for search_nitter.py only)
playwright install chromium
```

### 2. Setup Chrome Profile

`search_nitter.py` uses a dedicated Chrome profile to persist cookies and session data:

**Default profile location:** `~/.x-discovery/chrome-profile`

**Create the profile:**
```bash
mkdir -p ~/.x-discovery/chrome-profile
```

The profile will be populated automatically on first run.

**Why use a dedicated profile:**
- Persists cookies and login sessions
- Isolates automation from your main Chrome
- Reduces detection by maintaining consistent browser fingerprint
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
# Search posts (automatic instance rotation)
python search_nitter.py search --query "politics Indonesia" --max-results 50 --output posts.json

# Extract unique handles
cat posts.json | jq -r '.posts[].author_handle' | sort -u
```

### Get Profile Information

```bash
# Get single profile
python search_nitter.py profile prabowo --output prabowo.json

# Get multiple profiles (with delay to avoid rate limits)
for handle in prabowo jokowi ganjar; do
    python search_nitter.py profile $handle --output ${handle}.json
    sleep 5
done
```

### Check Instance Health

The script automatically tracks instance health:

```bash
# Run a search and check the output
python search_nitter.py search --query "test" --max-results 5 --output result.json

# View instance statistics
cat result.json | jq '.instance_stats'
```

## Integration with Skill Workflow

These scripts can be used as standalone tools or integrated into the X Account Seed Discovery workflow:

```python
# Example: Using in a custom orchestrator
import subprocess
import json

# Step 1: Search news
result = subprocess.run([
    "python", "scripts/search_news.py",
    "--topic", "politics",
    "--region", "Indonesia",
    "--max-results", "20"
], capture_output=True, text=True)

news_data = json.loads(result.stdout)
articles = news_data["articles"]

# Step 2: Extract keywords (using your own NLP)
keywords = extract_keywords(articles)

# Step 3: Search X via Nitter
result = subprocess.run([
    "python", "scripts/search_nitter.py",
    "search",
    "--query", "politics Indonesia",
    "--max-results", "100"
], capture_output=True, text=True)

posts_data = json.loads(result.stdout)
posts = posts_data["posts"]

# Step 4: Aggregate accounts and continue workflow...
```

## Notes

- **search_news.py**: Does NOT require Playwright, uses HTTP requests only
- **search_nitter.py**: REQUIRES Playwright and runs in headful mode (visible browser) by default
- Both scripts include rate limiting to be respectful to the services
- Nitter instances are community-run - availability may vary
- The load balancer automatically handles instance failures
- Always check terms of service before scraping
- See https://github.com/zedeus/nitter/wiki/Instances for instance status

## Troubleshooting

### Connection Refused / Cannot Connect to Nitter

If you get connection errors:

```
Trying instance: https://nitter.net
✗ Instance https://nitter.net failed: Connection refused
Trying instance: https://xcancel.com
✓ Instance https://xcancel.com returned 25 posts in 8.2s
```

The script automatically rotates to healthy instances. If all fail:

**Solutions:**
1. **Check instance status**: https://github.com/zedeus/nitter/wiki/Instances
2. **Set custom instances**:
   ```bash
   export NITTER_INSTANCES="https://nitter.net,https://xcancel.com"
   ```
3. **Use a VPN** - Change your geographic location
4. **Wait and retry** - Instances may be temporarily overloaded

### Playwright Not Found

```bash
pip install playwright playwright-stealth
playwright install chromium
```

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

### SerpAPI Key Not Found

```bash
export SERPAPI_KEY="your_api_key_here"
# Or pass to the script
SERPAPI_KEY="your_key" python search_news.py --provider serpapi ...
```
