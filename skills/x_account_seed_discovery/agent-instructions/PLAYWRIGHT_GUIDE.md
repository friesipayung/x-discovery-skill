# Agent Instructions: Using Playwright for X Account Seed Discovery

These instructions guide AI agents (Opencode, Claude Code, etc.) on how to use Playwright with stealth mode to perform news searches and X.com profile searches for the X Account Seed Discovery skill.

## Overview

Instead of using APIs, the agent will:
1. Use Playwright to browse and search news sources
2. Use Playwright with stealth mode to search X.com profiles
3. Extract data from web pages
4. Feed results into the skill workflow

## Prerequisites

The agent must have:
- Playwright installed (`playwright install chromium`)
- `playwright-stealth` package (`pip install playwright-stealth`)
- **AdGuard AdBlocker extension** (recommended for cleaner scraping)
- Ability to run Python code with Playwright

### Installing AdGuard Extension

Download and install the AdGuard extension for cleaner page scraping and better stealth:

**Extension URL:** https://chromewebstore.google.com/detail/adguard-adblocker/bgnkhhnnamicmpeenaelnjfhikgbkllg

**Why use AdGuard:**
- Blocks ads that interfere with element selection
- Reduces page load times
- Helps avoid detection by blocking trackers
- Cleaner DOM for reliable scraping

**Setup with Playwright:**

```python
from playwright.sync_api import sync_playwright

# Path to downloaded AdGuard extension (extracted .crx or unpacked folder)
adguard_path = "/path/to/adguard-extension"  # Or .crx file

def launch_browser_with_adguard():
    with sync_playwright() as p:
        # Launch with extension
        browser = p.chromium.launch(
            headless=False,  # Extensions require headful mode
            args=[
                f'--disable-extensions-except={adguard_path}',
                f'--load-extension={adguard_path}',
                '--disable-blink-features=AutomationControlled',
            ]
        )
        return browser
```

**Note:** Chrome extensions require `headless=False`. For fully headless operation, you can still use AdGuard's filtering capabilities or use the stealth mode without the extension.

**Alternative: Use AdGuard DNS or filtering without extension:**
```python
# Block ad/tracking domains at browser level
context = browser.new_context(
    bypass_csp=True,
    # Additional args to block common ad domains
)
```

## Step 1: News Search with Playwright

### Option A: Google News (Recommended)

```python
# Search Google News for articles about topic + region
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

def search_google_news(topic, region, max_results=20):
    """
    Search Google News using Playwright.
    
    Args:
        topic: Search topic (e.g., "politics", "mining policy")
        region: Geographic region (e.g., "Indonesia")
        max_results: Maximum articles to collect
    
    Returns:
        List of dicts with title, url, source, snippet
    """
    query = f"{topic} {region}"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()
        stealth_sync(page)
        
        # Navigate to Google News
        encoded_query = query.replace(' ', '+')
        url = f"https://news.google.com/search?q={encoded_query}&hl=en"
        page.goto(url, wait_until='networkidle')
        
        # Wait for articles to load
        page.wait_for_selector('article', timeout=10000)
        
        # Extract articles
        articles = []
        article_elements = page.query_selector_all('article')[:max_results]
        
        for article in article_elements:
            try:
                # Extract title
                title_elem = article.query_selector('h3, h4, .title')
                title = title_elem.inner_text() if title_elem else ""
                
                # Extract link
                link_elem = article.query_selector('a[href]')
                href = link_elem.get_attribute('href') if link_elem else ""
                if href.startswith('./'):
                    href = f"https://news.google.com{href[1:]}"
                
                # Extract source
                source_elem = article.query_selector('[data-n-tid]')
                source = source_elem.inner_text() if source_elem else ""
                
                # Extract snippet
                snippet_elem = article.query_selector('p, .snippet')
                snippet = snippet_elem.inner_text() if snippet_elem else ""
                
                articles.append({
                    'title': title,
                    'url': href,
                    'source': source,
                    'snippet': snippet
                })
            except:
                continue
        
        browser.close()
        return articles
```

### Option B: DuckDuckGo News (No API Key)

```python
def search_duckduckgo_news(topic, region, max_results=20):
    """
    Search DuckDuckGo News (free, no API key needed).
    """
    query = f"{topic} {region} news"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        stealth_sync(page)
        
        # Navigate to DuckDuckGo
        encoded_query = query.replace(' ', '+')
        url = f"https://duckduckgo.com/?q={encoded_query}&iar=news&ia=news"
        page.goto(url, wait_until='networkidle')
        
        # Wait for results
        page.wait_for_selector('.result', timeout=10000)
        
        # Extract results
        articles = []
        results = page.query_selector_all('.result')[:max_results]
        
        for result in results:
            try:
                title_elem = result.query_selector('.result__a')
                title = title_elem.inner_text() if title_elem else ""
                
                link_elem = result.query_selector('.result__a')
                href = link_elem.get_attribute('href') if link_elem else ""
                
                snippet_elem = result.query_selector('.result__snippet')
                snippet = snippet_elem.inner_text() if snippet_elem else ""
                
                articles.append({
                    'title': title,
                    'url': href,
                    'source': 'DuckDuckGo',
                    'snippet': snippet
                })
            except:
                continue
        
        browser.close()
        return articles
```

### Option C: Bing News

```python
def search_bing_news(topic, region, max_results=20):
    """
    Search Bing News using Playwright.
    """
    query = f"{topic} {region}"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        stealth_sync(page)
        
        encoded_query = query.replace(' ', '+')
        url = f"https://www.bing.com/news/search?q={encoded_query}"
        page.goto(url, wait_until='networkidle')
        
        # Wait for news cards
        page.wait_for_selector('.news-card', timeout=10000)
        
        articles = []
        cards = page.query_selector_all('.news-card')[:max_results]
        
        for card in cards:
            try:
                title_elem = card.query_selector('[role="heading"]')
                title = title_elem.inner_text() if title_elem else ""
                
                link_elem = card.query_selector('a')
                href = link_elem.get_attribute('href') if link_elem else ""
                
                source_elem = card.query_selector('.source')
                source = source_elem.inner_text() if source_elem else ""
                
                articles.append({
                    'title': title,
                    'url': href,
                    'source': source,
                    'snippet': ''
                })
            except:
                continue
        
        browser.close()
        return articles
```

## Step 2: Extract Keywords from News

After collecting news articles, extract keywords:

```python
import re
from collections import Counter

def extract_keywords_from_news(articles, max_keywords=40):
    """
    Extract keywords from news article titles and snippets.
    
    Args:
        articles: List of article dicts from news search
        max_keywords: Maximum keywords to extract
    
    Returns:
        List of dicts with keyword, type, frequency
    """
    # Combine all text
    all_text = " ".join([
        f"{a.get('title', '')} {a.get('snippet', '')}"
        for a in articles
    ])
    
    # Common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
    }
    
    # Extract words (3+ characters)
    words = re.findall(r'\b[a-zA-Z]{3,}\b', all_text.lower())
    words = [w for w in words if w not in stop_words]
    
    # Count frequencies
    word_counts = Counter(words)
    
    # Get top keywords
    keywords = []
    for word, count in word_counts.most_common(max_keywords):
        keywords.append({
            'keyword': word,
            'type': 'keyword',
            'frequency': count
        })
    
    # Extract entities (capitalized phrases)
    entity_pattern = r'\b[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)+\b'
    entities = re.findall(entity_pattern, all_text)
    entity_counts = Counter(entities)
    
    for entity, count in entity_counts.most_common(max_keywords // 2):
        if entity.lower() not in stop_words and len(entity) > 3:
            keywords.append({
                'keyword': entity,
                'type': 'entity',
                'frequency': count
            })
    
    # Sort by frequency
    keywords.sort(key=lambda x: x['frequency'], reverse=True)
    return keywords[:max_keywords]
```

## Step 3: Search X.com with Playwright (Stealth Mode)

### Search X Posts

```python
def search_x_posts(queries, max_posts=300, region_hint=None):
    """
    Search X.com posts using Playwright with stealth mode.
    
    Args:
        queries: List of search queries (from keywords)
        max_posts: Maximum posts to collect
        region_hint: Optional region for context
    
    Returns:
        List of dicts with post data and author info
    """
    from playwright.sync_api import sync_playwright
    from playwright_stealth import stealth_sync
    import time
    import random
    
    all_posts = []
    posts_per_query = max(1, max_posts // len(queries))
    
    with sync_playwright() as p:
        # Launch with anti-detection
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York'
        )
        
        # Add stealth scripts
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            window.chrome = { runtime: {} };
        """)
        
        for query in queries:
            if len(all_posts) >= max_posts:
                break
            
            page = context.new_page()
            stealth_sync(page)
            
            try:
                # Build search URL
                encoded_query = query.replace(' ', '%20')
                search_url = f"https://x.com/search?q={encoded_query}&f=live"
                
                # Navigate
                page.goto(search_url, wait_until='networkidle')
                
                # Wait for posts to load
                page.wait_for_selector('article', timeout=10000)
                
                # Scroll and collect posts
                last_height = 0
                scroll_attempts = 0
                max_scroll_attempts = 20
                query_posts = []
                
                while len(query_posts) < posts_per_query and scroll_attempts < max_scroll_attempts:
                    # Extract posts from current view
                    articles = page.query_selector_all('article')
                    
                    for article in articles:
                        try:
                            # Extract post ID from URL
                            link_elem = article.query_selector('a[href*="/status/"]')
                            if not link_elem:
                                continue
                            
                            href = link_elem.get_attribute('href')
                            if not href:
                                continue
                            
                            # Extract status ID
                            import re
                            match = re.search(r'/status/(\d+)', href)
                            if not match:
                                continue
                            
                            post_id = match.group(1)
                            
                            # Skip if already collected
                            if any(p['id'] == post_id for p in all_posts):
                                continue
                            
                            # Extract author
                            author_elem = article.query_selector('a[href^="/"]')
                            author_handle = ""
                            if author_elem:
                                author_href = author_elem.get_attribute('href')
                                if author_href:
                                    author_handle = author_href.strip('/').split('/')[0]
                            
                            # Skip if no handle
                            if not author_handle or author_handle in ['home', 'explore', 'notifications']:
                                continue
                            
                            # Extract display name
                            display_name_elem = article.query_selector('[data-testid="User-Name"]')
                            display_name = ""
                            if display_name_elem:
                                display_name = display_name_elem.inner_text().split('\n')[0]
                            
                            # Extract post text
                            text_elem = article.query_selector('[data-testid="tweetText"]')
                            text = text_elem.inner_text() if text_elem else ""
                            
                            # Extract engagement
                            likes = extract_count(article, '[data-testid="like"]')
                            retweets = extract_count(article, '[data-testid="retweet"]')
                            replies = extract_count(article, '[data-testid="reply"]')
                            
                            post = {
                                'id': post_id,
                                'text': text,
                                'author_handle': author_handle,
                                'author_display_name': display_name,
                                'likes': likes,
                                'retweets': retweets,
                                'replies': replies,
                                'url': f"https://x.com{href}",
                                'query': query
                            }
                            
                            query_posts.append(post)
                            all_posts.append(post)
                            
                            if len(all_posts) >= max_posts:
                                break
                            
                        except Exception as e:
                            continue
                    
                    # Scroll down
                    page.evaluate('window.scrollBy(0, 800)')
                    time.sleep(random.uniform(1, 3))
                    
                    # Check if we've reached the end
                    new_height = page.evaluate('document.body.scrollHeight')
                    if new_height == last_height:
                        scroll_attempts += 1
                    else:
                        scroll_attempts = 0
                        last_height = new_height
                
                page.close()
                
                # Random delay between queries
                time.sleep(random.uniform(2, 5))
                
            except Exception as e:
                print(f"Error searching query '{query}': {e}")
                page.close()
                continue
        
        browser.close()
    
    return all_posts[:max_posts]

def extract_count(article, selector):
    """Extract numeric count from an element."""
    try:
        elem = article.query_selector(selector)
        if elem:
            text = elem.inner_text()
            # Parse numbers like "1.2K", "5K", "1,234"
            text = text.replace(',', '').replace('K', '000').replace('M', '000000')
            numbers = re.findall(r'\d+', text)
            if numbers:
                return int(numbers[0])
    except:
        pass
    return 0
```

### Get X Profile Information

```python
def get_x_profile(handle):
    """
    Get detailed profile information for an X account.
    
    Args:
        handle: X handle (with or without @)
    
    Returns:
        Dict with profile information or None if not found
    """
    from playwright.sync_api import sync_playwright
    from playwright_stealth import stealth_sync
    
    handle = handle.lstrip('@')
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)
        
        page = context.new_page()
        stealth_sync(page)
        
        try:
            profile_url = f"https://x.com/{handle}"
            page.goto(profile_url, wait_until='networkidle')
            
            # Wait for profile to load
            page.wait_for_selector('[data-testid="UserName"]', timeout=10000)
            
            # Extract profile info
            profile = {}
            
            # Display name
            name_elem = page.query_selector('[data-testid="UserName"]')
            if name_elem:
                profile['display_name'] = name_elem.inner_text().split('\n')[0]
            
            # Bio
            bio_elem = page.query_selector('[data-testid="UserDescription"]')
            if bio_elem:
                profile['bio'] = bio_elem.inner_text()
            
            # Follower counts
            profile['followers_count'] = extract_profile_count(page, 'followers')
            profile['following_count'] = extract_profile_count(page, 'following')
            profile['post_count'] = extract_profile_count(page, 'posts')
            
            # Verification
            profile['verified'] = bool(page.query_selector('[data-testid="verified"]'))
            
            # Profile image
            img_elem = page.query_selector('[data-testid="UserAvatar"] img')
            if img_elem:
                profile['profile_image_url'] = img_elem.get_attribute('src')
            
            # Location
            location_elem = page.query_selector('[data-testid="UserLocation"]')
            if location_elem:
                profile['location_text'] = location_elem.inner_text()
            
            profile['handle'] = handle
            profile['profile_url'] = profile_url
            
            page.close()
            browser.close()
            
            return profile
            
        except Exception as e:
            print(f"Error getting profile for @{handle}: {e}")
            page.close()
            browser.close()
            return None

def extract_profile_count(page, count_type):
    """Extract count from profile page."""
    try:
        # Look for links containing the count type
        selectors = [
            f'a[href*="/{count_type}"]',
        ]
        
        for selector in selectors:
            elem = page.query_selector(selector)
            if elem:
                text = elem.inner_text()
                # Extract number
                text = text.replace(',', '').replace('K', '000').replace('M', '000000')
                numbers = re.findall(r'\d+', text)
                if numbers:
                    return int(numbers[0])
    except:
        pass
    return None
```

### Fallback: Using Nitter (When X.com is Inaccessible)

If X.com is blocked, requires login, or returns errors, use **Nitter** instances as a proxy:

**Nitter** is a free and open-source alternative Twitter/X front-end that provides public access to posts and profiles without authentication. See https://github.com/zedeus/nitter/wiki/Instances for the full list of instances.

**Recommended instances:**
- https://nitter.net (official)
- https://xcancel.com
- https://nitter.privacyredirect.com
- https://nitter.poast.org
- https://nitter.tiekoetter.com

#### Search Posts via Nitter

```python
def search_nitter_posts(query, max_posts=100, instance="nitter.net"):
    """
    Search X/Twitter posts via Nitter proxy.
    
    Args:
        query: Search query (e.g., "politics Indonesia")
        max_posts: Maximum posts to collect
        instance: Nitter instance URL (default: nitter.net)
    
    Returns:
        List of post dicts with author info
    """
    from playwright.sync_api import sync_playwright
    from playwright_stealth import stealth_sync
    import time
    import urllib.parse
    
    posts = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        stealth_sync(page)
        
        try:
            # Build Nitter search URL
            encoded_query = urllib.parse.quote(query)
            url = f"https://{instance}/search?f=tweets&q={encoded_query}"
            
            print(f"Searching Nitter ({instance}): {query}")
            page.goto(url, wait_until='domcontentloaded')
            
            # Wait for page to fully load
            time.sleep(3)
            
            # Wait for content to load (Nitter uses .timeline-item)
            page.wait_for_selector('.timeline-item', timeout=15000)
            
            # Extract posts
            post_elements = page.query_selector_all('.timeline-item')
            
            for elem in post_elements[:max_posts]:
                try:
                    # Skip "show more" items
                    if elem.query_selector('a.show-more'):
                        continue
                    
                    # Extract author handle from username link
                    author_elem = elem.query_selector('a.username')
                    handle = ""
                    if author_elem:
                        handle = author_elem.inner_text().strip().lstrip('@')
                    
                    # Extract display name
                    name_elem = elem.query_selector('a.fullname')
                    display_name = name_elem.inner_text().strip() if name_elem else handle
                    
                    # Extract post text
                    text_elem = elem.query_selector('.tweet-content')
                    text = text_elem.inner_text() if text_elem else ""
                    
                    # Extract post URL and ID
                    link_elem = elem.query_selector('a.tweet-link')
                    post_url = ""
                    post_id = ""
                    if link_elem:
                        href = link_elem.get_attribute('href') or ""
                        post_url = f"https://{instance}{href}" if href.startswith('/') else href
                        # Extract ID from /username/status/123456
                        parts = href.split('/')
                        if len(parts) >= 3:
                            post_id = parts[-1]
                    
                    # Extract engagement stats
                    stats = elem.query_selector('.tweet-stats')
                    likes = 0
                    retweets = 0
                    replies = 0
                    if stats:
                        like_elem = stats.query_selector('.icon-heart')
                        if like_elem:
                            likes = extract_nitter_stat(like_elem.inner_text())
                        rt_elem = stats.query_selector('.icon-retweet')
                        if rt_elem:
                            retweets = extract_nitter_stat(rt_elem.inner_text())
                        reply_elem = stats.query_selector('.icon-comment')
                        if reply_elem:
                            replies = extract_nitter_stat(reply_elem.inner_text())
                    
                    # Extract timestamp
                    time_elem = elem.query_selector('.tweet-date a')
                    post_time = time_elem.get_attribute('title') if time_elem else ""
                    
                    if handle and text:
                        posts.append({
                            'id': post_id or str(hash(text))[:10],
                            'text': text,
                            'author_handle': handle,
                            'author_display_name': display_name,
                            'url': post_url,
                            'created_at': post_time,
                            'likes': likes,
                            'retweets': retweets,
                            'replies': replies,
                            'query': query
                        })
                except:
                    continue
            
            browser.close()
            print(f"  Found {len(posts)} posts via Nitter")
            
        except Exception as e:
            print(f"Error searching Nitter: {e}")
            browser.close()
    
    return posts


def extract_nitter_stat(text):
    """Extract number from Nitter stat text (handles K, M suffixes)."""
    text = text.strip().replace(',', '')
    match = re.search(r'([\d.]+)\s*([KMB]?)', text, re.I)
    if match:
        num = float(match.group(1))
        suffix = match.group(2).upper()
        if suffix == 'K':
            num *= 1000
        elif suffix == 'M':
            num *= 1000000
        elif suffix == 'B':
            num *= 1000000000
        return int(num)
    return 0
```

#### Get Profile via Nitter

```python
def get_nitter_profile(handle, instance="nitter.net"):
    """
    Get X/Twitter profile via Nitter proxy.
    
    Args:
        handle: X handle (with or without @)
        instance: Nitter instance URL (default: nitter.net)
    
    Returns:
        Dict with profile information or None
    """
    from playwright.sync_api import sync_playwright
    from playwright_stealth import stealth_sync
    
    handle = handle.lstrip('@')
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        stealth_sync(page)
        
        try:
            url = f"https://{instance}/{handle}"
            print(f"Fetching profile via Nitter ({instance}): @{handle}")
            
            page.goto(url, wait_until='domcontentloaded')
            time.sleep(3)  # Wait for page to fully load
            
            # Wait for profile card to load
            page.wait_for_selector('.profile-card', timeout=15000)
            
            profile = {'handle': handle, 'profile_url': url}
            
            # Display name
            name_elem = page.query_selector('.profile-card-fullname')
            if name_elem:
                profile['display_name'] = name_elem.inner_text().strip()
            else:
                profile['display_name'] = handle
            
            # Bio
            bio_elem = page.query_selector('.profile-bio')
            if bio_elem:
                profile['bio'] = bio_elem.inner_text()
            
            # Stats (followers, following, posts)
            stat_elems = page.query_selector_all('.profile-stat')
            for stat in stat_elems:
                try:
                    label_elem = stat.query_selector('.profile-stat-header')
                    value_elem = stat.query_selector('.profile-stat-num')
                    
                    if not label_elem or not value_elem:
                        continue
                    
                    label = label_elem.inner_text().lower()
                    value_text = value_elem.inner_text()
                    value = extract_nitter_stat(value_text)
                    
                    if 'follower' in label:
                        profile['followers_count'] = value
                    elif 'following' in label:
                        profile['following_count'] = value
                    elif 'tweet' in label or 'post' in label:
                        profile['posts_count'] = value
                except:
                    continue
            
            # Profile image
            img_elem = page.query_selector('.profile-card-avatar')
            if img_elem:
                src = img_elem.get_attribute('src')
                if src and src.startswith('//'):
                    src = 'https:' + src
                profile['profile_image_url'] = src
            
            # Banner image
            banner_elem = page.query_selector('.profile-banner')
            if banner_elem:
                src = banner_elem.get_attribute('src')
                if src and src.startswith('//'):
                    src = 'https:' + src
                profile['banner_image_url'] = src
            
            # Verified badge
            profile['is_verified'] = bool(page.query_selector('.verified-icon'))
            
            # Location
            location_elem = page.query_selector('.profile-location')
            if location_elem:
                profile['location'] = location_elem.inner_text()
            
            # Website
            website_elem = page.query_selector('.profile-website')
            if website_elem:
                profile['website'] = website_elem.get_attribute('href')
            
            # Joined date
            joined_elem = page.query_selector('.profile-joindate')
            if joined_elem:
                profile['joined_date'] = joined_elem.inner_text()
            
            browser.close()
            print(f"  ✓ Profile fetched: {profile.get('display_name', handle)}")
            return profile
            
        except Exception as e:
            print(f"  ✗ Error fetching profile via Nitter: {e}")
            browser.close()
            return None
```

#### When to Use Nitter

**Use Nitter when:**
- X.com requires login/authentication
- X.com returns rate limit errors
- X.com is blocked in your region
- X.com layout changes break selectors
- You want free, public access without API keys

**Advantages over sotwe.com:**
- Open-source with multiple instances (better redundancy)
- Consistent API/layout across instances
- No authentication required
- Better community support and maintenance

**Limitations:**
- May not have all posts (only cached/public ones)
- Instances can go down (have backups ready)
- Rate limits still apply
- Check instance status: https://status.d420.de/

**Example Usage:**

```python
# Try X.com first, fallback to Nitter
def search_posts_with_fallback(queries, max_posts=300):
    all_posts = []
    
    # Try multiple Nitter instances
    instances = ['nitter.net', 'xcancel.com', 'nitter.privacyredirect.com']
    
    for query in queries:
        # Try X.com first
        try:
            posts = search_x_posts([query], max_posts=50)
            if posts:
                all_posts.extend(posts)
                continue
        except Exception as e:
            print(f"X.com failed for '{query}': {e}")
        
        # Fallback to Nitter instances
        for instance in instances:
            try:
                posts = search_nitter_posts(query, max_posts=50, instance=instance)
                if posts:
                    all_posts.extend(posts)
                    print(f"Using Nitter fallback ({instance}) for '{query}'")
                    break
            except Exception as e:
                print(f"Nitter {instance} failed for '{query}': {e}")
                continue
    
    return all_posts
```

## Step 4: Aggregate Accounts from Posts

```python
def aggregate_accounts_from_posts(posts, max_accounts=100):
    """
    Aggregate unique accounts from collected posts.
    
    Args:
        posts: List of post dicts from search_x_posts
        max_accounts: Maximum unique accounts to collect
    
    Returns:
        Dict mapping normalized handle to account data
    """
    accounts = {}
    
    for post in posts:
        handle = post.get('author_handle', '')
        if not handle:
            continue
        
        # Normalize handle
        normalized = handle.lower().strip().lstrip('@')
        
        if normalized in accounts:
            # Add post to existing account
            accounts[normalized]['posts'].append(post)
        else:
            # New account
            if len(accounts) >= max_accounts:
                continue
            
            accounts[normalized] = {
                'handle': handle,
                'display_name': post.get('author_display_name', ''),
                'posts': [post],
                'matched_keywords': set()
            }
        
        # Track which query/keyword matched
        if post.get('query'):
            accounts[normalized]['matched_keywords'].add(post['query'])
    
    # Convert sets to lists for JSON serialization
    for account in accounts.values():
        account['matched_keywords'] = list(account['matched_keywords'])
        account['post_count'] = len(account['posts'])
    
    return accounts
```

## Complete Agent Workflow

Here's how an agent should execute the full workflow:

```python
def run_x_discovery_skill(input_params):
    """
    Complete X Account Seed Discovery workflow using Playwright.
    
    Args:
        input_params: Dict matching input.json schema
    
    Returns:
        Dict matching output.json schema
    """
    topic = input_params['topic']
    region = input_params.get('region', 'Indonesia')
    max_news = input_params.get('max_news_articles', 20)
    max_keywords = input_params.get('max_keywords', 40)
    max_posts = input_params.get('max_x_posts', 300)
    max_accounts = input_params.get('max_accounts_to_aggregate', 100)
    
    print(f"Starting X Account Seed Discovery for: {topic} in {region}")
    
    # Step 1: Search news
    print("Step 1: Searching news...")
    articles = search_google_news(topic, region, max_news)
    print(f"  Found {len(articles)} articles")
    
    # Step 2: Extract keywords
    print("Step 2: Extracting keywords...")
    keywords = extract_keywords_from_news(articles, max_keywords)
    print(f"  Extracted {len(keywords)} keywords")
    
    # Step 3: Build search queries
    keyword_list = [k['keyword'] for k in keywords[:max_keywords]]
    queries = [f"{topic} {region}"] + [f"{kw} {region}" for kw in keyword_list[:20]]
    queries = list(set(queries))[:15]  # Deduplicate and limit
    print(f"  Built {len(queries)} search queries")
    
    # Step 4: Search X posts
    print("Step 4: Searching X posts...")
    posts = search_x_posts(queries, max_posts, region)
    print(f"  Found {len(posts)} posts")
    
    # Step 5: Aggregate accounts
    print("Step 5: Aggregating accounts...")
    accounts = aggregate_accounts_from_posts(posts, max_accounts)
    print(f"  Aggregated {len(accounts)} unique accounts")
    
    # Step 6: Get detailed profile info (for top accounts)
    print("Step 6: Fetching profile details...")
    detailed_accounts = []
    for handle, account_data in list(accounts.items())[:50]:
        profile = get_x_profile(handle)
        if profile:
            profile['posts'] = account_data['posts']
            profile['matched_keywords'] = account_data['matched_keywords']
            detailed_accounts.append(profile)
        
        # Small delay between profile requests
        import time
        time.sleep(1)
    
    print(f"  Fetched details for {len(detailed_accounts)} accounts")
    
    # Return results for further processing (filters, AI eval, etc.)
    return {
        'articles': articles,
        'keywords': keywords,
        'posts': posts,
        'accounts': detailed_accounts
    }
```

## Anti-Detection Best Practices

1. **Always use stealth mode**:
   ```python
   from playwright_stealth import stealth_sync
   stealth_sync(page)
   ```

2. **Random delays**:
   ```python
   import time, random
   time.sleep(random.uniform(1, 3))
   ```

3. **Human-like scrolling**:
   ```python
   page.evaluate('window.scrollBy(0, 800)')
   ```

4. **Custom user agent**:
   ```python
   context = browser.new_context(
       user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
   )
   ```

5. **Viewport size**:
   ```python
   viewport={'width': 1920, 'height': 1080}
   ```

6. **Use AdGuard extension** (highly recommended):
   ```python
   # Install: https://chromewebstore.google.com/detail/adguard-adblocker/bgnkhhnnamicmpeenaelnjfhikgbkllg
   browser = p.chromium.launch(
       headless=False,  # Required for extensions
       args=[
           f'--load-extension=/path/to/adguard',
           '--disable-blink-features=AutomationControlled',
       ]
   )
   ```
   - Blocks ads and trackers
   - Reduces page load times
   - Cleaner DOM for reliable scraping
   - Helps avoid detection

## Error Handling

```python
try:
    # Attempt search
    results = search_x_posts(queries, max_posts)
except Exception as e:
    print(f"Search failed: {e}")
    # Fallback: try different approach or reduce parameters
    results = []
```

## Rate Limiting Protection

If you encounter rate limiting:

1. **Increase delays**:
   ```python
   time.sleep(random.uniform(3, 7))  # Longer delays
   ```

2. **Reduce batch size**:
   ```python
   max_posts = 100  # Instead of 300
   ```

3. **Use proxy rotation** (if available)

4. **Take breaks between major operations**:
   ```python
   time.sleep(10)  # 10 second break
   ```

## Notes for Agents

- **X/Twitter may require login** for extensive searches
- If login required, ask user for credentials or use alternative approach
- **Stealth mode helps but isn't foolproof** - X may still detect automation
- **Always respect rate limits** - don't hammer the site
- **Handle errors gracefully** - some searches may fail, continue with what you have
- **Save progress periodically** - don't lose work if something fails
