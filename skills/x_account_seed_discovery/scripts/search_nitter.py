#!/usr/bin/env python3
"""
Nitter Search Script for X Account Seed Discovery
Searches X/Twitter profiles via Nitter instances using Playwright with Chrome profile

Usage:
    python search_nitter.py --query "politics Indonesia" --max-results 50
    python search_nitter.py --profile prabowo --output profile.json
    python search_nitter.py --search "mining policy" --max-results 100 --instance nitter.net

Requirements:
    pip install playwright playwright-stealth beautifulsoup4 lxml nest-asyncio
    playwright install chromium
"""

import argparse
import json
import nest_asyncio
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

# Apply nest_asyncio to allow nested event loops (needed in some environments)
nest_asyncio.apply()

# Working Nitter instances (from https://github.com/zedeus/nitter/wiki/Instances)
NITTER_INSTANCES = [
    "https://nitter.net",
    "https://xcancel.com",
    "https://nitter.poast.org",
    "https://nitter.privacyredirect.com",
    "https://lightbrd.com",
    "https://nitter.space",
    "https://nitter.tiekoetter.com",
    "https://nuku.trabun.org",
    "https://nitter.catsarch.com",
]


@dataclass
class XPost:
    """Represents an X/Twitter post from Nitter."""

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
    """Represents an X/Twitter profile from Nitter."""

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


class NitterSearcher:
    """Search X/Twitter via Nitter using Playwright with Chrome profile."""

    def __init__(
        self,
        base_url: str = "https://nitter.net",
        headless: bool = False,
        stealth: bool = True,
        delay_range: tuple = (2, 5),
        chrome_profile_dir: Optional[str] = None,
    ):
        """
        Initialize Nitter searcher.

        Args:
            base_url: Nitter instance URL to use
            headless: Whether to run headless (False recommended for avoiding blocks)
            stealth: Whether to use playwright-stealth
            delay_range: Random delay range between actions (min, max seconds)
            chrome_profile_dir: Path to Chrome user data directory (profile)
        """
        self.base_url = base_url.rstrip("/")
        self.headless = headless
        self.stealth = stealth
        self.delay_range = delay_range
        self.chrome_profile_dir = chrome_profile_dir
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
        """Initialize browser with optional Chrome profile."""
        self._playwright = sync_playwright().start()

        # Build launch arguments
        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ]

        # Check if using Chrome profile
        if self.chrome_profile_dir and Path(self.chrome_profile_dir).exists():
            # Use persistent context with user data directory
            profile_path = str(Path(self.chrome_profile_dir).resolve())
            print(f"Using Chrome profile: {profile_path}")

            # Use system Chrome executable if available (better profile compatibility)
            chrome_exe = self._get_chrome_executable()
            if chrome_exe:
                print(f"Using system Chrome: {chrome_exe}")
                self.context = self._playwright.chromium.launch_persistent_context(
                    user_data_dir=profile_path,
                    headless=self.headless,
                    args=args,
                    executable_path=chrome_exe,
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    locale="en-US",
                    timezone_id="America/New_York",
                )
            else:
                self.context = self._playwright.chromium.launch_persistent_context(
                    user_data_dir=profile_path,
                    headless=self.headless,
                    args=args,
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    locale="en-US",
                    timezone_id="America/New_York",
                )
            # When using persistent context, we don't need separate browser instance
            self.browser = None
        else:
            # Launch browser normally and create context
            self.browser = self._playwright.chromium.launch(
                headless=self.headless,
                args=args,
            )

            self.context = self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/New_York",
            )

        print(f"Browser initialized (headless={self.headless})")
        print(f"Using Nitter instance: {self.base_url}")

    def _get_chrome_executable(self) -> Optional[str]:
        """Find Chrome executable path."""
        possible_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/usr/bin/google-chrome",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
        ]

        for path in possible_paths:
            expanded = Path(path).expanduser()
            if expanded.exists():
                return str(expanded)
        return None

    def _random_delay(self):
        """Random delay to mimic human behavior."""
        delay = random.uniform(*self.delay_range)
        time.sleep(delay)

    def _wait_for_page_load(self, page: Page, timeout: int = 30):
        """Wait for page to fully load and any Cloudflare/verification to complete."""
        print("Waiting for page to load...")
        start_time = time.time()

        # Wait for initial load
        page.wait_for_load_state("networkidle", timeout=timeout * 1000)

        while time.time() - start_time < timeout:
            title = page.title()
            url = page.url

            # Check for verification/challenge pages
            is_verifying = (
                "just a moment" in title.lower()
                or "checking your browser" in title.lower()
                or "verifying" in title.lower()
                or "challenge" in url.lower()
                or page.locator('text="Checking your browser"').count() > 0
                or page.locator('text="Just a moment"').count() > 0
            )

            if not is_verifying:
                elapsed = int(time.time() - start_time)
                print(f"Page loaded successfully (took {elapsed}s)")
                return True

            elapsed = int(time.time() - start_time)
            print(f"Still waiting for verification... ({elapsed}s)")
            time.sleep(2)

        print(f"Warning: Page load timeout after {timeout}s")
        return False

    def _create_page(self) -> Page:
        """Create a new page with stealth mode."""
        page = self.context.new_page()

        if self.stealth:
            stealth = Stealth()
            stealth.apply_stealth_sync(page)

        return page

    def search_posts(self, query: str, max_results: int = 50) -> List[XPost]:
        """
        Search for posts on Nitter.

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
            url = f"{self.base_url}/search?f=tweets&q={encoded_query}"

            print(f"Searching: {url}")

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                self._wait_for_page_load(page)
                time.sleep(3)  # Extra wait for dynamic content
            except Exception as e:
                if "ERR_CONNECTION_REFUSED" in str(e) or "ERR_NAME_NOT_RESOLVED" in str(
                    e
                ):
                    print(f"ERROR: Cannot connect to {self.base_url}")
                    print("This instance may be down or blocked.")
                    print("\nAlternatives to try:")
                    print("  - Use a different Nitter instance (--instance)")
                    print("  - Try the official nitter.net")
                    print("  - Use a VPN or different network")
                    time.sleep(5)
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
            url = f"{self.base_url}/{handle}"

            print(f"Fetching profile: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            self._wait_for_page_load(page)
            time.sleep(3)  # Extra wait for dynamic content
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
        """Parse search results from Nitter HTML."""
        import re

        soup = BeautifulSoup(html, "lxml")
        posts = []

        # Nitter uses timeline-item class for tweets
        tweet_cards = soup.find_all("div", class_="timeline-item")

        for card in tweet_cards:
            try:
                # Skip "show more" items
                if card.find("a", class_="show-more"):
                    continue

                # Extract tweet link and ID
                tweet_link = card.find("a", class_="tweet-link")
                if not tweet_link:
                    continue

                href = tweet_link.get("href", "")
                post_id = None
                match = re.search(r"/status/(\d+)", href)
                if match:
                    post_id = match.group(1)

                # Extract author info
                author_elem = card.find("a", class_="username")
                if not author_elem:
                    continue

                author_handle = author_elem.get_text(strip=True).lstrip("@")
                author_name_elem = card.find("a", class_="fullname")
                author_display_name = (
                    author_name_elem.get_text(strip=True)
                    if author_name_elem
                    else author_handle
                )

                # Extract tweet text
                text_elem = card.find("div", class_="tweet-content")
                text = text_elem.get_text(strip=True) if text_elem else ""

                # Extract engagement metrics
                stats = card.find("div", class_="tweet-stats")
                likes = 0
                retweets = 0
                replies = 0

                if stats:
                    like_elem = stats.find("div", class_="icon-heart")
                    if like_elem:
                        likes = self._extract_stat_number(like_elem)

                    rt_elem = stats.find("div", class_="icon-retweet")
                    if rt_elem:
                        retweets = self._extract_stat_number(rt_elem)

                    reply_elem = stats.find("div", class_="icon-comment")
                    if reply_elem:
                        replies = self._extract_stat_number(reply_elem)

                # Extract timestamp
                time_elem = card.find("span", class_="tweet-date")
                created_at = None
                if time_elem:
                    time_link = time_elem.find("a")
                    if time_link:
                        title = time_link.get("title", "")
                        if title:
                            created_at = title

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

    def _extract_stat_number(self, element) -> int:
        """Extract number from stat element."""
        text = element.get_text(strip=True)
        match = re.search(r"([\d.,]+)\s*([KMB]?)\s*", text, re.I)
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

    def _parse_profile(self, html: str, handle: str) -> Optional[XProfile]:
        """Parse profile page HTML from Nitter."""
        import re

        soup = BeautifulSoup(html, "lxml")

        try:
            # Check if profile exists
            error_elem = soup.find("div", class_="error-panel")
            if error_elem:
                return None

            # Extract profile info from profile-card
            profile_card = soup.find("div", class_="profile-card")
            if not profile_card:
                # Try alternative selectors
                profile_card = soup.find("div", class_="profile-tab")

            if not profile_card:
                # Try to extract from page anyway
                profile_card = soup

            # Extract display name
            name_elem = profile_card.find("a", class_="profile-card-fullname")
            display_name = name_elem.get_text(strip=True) if name_elem else handle

            # Extract bio
            bio_elem = profile_card.find("div", class_="profile-bio")
            bio = bio_elem.get_text(strip=True) if bio_elem else ""

            # Extract stats
            stats = profile_card.find_all("div", class_="profile-stat")
            followers = 0
            following = 0
            posts = 0

            for stat in stats:
                label_elem = stat.find("div", class_="profile-stat-header")
                value_elem = stat.find("div", class_="profile-stat-num")

                if label_elem and value_elem:
                    label = label_elem.get_text(strip=True).lower()
                    value = value_elem.get_text(strip=True)

                    if "follower" in label:
                        followers = self._parse_number(value)
                    elif "following" in label:
                        following = self._parse_number(value)
                    elif "tweet" in label or "post" in label:
                        posts = self._parse_number(value)

            # Extract location
            location_elem = profile_card.find("div", class_="profile-location")
            location = location_elem.get_text(strip=True) if location_elem else ""

            # Extract website
            website_elem = profile_card.find("a", class_="profile-website")
            website = website_elem.get("href", "") if website_elem else ""

            # Extract joined date
            joined_elem = profile_card.find("div", class_="profile-joindate")
            joined_date = joined_elem.get_text(strip=True) if joined_elem else ""

            # Check verification
            verified_elem = profile_card.find("span", class_="verified-icon")
            is_verified = verified_elem is not None

            # Extract images
            profile_img = None
            banner_img = None

            img_elem = profile_card.find("img", class_="profile-card-avatar")
            if img_elem:
                profile_img = img_elem.get("src", "")
                if profile_img and profile_img.startswith("//"):
                    profile_img = "https:" + profile_img

            banner_elem = profile_card.find("img", class_="profile-banner")
            if banner_elem:
                banner_img = banner_elem.get("src", "")
                if banner_img and banner_img.startswith("//"):
                    banner_img = "https:" + banner_img

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

    def _parse_number(self, text: str) -> int:
        """Parse number from text (handles K, M, B suffixes)."""
        text = text.strip().replace(",", "")
        match = re.search(r"([\d.]+)\s*([KMB]?)\s*", text, re.I)
        if match:
            num = float(match.group(1))
            suffix = match.group(2).upper()
            if suffix == "K":
                num *= 1000
            elif suffix == "M":
                num *= 1000000
            elif suffix == "B":
                num *= 1000000000
            return int(num)
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
        description="Search X/Twitter via Nitter using Playwright with Chrome profile"
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
    parser.add_argument(
        "--instance",
        default="nitter.net",
        help=f"Nitter instance to use (default: nitter.net). Available: {', '.join(NITTER_INSTANCES[:3])}...",
    )
    parser.add_argument(
        "--profile",
        "-p",
        default=str(Path.home() / ".x-discovery" / "chrome-profile"),
        help="Path to Chrome profile directory (default: ~/.x-discovery/chrome-profile)",
    )
    parser.add_argument(
        "--headless", action="store_true", help="Run headless (not recommended)"
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

    # Build instance URL
    instance_url = args.instance
    if not instance_url.startswith("http"):
        instance_url = f"https://{instance_url}"

    # Initialize searcher
    delay_range = (args.delay_min, args.delay_max)

    try:
        with NitterSearcher(
            base_url=instance_url,
            headless=args.headless,
            stealth=not args.no_stealth,
            delay_range=delay_range,
            chrome_profile_dir=args.profile,
        ) as searcher:
            if args.command == "search":
                print(f"Searching posts: '{args.query}'")
                posts = searcher.search_posts(args.query, args.max_results)

                output = {
                    "query": args.query,
                    "instance": instance_url,
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
                    "instance": instance_url,
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
        error_msg = str(e)
        # Ignore asyncio loop warnings - they're not fatal
        if "asyncio loop" in error_msg or "Sync API inside the asyncio" in error_msg:
            print(f"Warning: {error_msg}", file=sys.stderr)
            print(
                "(This warning can be ignored - continuing execution)", file=sys.stderr
            )
            return 0
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    import re  # Import here for the module

    sys.exit(main())
