# Example Agent Workflow

This document shows exactly how an AI agent (Opencode/Claude Code) should execute the X Account Seed Discovery skill using Playwright.

## Scenario

**User Request**: "Find X accounts discussing politics in Indonesia"

## Step-by-Step Execution

### Step 1: Setup and Validation

**Agent Action**: Check prerequisites

```python
# Check if playwright is installed
try:
    from playwright.sync_api import sync_playwright
    from playwright_stealth import stealth_sync
    print("✓ Playwright available")
except ImportError:
    print("✗ Playwright not installed")
    print("Install with: pip install playwright playwright-stealth")
    print("Then: playwright install chromium")
```

### Step 2: Search News

**Agent Action**: Search Google News for "politics Indonesia"

```python
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

def search_news(topic, region, max_results=20):
    articles = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()
        stealth_sync(page)
        
        # Navigate to Google News
        query = f"{topic} {region}"
        encoded = query.replace(' ', '+')
        url = f"https://news.google.com/search?q={encoded}&hl=en"
        
        print(f"Searching: {url}")
        page.goto(url, wait_until='networkidle')
        page.wait_for_selector('article', timeout=10000)
        
        # Extract articles
        article_elements = page.query_selector_all('article')[:max_results]
        
        for article in article_elements:
            try:
                title_elem = article.query_selector('h3, h4')
                title = title_elem.inner_text() if title_elem else ""
                
                link_elem = article.query_selector('a[href]')
                href = link_elem.get_attribute('href') if link_elem else ""
                if href.startswith('./'):
                    href = f"https://news.google.com{href[1:]}"
                
                source_elem = article.query_selector('[data-n-tid]')
                source = source_elem.inner_text() if source_elem else ""
                
                articles.append({
                    'title': title,
                    'url': href,
                    'source': source
                })
            except:
                continue
        
        browser.close()
    
    return articles

# Execute
articles = search_news("politics", "Indonesia", 20)
print(f"Found {len(articles)} news articles")
for i, article in enumerate(articles[:5], 1):
    print(f"{i}. {article['title'][:80]}...")
```

**Expected Output**:
```
Found 18 news articles
1. Indonesian Government Announces New Policy on...
2. Political Tensions Rise as Election Approaches...
3. DPR Discusses Controversial Mining Bill...
```

### Step 3: Extract Keywords

**Agent Action**: Extract keywords from article titles

```python
import re
from collections import Counter

def extract_keywords(articles, max_keywords=40):
    # Combine all titles
    all_text = " ".join([a['title'] for a in articles])
    
    # Extract words
    words = re.findall(r'\b[a-zA-Z]{3,}\b', all_text.lower())
    
    # Remove stop words
    stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'boy', 'did', 'she', 'use', 'her', 'way', 'many', 'oil', 'sit', 'set', 'run', 'eat', 'far', 'sea', 'eye', 'ago', 'off', 'too', 'any', 'say', 'man', 'try', 'ask', 'end', 'why', 'let', 'put', 'say', 'she', 'try', 'way', 'own', 'say', 'too', 'old', 'tell', 'very', 'when', 'much', 'would', 'there', 'their', 'what', 'said', 'each', 'which', 'will', 'about', 'could', 'other', 'after', 'first', 'never', 'these', 'think', 'where', 'being', 'every', 'great', 'might', 'shall', 'still', 'those', 'while', 'this', 'that', 'with', 'have', 'from', 'they', 'been', 'were', 'said', 'time', 'than', 'them', 'into', 'just', 'like', 'over', 'also', 'back', 'only', 'know', 'take', 'year', 'good', 'some', 'come', 'make', 'well', 'look', 'want', 'here'}
    words = [w for w in words if w not in stop_words]
    
    # Count and get top keywords
    word_counts = Counter(words)
    keywords = [
        {'keyword': word, 'type': 'keyword', 'frequency': count}
        for word, count in word_counts.most_common(max_keywords)
    ]
    
    return keywords

# Execute
keywords = extract_keywords(articles, 40)
print(f"\nExtracted {len(keywords)} keywords:")
for kw in keywords[:10]:
    print(f"  - {kw['keyword']} ({kw['frequency']})")
```

**Expected Output**:
```
Extracted 35 keywords:
  - pemerintah (12)
  - politik (10)
  - indonesia (9)
  - dpr (8)
  - presiden (7)
  - pemilu (6)
  - partai (5)
  - rakyat (5)
  - hukum (4)
  - ekonomi (4)
```

### Step 4: Search X Posts

**Agent Action**: Search X using extracted keywords

```python
import time
import random

def search_x_posts(queries, max_posts=300):
    all_posts = []
    posts_per_query = max(1, max_posts // len(queries))
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        
        for query in queries:
            if len(all_posts) >= max_posts:
                break
            
            page = context.new_page()
            stealth_sync(page)
            
            try:
                encoded = query.replace(' ', '%20')
                url = f"https://x.com/search?q={encoded}&f=live"
                
                print(f"Searching X: {query}")
                page.goto(url, wait_until='networkidle')
                page.wait_for_selector('article', timeout=10000)
                
                # Scroll and collect
                last_height = 0
                scroll_attempts = 0
                query_posts = []
                
                while len(query_posts) < posts_per_query and scroll_attempts < 15:
                    articles = page.query_selector_all('article')
                    
                    for article in articles:
                        try:
                            # Get post ID
                            link = article.query_selector('a[href*="/status/"]')
                            if not link:
                                continue
                            href = link.get_attribute('href')
                            match = re.search(r'/status/(\d+)', href)
                            if not match:
                                continue
                            post_id = match.group(1)
                            
                            # Skip duplicates
                            if any(p['id'] == post_id for p in all_posts):
                                continue
                            
                            # Get author
                            author_link = article.query_selector('a[href^="/"]')
                            handle = ""
                            if author_link:
                                href_author = author_link.get_attribute('href')
                                handle = href_author.strip('/').split('/')[0]
                            
                            if not handle or handle in ['home', 'explore']:
                                continue
                            
                            # Get display name
                            name_elem = article.query_selector('[data-testid="User-Name"]')
                            display_name = name_elem.inner_text().split('\n')[0] if name_elem else ""
                            
                            # Get text
                            text_elem = article.query_selector('[data-testid="tweetText"]')
                            text = text_elem.inner_text() if text_elem else ""
                            
                            post = {
                                'id': post_id,
                                'text': text,
                                'author_handle': handle,
                                'author_display_name': display_name,
                                'query': query
                            }
                            
                            query_posts.append(post)
                            all_posts.append(post)
                            
                            if len(all_posts) >= max_posts:
                                break
                        except:
                            continue
                    
                    # Scroll
                    page.evaluate('window.scrollBy(0, 800)')
                    time.sleep(random.uniform(1, 3))
                    
                    new_height = page.evaluate('document.body.scrollHeight')
                    if new_height == last_height:
                        scroll_attempts += 1
                    else:
                        scroll_attempts = 0
                        last_height = new_height
                
                page.close()
                print(f"  Found {len(query_posts)} posts")
                time.sleep(random.uniform(2, 4))
                
            except Exception as e:
                print(f"  Error: {e}")
                page.close()
                continue
        
        browser.close()
    
    return all_posts

# Build queries from keywords
keyword_list = [k['keyword'] for k in keywords[:20]]
queries = [f"politics Indonesia"] + [f"{kw} Indonesia" for kw in keyword_list[:10]]
queries = list(set(queries))[:10]

print(f"\nSearching with {len(queries)} queries...")
posts = search_x_posts(queries, 300)
print(f"\nTotal posts collected: {len(posts)}")
```

**Expected Output**:
```
Searching with 10 queries...
Searching X: politics Indonesia
  Found 45 posts
Searching X: pemerintah Indonesia
  Found 38 posts
Searching X: politik Indonesia
  Found 42 posts
...

Total posts collected: 287
```

### Step 5: Aggregate Accounts

**Agent Action**: Extract unique accounts from posts

```python
def aggregate_accounts(posts, max_accounts=100):
    accounts = {}
    
    for post in posts:
        handle = post.get('author_handle', '')
        if not handle:
            continue
        
        # Normalize
        normalized = handle.lower().strip().lstrip('@')
        
        if normalized not in accounts:
            if len(accounts) >= max_accounts:
                continue
            
            accounts[normalized] = {
                'handle': handle,
                'display_name': post.get('author_display_name', ''),
                'posts': [],
                'matched_keywords': set()
            }
        
        accounts[normalized]['posts'].append(post)
        if post.get('query'):
            accounts[normalized]['matched_keywords'].add(post['query'])
    
    # Convert sets to lists
    for account in accounts.values():
        account['matched_keywords'] = list(account['matched_keywords'])
        account['post_count'] = len(account['posts'])
    
    return accounts

# Execute
accounts = aggregate_accounts(posts, 100)
print(f"\nAggregated {len(accounts)} unique accounts")
print("\nTop accounts by post count:")
sorted_accounts = sorted(accounts.items(), key=lambda x: x[1]['post_count'], reverse=True)
for handle, data in sorted_accounts[:10]:
    print(f"  @{handle}: {data['post_count']} posts")
```

**Expected Output**:
```
Aggregated 94 unique accounts

Top accounts by post count:
  @ politik_update: 12 posts
  @ indonesia_hariini: 9 posts
  @ nasional_info: 8 posts
  @ berita_dpr: 7 posts
  @ pemerintah_watch: 6 posts
...
```

### Step 6: Get Profile Details

**Agent Action**: Fetch detailed profile for top accounts

```python
def get_profile(handle):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        stealth_sync(page)
        
        try:
            url = f"https://x.com/{handle}"
            page.goto(url, wait_until='networkidle')
            page.wait_for_selector('[data-testid="UserName"]', timeout=10000)
            
            profile = {'handle': handle}
            
            # Name
            name_elem = page.query_selector('[data-testid="UserName"]')
            if name_elem:
                profile['display_name'] = name_elem.inner_text().split('\n')[0]
            
            # Bio
            bio_elem = page.query_selector('[data-testid="UserDescription"]')
            if bio_elem:
                profile['bio'] = bio_elem.inner_text()
            
            # Followers
            for count_type in ['followers', 'following']:
                try:
                    elem = page.query_selector(f'a[href*="/{count_type}"]')
                    if elem:
                        text = elem.inner_text()
                        text = text.replace(',', '').replace('K', '000').replace('M', '000000')
                        numbers = re.findall(r'\d+', text)
                        if numbers:
                            profile[f'{count_type}_count'] = int(numbers[0])
                except:
                    pass
            
            # Verified
            profile['verified'] = bool(page.query_selector('[data-testid="verified"]'))
            
            browser.close()
            return profile
            
        except Exception as e:
            print(f"Error getting @{handle}: {e}")
            browser.close()
            return None

# Get details for top 20 accounts
print("\nFetching profile details...")
detailed_accounts = []
for handle, data in sorted_accounts[:20]:
    profile = get_profile(handle)
    if profile:
        profile['posts'] = data['posts']
        profile['matched_keywords'] = data['matched_keywords']
        detailed_accounts.append(profile)
        print(f"  ✓ @{handle}: {profile.get('followers_count', 'N/A')} followers")
    else:
        print(f"  ✗ @{handle}: Failed")
    time.sleep(1)  # Be nice to X

print(f"\nSuccessfully fetched {len(detailed_accounts)} profiles")
```

**Expected Output**:
```
Fetching profile details...
  ✓ @politik_update: 15400 followers
  ✓ @indonesia_hariini: 8900 followers
  ✓ @nasional_info: 12300 followers
  ✓ @berita_dpr: 5600 followers
  ✓ @pemerintah_watch: 21000 followers
...

Successfully fetched 18 profiles
```

### Step 7: Apply Filters

**Agent Action**: Apply deterministic filters

```python
# Filter criteria from input
min_followers = 5000
min_posts = 50

filtered = []
for account in detailed_accounts:
    followers = account.get('followers_count', 0) or 0
    posts = len(account.get('posts', []))
    
    if followers >= min_followers and posts >= min_posts:
        filtered.append(account)
        print(f"✓ @{account['handle']}: {followers} followers, {posts} posts")
    else:
        print(f"✗ @{account['handle']}: {followers} followers (min: {min_followers}), {posts} posts (min: {min_posts})")

print(f"\n{len(filtered)} accounts passed filters")
```

### Step 8: AI Evaluation

**Agent Action**: Evaluate accounts with LLM

```python
# This would use the AI judge prompt from the skill
# For each account, build prompt and call LLM

def evaluate_account(account, topic, region):
    """
    Build prompt and call LLM for evaluation.
    In practice, this uses the seed_judge.md prompt.
    """
    prompt = f"""Evaluate this X account for relevance to {topic} in {region}.

Handle: @{account['handle']}
Name: {account.get('display_name', '')}
Bio: {account.get('bio', '')}
Followers: {account.get('followers_count', 0)}
Posts about topic: {len(account.get('posts', []))}

Respond with JSON:
{{"decision": "eligible|not_eligible|uncertain", "score": 0-100, "reason_short": "..."}}
"""
    
    # Call LLM (OpenAI, Anthropic, etc.)
    # Return evaluation result
    pass

# Evaluate all filtered accounts
print("\nEvaluating accounts with AI...")
evaluations = []
for account in filtered:
    result = evaluate_account(account, "politics", "Indonesia")
    evaluations.append({
        'account': account,
        'evaluation': result
    })
    print(f"@{account['handle']}: {result['decision']} (score: {result['score']})")
```

### Step 9: Save Results

**Agent Action**: Save to database

```python
# Save to SQLite using the schema
# This would use the database.py functions
# Insert into: runs, accounts, account_evaluations, account_topic_signals

print("\nSaving results to database...")
# ... database operations ...
print("✓ Results saved")
```

### Step 10: Return Output

**Agent Action**: Build and return output

```python
output = {
    'run_id': '20260330T120000Z-abc123',
    'topic': 'politics',
    'region': 'Indonesia',
    'total_news_articles': len(articles),
    'total_keywords': len(keywords),
    'total_x_posts': len(posts),
    'total_accounts_aggregated': len(accounts),
    'total_prefiltered': len(detailed_accounts) - len(filtered),
    'total_ai_evaluated': len(evaluations),
    'total_eligible': len([e for e in evaluations if e['evaluation']['decision'] == 'eligible']),
    'total_not_eligible': len([e for e in evaluations if e['evaluation']['decision'] == 'not_eligible']),
    'total_uncertain': len([e for e in evaluations if e['evaluation']['decision'] == 'uncertain']),
    'eligible_accounts': [
        {
            'handle': e['account']['handle'],
            'display_name': e['account'].get('display_name'),
            'followers_count': e['account'].get('followers_count'),
            'decision': e['evaluation']['decision'],
            'score': e['evaluation']['score'],
            'reason_short': e['evaluation']['reason_short']
        }
        for e in evaluations
        if e['evaluation']['decision'] == 'eligible'
    ],
    'errors': []
}

print("\n" + "="*60)
print("FINAL RESULTS")
print("="*60)
print(f"Eligible accounts: {output['total_eligible']}")
print(f"Not eligible: {output['total_not_eligible']}")
print(f"Uncertain: {output['total_uncertain']}")
print("\nEligible accounts:")
for acc in output['eligible_accounts']:
    print(f"  @{acc['handle']} - {acc['display_name']} (Score: {acc['score']})")
```

## Summary

This workflow shows exactly how an agent should:
1. Use Playwright to search news
2. Extract keywords from articles
3. Use Playwright with stealth to search X posts
4. Aggregate unique accounts
5. Get detailed profile information
6. Apply filters
7. Evaluate with AI
8. Save to database
9. Return structured output

Each step includes error handling, rate limiting protection, and anti-detection measures.
