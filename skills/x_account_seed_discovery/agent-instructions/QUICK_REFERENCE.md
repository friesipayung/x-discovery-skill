# Quick Reference: Playwright for X Discovery

## One-Liner Commands for Agents

### Setup
```bash
pip install playwright playwright-stealth
playwright install chromium
```

### Search News (Google)
```python
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    stealth_sync(page)
    page.goto(f"https://news.google.com/search?q={topic}+{region}&hl=en")
    articles = page.query_selector_all('article')
    # Extract data...
    browser.close()
```

### Search X Posts
```python
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import time, random

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
    context = browser.new_context(viewport={'width': 1920, 'height': 1080})
    page = context.new_page()
    stealth_sync(page)
    
    page.goto(f"https://x.com/search?q={query}&f=live")
    page.wait_for_selector('article')
    
    # Scroll and collect
    for _ in range(5):
        posts = page.query_selector_all('article')
        # Extract posts...
        page.evaluate('window.scrollBy(0, 800)')
        time.sleep(random.uniform(1, 3))
    
    browser.close()
```

### Get X Profile
```python
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    stealth_sync(page)
    page.goto(f"https://x.com/{handle}")
    page.wait_for_selector('[data-testid="UserName"]')
    # Extract profile data...
    browser.close()
```

## Common Selectors for X.com

| Element | Selector |
|---------|----------|
| Post/article | `article` |
| Post text | `[data-testid="tweetText"]` |
| Author handle | `a[href^="/"]` (first link) |
| Display name | `[data-testid="User-Name"]` |
| Likes count | `[data-testid="like"]` |
| Retweets | `[data-testid="retweet"]` |
| Replies | `[data-testid="reply"]` |
| Profile bio | `[data-testid="UserDescription"]` |
| Followers | `a[href*="/followers"]` |
| Verified badge | `[data-testid="verified"]` |
| Profile image | `[data-testid="UserAvatar"] img` |

## Common Selectors for Google News

| Element | Selector |
|---------|----------|
| Article | `article` |
| Title | `h3, h4, .title` |
| Link | `a[href]` |
| Source | `[data-n-tid]` |
| Snippet | `p, .snippet` |

## Anti-Detection Checklist

- [ ] Use `playwright-stealth`
- [ ] Set realistic viewport (1920x1080)
- [ ] Use common user agent
- [ ] Add random delays between actions
- [ ] Scroll like a human (not too fast)
- [ ] Disable automation flags
- [ ] **Install AdGuard extension** (https://chromewebstore.google.com/detail/adguard-adblocker/bgnkhhnnamicmpeenaelnjfhikgbkllg)
- [ ] Handle errors gracefully

## Extension Setup (Quick)

```python
# Launch browser with AdGuard extension
browser = p.chromium.launch(
    headless=False,  # Required for extensions
    args=[
        '--load-extension=/path/to/adguard-extension',
        '--disable-blink-features=AutomationControlled',
    ]
)
```

**Download:** https://chromewebstore.google.com/detail/adguard-adblocker/bgnkhhnnamicmpeenaelnjfhikgbkllg

## Error Recovery

```python
try:
    page.wait_for_selector('article', timeout=10000)
except:
    # Try alternative or skip
    print("Timeout, trying alternative...")
    # Or continue with partial results
```

## Rate Limit Response

If you see "Rate limit exceeded":
1. Wait 60 seconds
2. Reduce request frequency
3. Use longer delays
4. Consider using fewer queries

## Quick Test

```python
# Test if Playwright works
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    stealth_sync(page)
    page.goto("https://x.com")
    title = page.title()
    print(f"Page title: {title}")
    browser.close()
```
