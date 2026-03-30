#!/usr/bin/env python3
"""
News Search Script for X Account Seed Discovery
Searches news articles using DuckDuckGo (no Playwright required)

Usage:
    python search_news.py --topic "politics" --region "Indonesia" --max-results 20
    python search_news.py --topic "mining policy" --region "Indonesia" --output news.json
"""

import argparse
import json
import re
import sys
import time
import urllib.parse
from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime

import requests
from bs4 import BeautifulSoup


@dataclass
class NewsArticle:
    """Represents a news article."""

    title: str
    url: str
    source: str
    snippet: str
    published_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class DuckDuckGoNewsSearcher:
    """Search news using DuckDuckGo HTML interface."""

    BASE_URL = "https://html.duckduckgo.com/html/"
    NEWS_URL = "https://duckduckgo.com/html/"

    def __init__(self, delay: float = 1.0):
        """
        Initialize searcher.

        Args:
            delay: Delay between requests in seconds (be polite)
        """
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
            }
        )

    def search(self, query: str, max_results: int = 20) -> List[NewsArticle]:
        """
        Search for news articles.

        Args:
            query: Search query
            max_results: Maximum number of results to return

        Returns:
            List of NewsArticle objects
        """
        articles = []
        next_url = None

        # First search - get initial results
        params = {
            "q": f"{query} news",
            "kl": "us-en",  # Region
        }

        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Error searching news: {e}", file=sys.stderr)
            return articles

        # Parse results
        new_articles, next_url = self._parse_results(response.text)
        articles.extend(new_articles)

        # Follow pagination if needed
        while len(articles) < max_results and next_url:
            time.sleep(self.delay)  # Be polite

            try:
                response = self.session.get(next_url, timeout=30)
                response.raise_for_status()
            except requests.RequestException as e:
                print(f"Error fetching next page: {e}", file=sys.stderr)
                break

            new_articles, next_url = self._parse_results(response.text)
            articles.extend(new_articles)

        return articles[:max_results]

    def _parse_results(self, html: str) -> tuple:
        """
        Parse search results from HTML.

        Args:
            html: HTML content

        Returns:
            Tuple of (articles list, next page URL or None)
        """
        soup = BeautifulSoup(html, "html.parser")
        articles = []

        # Find all result items
        results = soup.find_all("div", class_="result")

        for result in results:
            try:
                # Extract title and URL
                title_elem = result.find("a", class_="result__a")
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                url = title_elem.get("href", "")

                # Clean URL (DuckDuckGo redirects)
                if url.startswith("/l/"):
                    # Extract actual URL from DuckDuckGo redirect
                    url_match = re.search(r"uddg=([^&]+)", url)
                    if url_match:
                        url = urllib.parse.unquote(url_match.group(1))
                elif url.startswith("//"):
                    url = "https:" + url

                # Extract snippet
                snippet_elem = result.find("a", class_="result__snippet")
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                # Extract source
                source_elem = result.find("span", class_="result__url__domain")
                source = (
                    source_elem.get_text(strip=True)
                    if source_elem
                    else self._extract_domain(url)
                )

                article = NewsArticle(
                    title=title, url=url, source=source, snippet=snippet
                )
                articles.append(article)

            except Exception as e:
                print(f"Error parsing result: {e}", file=sys.stderr)
                continue

        # Find next page URL
        next_url = None
        next_elem = soup.find("div", class_="nav-link")
        if next_elem:
            next_link = next_elem.find("a")
            if next_link:
                href = next_link.get("href", "")
                if href:
                    next_url = urllib.parse.urljoin(self.BASE_URL, href)

        return articles, next_url

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urllib.parse.urlparse(url)
            return parsed.netloc.replace("www.", "")
        except:
            return "unknown"


def search_news(topic: str, region: str, max_results: int = 20) -> List[NewsArticle]:
    """
    Convenience function to search news.

    Args:
        topic: Topic to search for
        region: Geographic region
        max_results: Maximum results to return

    Returns:
        List of NewsArticle objects
    """
    query = f"{topic} {region}"
    searcher = DuckDuckGoNewsSearcher(delay=1.0)
    return searcher.search(query, max_results)


def main():
    parser = argparse.ArgumentParser(
        description="Search news articles for X Account Seed Discovery"
    )
    parser.add_argument(
        "--topic",
        "-t",
        required=True,
        help='Topic to search for (e.g., "politics", "mining policy")',
    )
    parser.add_argument(
        "--region",
        "-r",
        default="Indonesia",
        help="Geographic region (default: Indonesia)",
    )
    parser.add_argument(
        "--max-results",
        "-n",
        type=int,
        default=20,
        help="Maximum number of articles to fetch (default: 20)",
    )
    parser.add_argument(
        "--output", "-o", help="Output JSON file (default: print to stdout)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between requests in seconds (default: 1.0)",
    )

    args = parser.parse_args()

    print(f"Searching news for: {args.topic} in {args.region}")
    print(f"Max results: {args.max_results}")

    # Search
    searcher = DuckDuckGoNewsSearcher(delay=args.delay)
    query = f"{args.topic} {args.region}"
    articles = searcher.search(query, args.max_results)

    print(f"Found {len(articles)} articles")

    # Prepare output
    output = {
        "query": query,
        "topic": args.topic,
        "region": args.region,
        "total_found": len(articles),
        "timestamp": datetime.now().isoformat(),
        "articles": [article.to_dict() for article in articles],
    }

    # Output results
    json_output = json.dumps(output, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_output)
        print(f"Results saved to: {args.output}")
    else:
        print(json_output)

    return 0 if articles else 1


if __name__ == "__main__":
    sys.exit(main())
