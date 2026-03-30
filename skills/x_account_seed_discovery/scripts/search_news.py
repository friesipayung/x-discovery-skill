#!/usr/bin/env python3
"""
News Search Script for X Account Seed Discovery
Searches news articles using Serper.dev (default, requires API key), SerpAPI (requires API key), or DuckDuckGo (free)

Usage:
    # Serper.dev (default, requires API key - recommended, cheapest)
    python search_news.py --topic "politics" --region "Indonesia" --max-results 20

    # SerpAPI Google News (requires API key)
    python search_news.py --topic "politics" --region "Indonesia" --provider serpapi --max-results 20

    # DuckDuckGo (free, no API key)
    python search_news.py --topic "politics" --region "Indonesia" --provider duckduckgo --max-results 20

    python search_news.py --topic "mining policy" --region "Indonesia" --output news.json

Environment:
    SERPER_API_KEY - Required for Serper provider, default (get from https://serper.dev)
    SERPAPI_KEY - Required for SerpAPI provider (get from https://serpapi.com)
"""

import argparse
import json
import os
import re
import socket
import sys
import time
import urllib.parse
from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime

import requests
from bs4 import BeautifulSoup


# Google DNS-over-HTTPS (DoH) endpoint
DOH_URL = "https://dns.google/resolve"


class GoogleDoHResolver:
    """DNS resolver using Google DNS-over-HTTPS (DoH)."""

    @staticmethod
    def resolve(hostname: str) -> str:
        """Resolve hostname using Google DoH."""
        try:
            response = requests.get(
                DOH_URL,
                params={"name": hostname, "type": "A", "do": "false", "cd": "false"},
                headers={"Accept": "application/dns-json"},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("Status") == 0 and data.get("Answer"):
                # Return first A record
                for answer in data["Answer"]:
                    if answer.get("type") == 1:  # A record
                        return answer["data"]

            # Fallback to system resolver if DoH fails
            return socket.gethostbyname(hostname)
        except Exception:
            # Fallback to system resolver
            return socket.gethostbyname(hostname)


class DNSHTTPAdapter(requests.adapters.HTTPAdapter):
    """Custom HTTP adapter that uses Google DoH for resolution."""

    def resolve(self, hostname):
        """Resolve hostname using Google DoH."""
        return GoogleDoHResolver.resolve(hostname)

    def send(self, request, **kwargs):
        """Send request with custom DNS resolution."""
        # Extract hostname from URL
        parsed = urllib.parse.urlparse(request.url)
        hostname = parsed.hostname

        if hostname and hostname not in ["localhost", "127.0.0.1"]:
            try:
                ip = self.resolve(hostname)
                # Replace hostname with IP in URL but keep Host header
                new_url = request.url.replace(f"//{hostname}", f"//{ip}", 1)
                request.url = new_url
                # Ensure Host header is set to original hostname
                if "Host" not in request.headers:
                    request.headers["Host"] = hostname
            except Exception:
                # If resolution fails, let requests handle it
                pass

        return super().send(request, **kwargs)


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


class SerpAPINewsSearcher:
    """Search news using SerpAPI Google News API."""

    BASE_URL = "https://serpapi.com/search"

    def __init__(self, api_key: Optional[str] = None, delay: float = 1.0):
        """
        Initialize searcher.

        Args:
            api_key: SerpAPI key (or from SERPAPI_KEY env var)
            delay: Delay between requests in seconds
        """
        self.api_key = api_key or os.environ.get("SERPAPI_KEY")
        if not self.api_key:
            raise ValueError(
                "SerpAPI key required. Set SERPAPI_KEY env var or pass api_key parameter."
            )
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )

    def search(self, query: str, max_results: int = 20) -> List[NewsArticle]:
        """
        Search for news articles using Google News via SerpAPI.

        Args:
            query: Search query
            max_results: Maximum number of results to return

        Returns:
            List of NewsArticle objects
        """
        articles = []
        page = 0
        max_pages = (max_results // 10) + 1

        while len(articles) < max_results and page < max_pages:
            params = {
                "engine": "google_news",
                "q": query,
                "api_key": self.api_key,
                "num": min(10, max_results - len(articles)),
                "start": page * 10,
            }

            try:
                response = self.session.get(self.BASE_URL, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                # Parse news results
                news_results = data.get("news_results", [])
                for item in news_results:
                    article = NewsArticle(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        source=item.get("source", {}).get("name", "Unknown"),
                        snippet=item.get("snippet", ""),
                        published_at=item.get("date", None),
                    )
                    articles.append(article)

                    if len(articles) >= max_results:
                        break

                # Check if there are more results
                if not news_results:
                    break

                page += 1
                if page < max_pages and len(articles) < max_results:
                    time.sleep(self.delay)

            except requests.RequestException as e:
                print(f"Error searching news: {e}", file=sys.stderr)
                break
            except json.JSONDecodeError as e:
                print(f"Error parsing response: {e}", file=sys.stderr)
                break

        return articles[:max_results]


class SerperNewsSearcher:
    """Search news using Serper.dev Google News API."""

    BASE_URL = "https://google.serper.dev/news"

    def __init__(self, api_key: Optional[str] = None, delay: float = 1.0):
        """
        Initialize searcher.

        Args:
            api_key: Serper API key (or from SERPER_API_KEY env var)
            delay: Delay between requests in seconds
        """
        self.api_key = api_key or os.environ.get("SERPER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Serper API key required. Set SERPER_API_KEY env var or pass api_key parameter. Get key from https://serper.dev"
            )
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json",
            }
        )

    def search(
        self, query: str, max_results: int = 20, gl: str = "id", hl: str = "id"
    ) -> List[NewsArticle]:
        """
        Search for news articles using Google News via Serper.dev.

        Args:
            query: Search query
            max_results: Maximum number of results to return
            gl: Country code for search (default: 'id' for Indonesia)
            hl: Language code for search (default: 'id' for Indonesian)

        Returns:
            List of NewsArticle objects
        """
        articles = []

        try:
            payload = {
                "q": query,
                "gl": gl,
                "hl": hl,
            }

            response = self.session.post(self.BASE_URL, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Parse news results from Serper response
            # Serper returns results in 'news' array
            news_results = data.get("news", [])
            for item in news_results[:max_results]:
                article = NewsArticle(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    source=item.get("source", "Unknown"),
                    snippet=item.get("snippet", ""),
                    published_at=item.get("date", None),
                )
                articles.append(article)

            time.sleep(self.delay)

        except requests.RequestException as e:
            print(f"Error searching news: {e}", file=sys.stderr)
        except json.JSONDecodeError as e:
            print(f"Error parsing response: {e}", file=sys.stderr)

        return articles[:max_results]


class DuckDuckGoNewsSearcher:
    """Search news using DuckDuckGo HTML interface."""

    BASE_URL = "https://html.duckduckgo.com/html/"
    NEWS_URL = "https://duckduckgo.com/html/"

    def __init__(self, delay: float = 1.0, verify_ssl: bool = True):
        """
        Initialize searcher.

        Args:
            delay: Delay between requests in seconds (be polite)
            verify_ssl: Whether to verify SSL certificates (default: True)
                         Set to False if you get SSL certificate errors
        """
        self.delay = delay
        self.verify_ssl = verify_ssl
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
        # Mount custom DNS adapter for both HTTP and HTTPS
        self.session.mount("http://", DNSHTTPAdapter())
        self.session.mount("https://", DNSHTTPAdapter())

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
            response = self.session.get(
                self.BASE_URL, params=params, timeout=30, verify=self.verify_ssl
            )
            response.raise_for_status()
        except requests.exceptions.SSLError as e:
            print(f"SSL Error: {e}", file=sys.stderr)
            print(
                "If this is a certificate verification issue, try running with --no-verify-ssl",
                file=sys.stderr,
            )
            return articles
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
                response = self.session.get(
                    next_url, timeout=30, verify=self.verify_ssl
                )
                response.raise_for_status()
            except requests.exceptions.SSLError as e:
                print(f"SSL Error on pagination: {e}", file=sys.stderr)
                break
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


def search_news(
    topic: str,
    region: str,
    max_results: int = 20,
    provider: str = "duckduckgo",
    verify_ssl: bool = True,
) -> List[NewsArticle]:
    """
    Convenience function to search news.

    Args:
        topic: Topic to search for
        region: Geographic region
        max_results: Maximum results to return
        provider: News provider ('duckduckgo', 'serpapi', or 'serper')
        verify_ssl: Whether to verify SSL certificates (DuckDuckGo only)

    Returns:
        List of NewsArticle objects
    """
    query = f"{topic} {region}"

    if provider == "serpapi":
        searcher = SerpAPINewsSearcher(delay=1.0)
    elif provider == "serper":
        searcher = SerperNewsSearcher(delay=1.0)
    else:
        searcher = DuckDuckGoNewsSearcher(delay=1.0, verify_ssl=verify_ssl)

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
    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        help="Disable SSL certificate verification (use if you get SSL errors)",
    )
    parser.add_argument(
        "--provider",
        choices=["duckduckgo", "serpapi", "serper"],
        default="serper",
        help="News provider: serper (requires API key, default), serpapi (requires API key), or duckduckgo (free)",
    )

    args = parser.parse_args()

    print(f"Searching news for: {args.topic} in {args.region}")
    print(f"Provider: {args.provider}")
    print(f"Max results: {args.max_results}")

    # Search
    query = f"{args.topic} {args.region}"

    try:
        if args.provider == "duckduckgo":
            searcher = DuckDuckGoNewsSearcher(
                delay=args.delay, verify_ssl=not args.no_verify_ssl
            )
        elif args.provider == "serpapi":
            searcher = SerpAPINewsSearcher(delay=args.delay)
        else:
            # Default: serper
            searcher = SerperNewsSearcher(delay=args.delay)
        articles = searcher.search(query, args.max_results)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"Found {len(articles)} articles")

    # Prepare output
    output = {
        "query": query,
        "topic": args.topic,
        "region": args.region,
        "provider": args.provider,
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
