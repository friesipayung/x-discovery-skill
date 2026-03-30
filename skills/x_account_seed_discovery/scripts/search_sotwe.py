#!/usr/bin/env python3
"""
Sotwe.com Search Script for X Account Seed Discovery
Searches X/Twitter profiles via sotwe.com proxy using Playwright with AdGuard (headful mode)

Usage:
    python search_sotwe.py --query "politics Indonesia" --max-results 50
    python search_sotwe.py --profile prabowo --output profile.json
    python search_sotwe.py --search "mining policy" --max-results 100 --adguard-path /path/to/adguard

Requirements:
    pip install playwright playwright-stealth beautifulsoup4 lxml
    playwright install chromium
"""

import argparse
import json
import random
import sys
import time
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from playwright_stealth import Stealth
from bs4 import BeautifulSoup


@dataclass
class XPost:
    """Represents an X/Twitter post from sotwe.com."""

    post_id: Optional[str]
    text: str
    created_at: Optional[str]
    likes: int
    retweets: int
    replies: int
    author_handle: str
    author_display_name: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class XProfile:
    """Represents an X/Twitter profile from sotwe.com."""

    handle: str
    display_name: str
    bio: str
    followers_count: int
    following_count: int
    posts_count: int
    location: str
    website: str
    joined_date: str
    is_verified: bool
    profile_image_url: Optional[str] = None
    banner_image_url: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class SotweSearcher:
    """Search X/Twitter via sotwe.com using Playwright with AdGuard."""

    BASE_URL = "https://www.sotwe.com"

    def __init__(
        self,
        adguard_path: Optional[str] = None,
        headless: bool = False,  # Headful required for extensions
        stealth: bool = True,
        delay_range: tuple = (2, 5),
    ):
        """
        Initialize sotwe searcher.

        Args:
            adguard_path: Path to AdGuard extension (folder or .crx file)
            headless: Whether to run headless (False required for extensions)
            stealth: Whether to use playwright-stealth
            delay_range: Random delay range between actions (min, max seconds)
        """
        self.adguard_path = adguard_path
        self.headless = headless
        self.stealth = stealth
        self.delay_range = delay_range
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self._playwright = None

    def __enter__(self):
        """Context manager entry."""
        self._init_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def _init_browser(self):
        """Initialize browser with AdGuard extension."""
        self._playwright = sync_playwright().start()

        # Build launch arguments
        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ]

        # Add AdGuard extension if provided
        if self.adguard_path and Path(self.adguard_path).exists():
            adguard_path = str(Path(self.adguard_path).resolve())
            args.extend(
                [
                    f"--disable-extensions-except={adguard_path}",
                    f"--load-extension={adguard_path}",
                ]
            )
            print(f"Loading AdGuard extension from: {adguard_path}")

        # Launch browser
        self.browser = self._playwright.chromium.launch(
            headless=self.headless, args=args
        )

        # Create context with realistic viewport and user agent
        self.context = self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/New_York",
        )

        print(f"Browser initialized (headless={self.headless})")

    def _random_delay(self):
        """Random delay to mimic human behavior."""
        delay = random.uniform(*self.delay_range)
        time.sleep(delay)

    def _create_page(self) -> Page:
        """Create a new page with stealth mode."""
        page = self.context.new_page()

        if self.stealth:
            stealth = Stealth()
            stealth.apply_stealth_sync(page)

        return page

    def search_posts(self, query: str, max_results: int = 50) -> List[XPost]:
        """
        Search for posts on sotwe.com.

        Args:
            query: Search query
            max_results: Maximum posts to collect

        Returns:
            List of XPost objects
        """
        if not self.browser:
            self._init_browser()

        page = self._create_page()
        posts = []

        try:
            # Navigate to search page
            encoded_query = query.replace(" ", "%20")
            url = f"{self.BASE_URL}/search/{encoded_query}"

            print(f"Searching: {url}")

            try:
                page.goto(url, wait_until="networkidle", timeout=60000)
            except Exception as e:
                if "ERR_CONNECTION_REFUSED" in str(e) or "ERR_NAME_NOT_RESOLVED" in str(
                    e
                ):
                    print(f"ERROR: Cannot connect to {self.BASE_URL}")
                    print("This may be due to:")
                    print("  - Geographic blocking")
                    print("  - Network restrictions")
                    print("  - The site being temporarily down")
                    print("\nAlternatives to try:")
                    print("  - Use a VPN or different network")
                    print("  - Try nitter.net or other X/Twitter viewers")
                    print("  - Use the official X API instead")
                    print("\nWaiting 10 seconds before closing browser...")
                    time.sleep(10)  # Wait so user can see the browser
                    return posts
                raise

            self._random_delay()

            # Scroll to load more content
            last_height = page.evaluate("document.body.scrollHeight")
            scroll_attempts = 0
            max_scroll_attempts = 10

            while len(posts) < max_results and scroll_attempts < max_scroll_attempts:
                # Parse current page content
                html = page.content()
                new_posts = self._parse_search_results(html)

                # Add new unique posts
                existing_ids = {p.post_id for p in posts if p.post_id}
                for post in new_posts:
                    if post.post_id not in existing_ids:
                        posts.append(post)
                        existing_ids.add(post.post_id)

                if len(posts) >= max_results:
                    break

                # Scroll down
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                self._random_delay()

                # Check if more content loaded
                new_height = page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    scroll_attempts += 1
                else:
                    scroll_attempts = 0
                    last_height = new_height

            print(f"Collected {len(posts)} posts")

        except Exception as e:
            print(f"Error searching posts: {e}", file=sys.stderr)

        finally:
            page.close()

        return posts[:max_results]

    def get_profile(self, handle: str) -> Optional[XProfile]:
        """
        Get profile information for a specific handle.

        Args:
            handle: X/Twitter handle (without @)

        Returns:
            XProfile object or None if not found
        """
        if not self.browser:
            self._init_browser()

        page = self._create_page()
        profile = None

        try:
            # Clean handle
            handle = handle.strip().lstrip("@").lower()
            url = f"{self.BASE_URL}/{handle}"

            print(f"Fetching profile: {url}")
            page.goto(url, wait_until="networkidle", timeout=60000)
            self._random_delay()

            # Parse profile
            html = page.content()
            profile = self._parse_profile(html, handle)

            if profile:
                print(f"Found profile: @{profile.handle} ({profile.display_name})")
            else:
                print(f"Profile not found: @{handle}")

        except Exception as e:
            print(f"Error fetching profile: {e}", file=sys.stderr)

        finally:
            page.close()

        return profile

    def _parse_search_results(self, html: str) -> List[XPost]:
        """Parse search results from HTML."""
        soup = BeautifulSoup(html, "lxml")
        posts = []

        # Find all tweet cards
        tweet_cards = soup.find_all("div", class_="tweet-card") or soup.find_all(
            "article"
        )

        for card in tweet_cards:
            try:
                # Extract author info
                author_elem = card.find("a", href=re.compile(r"^/[^/]+$"))
                if not author_elem:
                    continue

                author_handle = author_elem.get("href", "").strip("/")
                author_name_elem = card.find("span", class_="name") or card.find(
                    "div", class_="user-name"
                )
                author_display_name = (
                    author_name_elem.get_text(strip=True)
                    if author_name_elem
                    else author_handle
                )

                # Extract tweet text
                text_elem = card.find("div", class_="tweet-text") or card.find(
                    "div", {"data-testid": "tweetText"}
                )
                text = text_elem.get_text(strip=True) if text_elem else ""

                # Extract engagement metrics
                likes = self._extract_number(card, ["likes", "like-count", "favorite"])
                retweets = self._extract_number(card, ["retweets", "retweet-count"])
                replies = self._extract_number(card, ["replies", "reply-count"])

                # Extract timestamp
                time_elem = card.find("time") or card.find("span", class_="time")
                created_at = (
                    time_elem.get("datetime")
                    if time_elem and time_elem.get("datetime")
                    else None
                )

                # Extract post ID from URL if available
                post_id = None
                link_elem = card.find("a", href=re.compile(r"/status/\d+"))
                if link_elem:
                    match = re.search(r"/status/(\d+)", link_elem.get("href", ""))
                    if match:
                        post_id = match.group(1)

                post = XPost(
                    post_id=post_id,
                    text=text,
                    created_at=created_at,
                    likes=likes,
                    retweets=retweets,
                    replies=replies,
                    author_handle=author_handle,
                    author_display_name=author_display_name,
                )
                posts.append(post)

            except Exception as e:
                continue

        return posts

    def _parse_profile(self, html: str, handle: str) -> Optional[XProfile]:
        """Parse profile page HTML."""
        soup = BeautifulSoup(html, "lxml")

        try:
            # Check if profile exists
            error_elem = soup.find(
                "div", string=re.compile(r"not found|does not exist", re.I)
            )
            if error_elem:
                return None

            # Extract display name
            name_elem = soup.find("h1", class_="profile-name") or soup.find(
                "div", class_="user-name"
            )
            display_name = name_elem.get_text(strip=True) if name_elem else handle

            # Extract bio
            bio_elem = soup.find("div", class_="profile-bio") or soup.find(
                "div", {"data-testid": "UserDescription"}
            )
            bio = bio_elem.get_text(strip=True) if bio_elem else ""

            # Extract stats
            followers = self._extract_stat(soup, ["followers", "Followers"])
            following = self._extract_stat(soup, ["following", "Following"])
            posts = self._extract_stat(soup, ["posts", "tweets", "Posts", "Tweets"])

            # Extract location
            location_elem = soup.find("span", class_="location") or soup.find(
                "div", {"data-testid": "UserLocation"}
            )
            location = location_elem.get_text(strip=True) if location_elem else ""

            # Extract website
            website_elem = soup.find("a", class_="website") or soup.find(
                "a", {"data-testid": "UserUrl"}
            )
            website = website_elem.get("href", "") if website_elem else ""

            # Extract joined date
            joined_elem = soup.find("span", class_="joined") or soup.find(
                "div", {"data-testid": "UserJoinDate"}
            )
            joined_date = joined_elem.get_text(strip=True) if joined_elem else ""

            # Check verification
            verified_elem = soup.find(
                "svg", class_=re.compile(r"verified", re.I)
            ) or soup.find("span", class_=re.compile(r"verified", re.I))
            is_verified = verified_elem is not None

            # Extract images
            profile_img = None
            banner_img = None

            img_elem = soup.find("img", class_=re.compile(r"profile.*photo", re.I))
            if img_elem:
                profile_img = img_elem.get("src")

            banner_elem = soup.find("div", class_=re.compile(r"banner|header", re.I))
            if banner_elem:
                style = banner_elem.get("style", "")
                match = re.search(r'url\(["\']?([^"\')]+)', style)
                if match:
                    banner_img = match.group(1)

            return XProfile(
                handle=handle,
                display_name=display_name,
                bio=bio,
                followers_count=followers,
                following_count=following,
                posts_count=posts,
                location=location,
                website=website,
                joined_date=joined_date,
                is_verified=is_verified,
                profile_image_url=profile_img,
                banner_image_url=banner_img,
            )

        except Exception as e:
            print(f"Error parsing profile: {e}", file=sys.stderr)
            return None

    def _extract_number(self, element, class_names: List[str]) -> int:
        """Extract number from element by class names."""
        for class_name in class_names:
            elem = element.find(class_=re.compile(class_name, re.I))
            if elem:
                text = elem.get_text(strip=True)
                # Parse numbers like "1.2K", "3M", "1,234"
                match = re.search(r"([\d.,]+)\s*([KMB]?)", text, re.I)
                if match:
                    num = float(match.group(1).replace(",", ""))
                    suffix = match.group(2).upper()
                    if suffix == "K":
                        num *= 1000
                    elif suffix == "M":
                        num *= 1000000
                    elif suffix == "B":
                        num *= 1000000000
                    return int(num)
        return 0

    def _extract_stat(self, soup, keywords: List[str]) -> int:
        """Extract stat number from profile page."""
        for keyword in keywords:
            # Try different selectors
            selectors = [
                f'div:contains("{keyword}")',
                f'span:contains("{keyword}")',
                f'a:contains("{keyword}")',
            ]

            for selector in selectors:
                try:
                    elems = soup.find_all(string=re.compile(keyword, re.I))
                    for elem in elems:
                        parent = elem.parent
                        if parent:
                            # Look for number in parent or sibling
                            text = parent.get_text()
                            match = re.search(r"([\d.,]+)\s*([KMB]?)", text, re.I)
                            if match:
                                num = float(match.group(1).replace(",", ""))
                                suffix = match.group(2).upper()
                                if suffix == "K":
                                    num *= 1000
                                elif suffix == "M":
                                    num *= 1000000
                                elif suffix == "B":
                                    num *= 1000000000
                                return int(num)
                except:
                    continue

        return 0

    def close(self):
        """Close browser and cleanup."""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self._playwright:
            self._playwright.stop()
        print("Browser closed")


def main():
    parser = argparse.ArgumentParser(
        description="Search X/Twitter via sotwe.com using Playwright with AdGuard"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for posts")
    search_parser.add_argument("--query", "-q", required=True, help="Search query")
    search_parser.add_argument(
        "--max-results", "-n", type=int, default=50, help="Max posts to collect"
    )
    search_parser.add_argument("--output", "-o", help="Output JSON file")

    # Profile command
    profile_parser = subparsers.add_parser("profile", help="Get profile info")
    profile_parser.add_argument("handle", help="X/Twitter handle (without @)")
    profile_parser.add_argument("--output", "-o", help="Output JSON file")

    # Common options
    parser.add_argument("--adguard-path", help="Path to AdGuard extension")
    parser.add_argument(
        "--headless", action="store_true", help="Run headless (no extension support)"
    )
    parser.add_argument(
        "--no-stealth", action="store_true", help="Disable stealth mode"
    )
    parser.add_argument(
        "--delay-min", type=float, default=2.0, help="Min delay between actions"
    )
    parser.add_argument(
        "--delay-max", type=float, default=5.0, help="Max delay between actions"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Initialize searcher
    delay_range = (args.delay_min, args.delay_max)

    try:
        with SotweSearcher(
            adguard_path=args.adguard_path,
            headless=args.headless,
            stealth=not args.no_stealth,
            delay_range=delay_range,
        ) as searcher:
            if args.command == "search":
                print(f"Searching posts: '{args.query}'")
                posts = searcher.search_posts(args.query, args.max_results)

                output = {
                    "query": args.query,
                    "total_found": len(posts),
                    "timestamp": datetime.now().isoformat(),
                    "posts": [post.to_dict() for post in posts],
                }

            elif args.command == "profile":
                print(f"Fetching profile: @{args.handle}")
                profile = searcher.get_profile(args.handle)

                if not profile:
                    print(f"Profile not found: @{args.handle}", file=sys.stderr)
                    return 1

                output = {
                    "handle": args.handle,
                    "timestamp": datetime.now().isoformat(),
                    "profile": profile.to_dict(),
                }

            # Output results
            json_output = json.dumps(output, indent=2, ensure_ascii=False)

            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(json_output)
                print(f"Results saved to: {args.output}")
            else:
                print(json_output)

            return 0

    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    import re  # Import here for the module

    sys.exit(main())
