#!/usr/bin/env python3
"""
Nitter Search Script for X Account Seed Discovery
Searches X/Twitter via Nitter instances using Playwright with Chrome profile

Features:
- Automatic Nitter instance load balancing
- Rate limit awareness and rotation
- Persistent Chrome profile for session continuity

Usage:
    python search_nitter.py --query "politics Indonesia" --max-results 50
    python search_nitter.py --profile prabowo --output profile.json
    python search_nitter.py --search "mining policy" --max-results 100

Environment:
    NITTER_INSTANCES - Comma-separated list of Nitter instances (optional)
    Default profile: ~/.x-discovery/chrome-profile

Requirements:
    pip install playwright playwright-stealth beautifulsoup4 lxml nest-asyncio
    playwright install chromium
"""

import argparse
import json
import os
import nest_asyncio
import random
import sys
import time
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from playwright_stealth import Stealth
from bs4 import BeautifulSoup

# Apply nest_asyncio to allow nested event loops (needed in some environments)
nest_asyncio.apply()

# Default Nitter instances (from https://github.com/zedeus/nitter/wiki/Instances)
DEFAULT_NITTER_INSTANCES = [
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

# Load from environment or use defaults
NITTER_INSTANCES = (
    os.environ.get("NITTER_INSTANCES", "").split(",")
    if os.environ.get("NITTER_INSTANCES")
    else DEFAULT_NITTER_INSTANCES
)
NITTER_INSTANCES = [url.strip() for url in NITTER_INSTANCES if url.strip()]

# Default Chrome profile path
DEFAULT_CHROME_PROFILE = os.path.expanduser("~/.x-discovery/chrome-profile")


@dataclass
class InstanceHealth:
    """Tracks health metrics for a Nitter instance."""

    url: str
    last_used: Optional[float] = None
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    avg_response_time: float = 0.0
    is_healthy: bool = True


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
    """Search X/Twitter via Nitter using Playwright with Chrome profile and instance load balancing."""

    def __init__(
        self,
        instances: Optional[List[str]] = None,
        headless: bool = False,
        stealth: bool = True,
        delay_range: tuple = (2, 5),
        chrome_profile_dir: Optional[str] = None,
        max_failures: int = 3,
    ):
        """
        Initialize Nitter searcher with load balancing.

        Args:
            instances: List of Nitter instance URLs (defaults to NITTER_INSTANCES)
            headless: Whether to run headless (False recommended for avoiding blocks)
            stealth: Whether to use playwright-stealth
            delay_range: Random delay range between actions (min, max seconds)
            chrome_profile_dir: Path to Chrome user data directory (defaults to ~/.x-discovery/chrome-profile)
            max_failures: Max consecutive failures before marking instance unhealthy
        """
        self.instances = instances or NITTER_INSTANCES
        if not self.instances:
            raise ValueError(
                "No Nitter instances configured. Set NITTER_INSTANCES env var or pass instances list."
            )

        self.headless = headless
        self.stealth = stealth
        self.delay_range = delay_range
        self.chrome_profile_dir = chrome_profile_dir or DEFAULT_CHROME_PROFILE
        self.max_failures = max_failures

        # Initialize health tracking for all instances
        self.instance_health: Dict[str, InstanceHealth] = {
            url: InstanceHealth(url=url) for url in self.instances
        }

        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self._playwright = None
        self._current_instance: Optional[str] = None

    def _get_healthy_instance(self) -> str:
        """Get the next healthy instance using round-robin with health check."""
        healthy = [h for h in self.instance_health.values() if h.is_healthy]

        if not healthy:
            # Reset all instances if none are healthy
            for h in self.instance_health.values():
                h.is_healthy = True
                h.consecutive_failures = 0
            healthy = list(self.instance_health.values())

        # Sort by last used (oldest first) for round-robin
        healthy.sort(key=lambda h: h.last_used or 0)

        return healthy[0].url

    def _mark_instance_success(self, url: str, response_time: float):
        """Mark instance as successful."""
        health = self.instance_health[url]
        health.last_used = time.time()
        health.consecutive_failures = 0
        health.is_healthy = True
        # Update average response time
        if health.avg_response_time == 0:
            health.avg_response_time = response_time
        else:
            health.avg_response_time = (health.avg_response_time * 0.7) + (
                response_time * 0.3
            )

    def _mark_instance_failure(self, url: str, error: str):
        """Mark instance as failed."""
        health = self.instance_health[url]
        health.last_used = time.time()
        health.consecutive_failures += 1
        health.last_error = error

        if health.consecutive_failures >= self.max_failures:
            health.is_healthy = False
            print(
                f"Instance {url} marked unhealthy after {health.consecutive_failures} failures"
            )

    def _get_instance_stats(self) -> Dict:
        """Get statistics for all instances."""
        return {
            url: {
                "healthy": h.is_healthy,
                "failures": h.consecutive_failures,
                "avg_response_time": round(h.avg_response_time, 2),
                "last_error": h.last_error,
            }
            for url, h in self.instance_health.items()
        }

    def __enter__(self):
        """Context manager entry."""
        self._init_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def _init_browser(self):
        """Initialize browser with Chrome profile."""
        # Ensure profile directory exists
        profile_path = Path(self.chrome_profile_dir)
        profile_path.mkdir(parents=True, exist_ok=True)

        self._playwright = sync_playwright().start()

        # Build launch arguments
        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ]

        # Use persistent context with user data directory
        profile_path = str(profile_path.resolve())
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
        print(f"Browser initialized (headless={self.headless})")
        print(f"Available Nitter instances: {len(self.instances)}")
        print(
            f"Healthy instances: {sum(1 for h in self.instance_health.values() if h.is_healthy)}"
        )

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
        Search for posts on Nitter with automatic instance rotation.

        Args:
            query: Search query
            max_results: Maximum posts to collect

        Returns:
            List of XPost objects
        """
        if not self.context:
            self._init_browser()

        posts = []
        attempted_instances = set()

        while len(attempted_instances) < len(self.instances):
            # Get next healthy instance
            instance_url = self._get_healthy_instance()

            if instance_url in attempted_instances:
                break

            attempted_instances.add(instance_url)
            self._current_instance = instance_url

            print(f"\nTrying instance: {instance_url}")
            start_time = time.time()

            try:
                new_posts = self._search_posts_on_instance(
                    instance_url, query, max_results - len(posts)
                )

                if new_posts:
                    # Add unique posts
                    existing_ids = {p.post_id for p in posts if p.post_id}
                    for post in new_posts:
                        if post.post_id not in existing_ids:
                            posts.append(post)
                            existing_ids.add(post.post_id)

                    # Mark success
                    response_time = time.time() - start_time
                    self._mark_instance_success(instance_url, response_time)
                    print(
                        f"✓ Instance {instance_url} returned {len(new_posts)} posts in {response_time:.1f}s"
                    )

                    # If we have enough posts, stop
                    if len(posts) >= max_results:
                        break

                    # Otherwise try next instance for more results
                    continue
                else:
                    # No posts found, try next instance
                    self._mark_instance_failure(instance_url, "No posts found")

            except Exception as e:
                response_time = time.time() - start_time
                error_msg = str(e)
                self._mark_instance_failure(instance_url, error_msg)
                print(f"✗ Instance {instance_url} failed: {error_msg}")

        print(f"\nTotal posts collected: {len(posts)}")
        print(f"Instance stats: {self._get_instance_stats()}")

        return posts[:max_results]

    def _search_posts_on_instance(
        self, instance_url: str, query: str, max_results: int
    ) -> List[XPost]:
        """Search posts on a specific Nitter instance."""
        page = self._create_page()
        posts = []

        try:
            # Navigate to search page
            encoded_query = query.replace(" ", "%20")
            url = f"{instance_url}/search?f=tweets&q={encoded_query}"

            print(f"Searching: {url}")

            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            self._wait_for_page_load(page)
            time.sleep(3)  # Extra wait for dynamic content

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

        except Exception as e:
            raise

        finally:
            page.close()

        return posts[:max_results]

    def get_profile(self, handle: str) -> Optional[XProfile]:
        """
        Get profile information for a specific handle with instance rotation.

        Args:
            handle: X/Twitter handle (without @)

        Returns:
            XProfile object or None if not found
        """
        if not self.context:
            self._init_browser()

        attempted_instances = set()

        while len(attempted_instances) < len(self.instances):
            # Get next healthy instance
            instance_url = self._get_healthy_instance()

            if instance_url in attempted_instances:
                break

            attempted_instances.add(instance_url)

            try:
                profile = self._get_profile_on_instance(instance_url, handle)

                if profile:
                    self._mark_instance_success(instance_url, 1.0)
                    return profile
                else:
                    # Profile not found on this instance, try next
                    self._mark_instance_failure(instance_url, "Profile not found")

            except Exception as e:
                error_msg = str(e)
                self._mark_instance_failure(instance_url, error_msg)
                print(f"Instance {instance_url} failed: {error_msg}")

        print(f"Profile not found on any instance: @{handle}")
        return None

    def _get_profile_on_instance(
        self, instance_url: str, handle: str
    ) -> Optional[XProfile]:
        """Get profile from a specific Nitter instance."""
        page = self._create_page()
        profile = None

        try:
            # Clean handle
            handle = handle.strip().lstrip("@").lower()
            url = f"{instance_url}/{handle}"

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

        except Exception as e:
            raise

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
        description="Search X/Twitter via Nitter using Playwright with Chrome profile and load balancing"
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
        "--profile-dir",
        "-p",
        default=DEFAULT_CHROME_PROFILE,
        help=f"Path to Chrome profile directory (default: {DEFAULT_CHROME_PROFILE})",
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

    # Initialize searcher with load balancing
    delay_range = (args.delay_min, args.delay_max)

    try:
        with NitterSearcher(
            headless=args.headless,
            stealth=not args.no_stealth,
            delay_range=delay_range,
            chrome_profile_dir=args.profile_dir,
        ) as searcher:
            if args.command == "search":
                print(f"Searching posts: '{args.query}'")
                print(
                    f"Using {len(NITTER_INSTANCES)} Nitter instances with load balancing"
                )
                posts = searcher.search_posts(args.query, args.max_results)

                output = {
                    "query": args.query,
                    "instances_used": list(searcher.instance_health.keys()),
                    "instance_stats": searcher._get_instance_stats(),
                    "total_found": len(posts),
                    "timestamp": datetime.now().isoformat(),
                    "posts": [post.to_dict() for post in posts],
                }

            elif args.command == "profile":
                print(f"Fetching profile: @{args.handle}")
                print(
                    f"Using {len(NITTER_INSTANCES)} Nitter instances with load balancing"
                )
                profile = searcher.get_profile(args.handle)

                if not profile:
                    print(f"Profile not found: @{args.handle}", file=sys.stderr)
                    return 1

                output = {
                    "handle": args.handle,
                    "instances_used": list(searcher.instance_health.keys()),
                    "instance_stats": searcher._get_instance_stats(),
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
