#!/usr/bin/env python3
"""
TwStalker Search Script for X Account Seed Discovery
Alternative X/Twitter viewer - not a Nitter instance

Features:
- Profile viewing and search via TwStalker
- Different architecture than Nitter (often more reliable)
- No API key required for public profiles

Usage:
    # Search profiles
    python search_twstalker.py search --query "makan bergizi gratis" --max-results 50

    # Get profile info
    python search_twstalker.py profile jokowi --output profile.json

Requirements:
    pip install playwright playwright-stealth beautifulsoup4 lxml
    playwright install chromium
"""

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, Page
from playwright_stealth import stealth_sync
from bs4 import BeautifulSoup


@dataclass
class XPost:
    """Represents an X/Twitter post from TwStalker."""

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
    """Represents an X/Twitter profile from TwStalker."""

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

    def to_dict(self) -> dict:
        return asdict(self)


class TwStalkerSearcher:
    """Search X/Twitter via TwStalker using Playwright."""

    BASE_URL = "https://w.twstalker.com"

    def __init__(self, headless: bool = False, delay_range: tuple = (2, 5)):
        self.headless = headless
        self.delay_range = delay_range
        self._playwright = None
        self.context = None

    def __enter__(self):
        self._init_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _init_browser(self):
        """Initialize browser."""
        self._playwright = sync_playwright().start()

        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-web-security",
        ]

        self.context = self._playwright.chromium.launch_persistent_context(
            user_data_dir="",
            headless=self.headless,
            args=args,
            viewport={"width": 1920, "height": 1080},
        )
        print(f"Browser initialized (headless={self.headless})")

    def _create_page(self) -> Page:
        """Create a new page with stealth mode."""
        page = self.context.new_page()
        stealth_sync(page)
        return page

    def _random_delay(self):
        """Random delay to mimic human behavior."""
        import random

        delay = random.uniform(*self.delay_range)
        time.sleep(delay)

    def search_profiles(self, query: str, max_results: int = 50) -> List[XProfile]:
        """
        Search for profiles on TwStalker.

        TwStalker search URL pattern: https://w.twstalker.com/search/?q={query}
        """
        if not self.context:
            self._init_browser()

        page = self._create_page()
        profiles = []

        try:
            # Navigate to search page
            encoded_query = query.replace(" ", "+")
            url = f"{self.BASE_URL}/search/?q={encoded_query}"

            print(f"Searching TwStalker: {url}")

            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            time.sleep(3)
            self._random_delay()

            # Parse results
            html = page.content()
            profiles = self._parse_search_results(html, max_results)

        except Exception as e:
            print(f"Error searching: {e}", file=sys.stderr)

        finally:
            page.close()

        print(f"Found {len(profiles)} profiles")
        return profiles[:max_results]

    def _parse_search_results(self, html: str, max_results: int) -> List[XProfile]:
        """Parse search results from TwStalker HTML."""
        soup = BeautifulSoup(html, "lxml")
        profiles = []

        # TwStalker profile cards - adjust selectors based on actual HTML structure
        # Common patterns for X profile viewers:
        profile_cards = soup.find_all(
            "div", class_=re.compile("profile|user|account", re.I)
        )

        for card in profile_cards[:max_results]:
            try:
                # Extract handle
                handle_elem = card.find("a", href=re.compile(r"^/[^/]+$"))
                if not handle_elem:
                    continue

                handle = handle_elem.get("href", "").strip("/")
                if not handle or handle in ["search", "about", "privacy"]:
                    continue

                # Extract display name
                name_elem = card.find(
                    ["h3", "h4", "span", "div"], class_=re.compile("name|title", re.I)
                )
                display_name = name_elem.get_text(strip=True) if name_elem else handle

                # Extract bio
                bio_elem = card.find("div", class_=re.compile("bio|description", re.I))
                bio = bio_elem.get_text(strip=True) if bio_elem else ""

                # Extract stats (followers, following, posts)
                followers = 0
                following = 0
                posts = 0

                stats_elems = card.find_all(
                    text=re.compile(r"(followers|following|tweets|posts)", re.I)
                )
                for stat_text in stats_elems:
                    parent = stat_text.parent
                    if parent:
                        number_match = re.search(
                            r"([\d.,]+)\s*(K|M|B)?", parent.get_text()
                        )
                        if number_match:
                            num = float(number_match.group(1).replace(",", ""))
                            suffix = number_match.group(2)
                            if suffix == "K":
                                num *= 1000
                            elif suffix == "M":
                                num *= 1000000
                            elif suffix == "B":
                                num *= 1000000000

                            if "follower" in stat_text.lower():
                                followers = int(num)
                            elif "following" in stat_text.lower():
                                following = int(num)
                            elif (
                                "tweet" in stat_text.lower()
                                or "post" in stat_text.lower()
                            ):
                                posts = int(num)

                profile = XProfile(
                    handle=handle,
                    display_name=display_name,
                    bio=bio,
                    followers_count=followers,
                    following_count=following,
                    posts_count=posts,
                    location="",
                    website="",
                    joined_date="",
                    is_verified=False,
                )
                profiles.append(profile)

            except Exception as e:
                continue

        return profiles

    def get_profile(self, handle: str) -> Optional[XProfile]:
        """Get detailed profile information."""
        if not self.context:
            self._init_browser()

        page = self._create_page()
        profile = None

        try:
            handle = handle.strip().lstrip("@").lower()
            url = f"{self.BASE_URL}/{handle}"

            print(f"Fetching profile: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            time.sleep(3)
            self._random_delay()

            html = page.content()
            profile = self._parse_profile(html, handle)

            if profile:
                print(f"Found profile: @{profile.handle}")

        except Exception as e:
            print(f"Error fetching profile: {e}", file=sys.stderr)

        finally:
            page.close()

        return profile

    def _parse_profile(self, html: str, handle: str) -> Optional[XProfile]:
        """Parse profile page HTML from TwStalker."""
        soup = BeautifulSoup(html, "lxml")

        try:
            # Check if profile exists (error page indicators)
            error_elem = soup.find(
                text=re.compile(r"(not found|error|doesn't exist)", re.I)
            )
            if error_elem:
                return None

            # Extract profile info - adjust selectors based on actual TwStalker HTML
            # These are common patterns for X profile pages:

            name_elem = soup.find("h1") or soup.find("h2") or soup.find("title")
            display_name = name_elem.get_text(strip=True) if name_elem else handle

            bio_elem = soup.find(
                "div", class_=re.compile("bio|description|about", re.I)
            )
            bio = bio_elem.get_text(strip=True) if bio_elem else ""

            # Extract stats
            followers = 0
            following = 0
            posts = 0

            # Look for stat elements
            stat_patterns = [
                (r"followers", "followers"),
                (r"following", "following"),
                (r"tweets|posts", "posts"),
            ]

            for pattern, stat_type in stat_patterns:
                stat_elem = soup.find(text=re.compile(pattern, re.I))
                if stat_elem:
                    parent = stat_elem.parent
                    if parent:
                        number_match = re.search(
                            r"([\d.,]+)\s*(K|M|B)?", parent.get_text()
                        )
                        if number_match:
                            num = float(number_match.group(1).replace(",", ""))
                            suffix = number_match.group(2)
                            if suffix == "K":
                                num *= 1000
                            elif suffix == "M":
                                num *= 1000000
                            elif suffix == "B":
                                num *= 1000000000

                            if stat_type == "followers":
                                followers = int(num)
                            elif stat_type == "following":
                                following = int(num)
                            elif stat_type == "posts":
                                posts = int(num)

            return XProfile(
                handle=handle,
                display_name=display_name,
                bio=bio,
                followers_count=followers,
                following_count=following,
                posts_count=posts,
                location="",
                website="",
                joined_date="",
                is_verified=False,
            )

        except Exception as e:
            print(f"Error parsing profile: {e}", file=sys.stderr)
            return None

    def close(self):
        """Close browser and cleanup."""
        if self.context:
            self.context.close()
        if self._playwright:
            self._playwright.stop()
        print("Browser closed")


def main():
    parser = argparse.ArgumentParser(
        description="Search X/Twitter via TwStalker using Playwright"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for profiles")
    search_parser.add_argument("--query", "-q", required=True, help="Search query")
    search_parser.add_argument(
        "--max-results", "-n", type=int, default=50, help="Max profiles to collect"
    )
    search_parser.add_argument("--output", "-o", help="Output JSON file")

    # Profile command
    profile_parser = subparsers.add_parser("profile", help="Get profile info")
    profile_parser.add_argument("handle", help="X/Twitter handle (without @)")
    profile_parser.add_argument("--output", "-o", help="Output JSON file")

    # Common options
    parser.add_argument(
        "--headless", action="store_true", help="Run headless (not recommended)"
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

    delay_range = (args.delay_min, args.delay_max)

    try:
        with TwStalkerSearcher(
            headless=args.headless, delay_range=delay_range
        ) as searcher:
            if args.command == "search":
                print(f"Searching profiles: '{args.query}'")
                profiles = searcher.search_profiles(args.query, args.max_results)

                output = {
                    "query": args.query,
                    "total_found": len(profiles),
                    "timestamp": datetime.now().isoformat(),
                    "profiles": [profile.to_dict() for profile in profiles],
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
    sys.exit(main())
