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
    """Search X/Twitter via TwStalker using Playwright with rate limit respect."""

    BASE_URL = "https://w.twstalker.com"
    MIN_REQUEST_INTERVAL = 5.0  # Minimum seconds between requests
    MAX_RETRIES = 3
    BACKOFF_BASE = 2.0  # Base for exponential backoff

    def __init__(
        self,
        headless: bool = False,
        delay_range: tuple = (3, 7),
        enrich_profiles: bool = True,
    ):
        self.headless = headless
        self.delay_range = delay_range
        self.enrich_profiles = enrich_profiles
        self._playwright = None
        self.context = None
        self._last_request_time = None
        self._request_count = 0
        self._rate_limit_hits = 0

    def __enter__(self):
        self._init_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _init_browser(self):
        """Initialize browser with proper profile directory."""
        import tempfile

        self._playwright = sync_playwright().start()

        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-web-security",
        ]

        # Use a proper temp directory for persistent context
        profile_dir = tempfile.mkdtemp(prefix="twstalker_profile_")

        self.context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=self.headless,
            args=args,
            viewport={"width": 1920, "height": 1080},
        )
        print(f"Browser initialized (headless={self.headless}, profile={profile_dir})")

    def _create_page(self) -> Page:
        """Create a new page with stealth mode."""
        page = self.context.new_page()
        stealth_sync(page)
        return page

    def _random_delay(self):
        """Random delay with jitter to mimic human behavior and avoid patterns."""
        import random

        delay = random.uniform(*self.delay_range)
        # Add jitter (±20% variation)
        jitter = delay * random.uniform(-0.2, 0.2)
        total_delay = delay + jitter
        time.sleep(max(0.5, total_delay))

    def _enforce_rate_limit(self):
        """Enforce minimum time between requests to respect rate limits."""
        if self._last_request_time is not None:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.MIN_REQUEST_INTERVAL:
                wait_time = self.MIN_REQUEST_INTERVAL - elapsed
                print(f"  [Rate limit] Waiting {wait_time:.1f}s before next request...")
                time.sleep(wait_time)
        self._last_request_time = time.time()
        self._request_count += 1

    def _handle_rate_limit_response(self, page) -> bool:
        """
        Check if page shows rate limit/blocking indicators.
        Returns True if rate limited, False if OK.
        """
        html = page.content()
        title = page.title()

        # Common rate limit indicators - more specific to avoid false positives
        indicators = {
            "rate_limit_text": "rate limit" in html.lower(),
            "too_many_requests": "too many requests" in html.lower(),
            "just_a_moment_title": "just a moment" in title.lower(),
            "checking_browser": "checking your browser" in html.lower(),
            # Only count cloudflare if it's a challenge page, not just mentioned in HTML
            "cloudflare_challenge": "just a moment" in title.lower()
            and "cloudflare" in html.lower(),
            "429_error": "429" in title.lower(),
            "503_error": "503" in title.lower(),
            "error_title": "error" in title.lower()
            and title.lower() not in ["top tweets", "twitter profile"],
        }

        if any(indicators.values()):
            self._rate_limit_hits += 1
            return True
        return False

    def _exponential_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay."""
        import random

        base = self.BACKOFF_BASE**attempt
        jitter = random.uniform(0, 1)
        return base + jitter

    def _is_cloudflare_challenge(self, page) -> bool:
        """
        Check if page is showing a Cloudflare challenge/CAPTCHA.
        Returns True if it's a challenge page.
        """
        html = page.content()
        title = page.title()

        # Cloudflare challenge indicators
        challenge_indicators = [
            "just a moment" in title.lower(),
            "checking your browser" in html.lower(),
            "one more step" in html.lower(),
            "please complete the security check" in html.lower(),
            "cf-im-under-attack" in html.lower(),
            "cf-browser-verification" in html.lower(),
            page.locator('input[name="cf-turnstile-response"]').count() > 0,
            page.locator('[class*="cf-"][class*="challenge"]').count() > 0,
            page.locator('text="Verify you are human"').count() > 0,
        ]

        return any(challenge_indicators)

    def _wait_for_cloudflare_resolution(self, page):
        """
        Wait for human to solve Cloudflare challenge.
        Only works in headful mode - will fail in headless.
        """
        if self.headless:
            print("⚠️  Cloudflare challenge detected but running in HEADLESS mode!")
            print(
                "   Cannot solve challenge automatically. Use without --headless flag"
            )
            return False

        print("\n" + "=" * 60)
        print("🔒 CLOUDFLARE CHALLENGE DETECTED")
        print("=" * 60)
        print("\nThe browser is showing a security challenge.")
        print("Please complete it manually in the browser window:")
        print("  1. Check the 'I'm not a robot' box if shown")
        print("  2. Solve any CAPTCHA presented")
        print("  3. Wait for the page to load completely")
        print("\n⏳ Waiting for you to complete the challenge...")
        print("   (Will auto-detect when done, or timeout after 5 min)\n")

        # Poll for resolution
        max_wait = 300  # 5 minutes max
        check_interval = 2  # Check every 2 seconds
        elapsed = 0

        while elapsed < max_wait:
            time.sleep(check_interval)
            elapsed += check_interval

            # Check if challenge is resolved
            if not self._is_cloudflare_challenge(page):
                print("✅ Challenge appears to be resolved!")
                # Wait a bit more for page to fully load
                time.sleep(3)
                return True

            # Show progress every 30 seconds
            if elapsed % 30 == 0:
                print(f"   ... still waiting ({elapsed}s elapsed)")

        print(f"\n⏱️  Timeout after {max_wait}s. Challenge not resolved.")
        return False

    def search_profiles(self, query: str, max_results: int = 50) -> List[XProfile]:
        """
        Search for profiles on TwStalker with rate limit respect.

        TwStalker search URL pattern: https://w.twstalker.com/search/<keywords>
        Example: https://w.twstalker.com/search/kebijakan
        """
        if not self.context:
            self._init_browser()

        profiles = []

        for attempt in range(self.MAX_RETRIES):
            try:
                # Enforce rate limit before request
                self._enforce_rate_limit()

                page = self._create_page()

                # Navigate to search page
                # TwStalker URL pattern: https://w.twstalker.com/search/<keywords>
                encoded_query = query.replace(" ", "%20")
                url = f"{self.BASE_URL}/search/{encoded_query}"

                print(f"Searching TwStalker: {url}")

                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                time.sleep(3)
                self._random_delay()

                # Check for rate limiting or Cloudflare challenge
                if self._handle_rate_limit_response(page):
                    # Check if it's specifically a Cloudflare challenge
                    if self._is_cloudflare_challenge(page):
                        # Try to wait for human resolution
                        resolved = self._wait_for_cloudflare_resolution(page)
                        if resolved:
                            # Challenge resolved, continue with parsing
                            html = page.content()
                            profiles = self._parse_search_results(html, max_results)
                            page.close()
                            if profiles:
                                print(
                                    f"✓ Found {len(profiles)} profiles after challenge"
                                )
                                break
                            else:
                                print(f"⚠️ No profiles found after challenge resolution")
                                continue
                        else:
                            # Challenge not resolved, use backoff
                            backoff = self._exponential_backoff(attempt)
                            print(
                                f"⚠️ Challenge not resolved. Backing off for {backoff:.1f}s..."
                            )
                            page.close()
                            time.sleep(backoff)
                            continue
                    else:
                        # Regular rate limit (not Cloudflare), use backoff
                        backoff = self._exponential_backoff(attempt)
                        print(
                            f"⚠️ Rate limited or blocked. Backing off for {backoff:.1f}s..."
                        )
                        page.close()
                        time.sleep(backoff)
                        continue

                # Parse results - extract handles from tweets
                html = page.content()
                handles = self._extract_handles_from_search(html)

                # Try to load more results if available
                if len(handles) < max_results:
                    additional_handles = self._load_more_handles(
                        page, max_results - len(handles)
                    )
                    handles.extend(additional_handles)

                # Remove duplicates
                handles = list(
                    dict.fromkeys(handles)
                )  # Preserves order, removes duplicates
                handles = handles[:max_results]

                print(f"  Found {len(handles)} unique handles from search")

                # Visit each profile page to get full details (if enrichment enabled)
                profiles = []
                if self.enrich_profiles:
                    for i, handle in enumerate(handles):
                        print(f"  [{i + 1}/{len(handles)}] Fetching profile: @{handle}")
                        profile = self.get_profile(handle)
                        if profile:
                            profiles.append(profile)
                            print(
                                f"    ✓ Got profile: {profile.display_name} ({profile.followers_count} followers)"
                            )
                        else:
                            print(f"    ✗ Failed to get profile for @{handle}")
                else:
                    # Quick mode: create basic profiles from handles only
                    print(f"  Quick mode: Skipping profile enrichment")
                    for handle in handles:
                        profiles.append(
                            XProfile(
                                handle=handle,
                                display_name=handle,
                                bio="",
                                followers_count=0,
                                following_count=0,
                                posts_count=0,
                                location="",
                                website="",
                                joined_date="",
                                is_verified=False,
                            )
                        )

                page.close()

                if profiles:
                    print(f"✓ Found {len(profiles)} profiles")
                    break
                else:
                    print(f"⚠️ No profiles found on attempt {attempt + 1}")

            except Exception as e:
                print(f"Error on attempt {attempt + 1}: {e}", file=sys.stderr)
                if attempt < self.MAX_RETRIES - 1:
                    backoff = self._exponential_backoff(attempt)
                    print(f"Retrying in {backoff:.1f}s...")
                    time.sleep(backoff)
                else:
                    print(f"Max retries reached. Giving up.")
                    break

        return profiles[:max_results]

    def _extract_handles_from_search(self, html: str) -> List[str]:
        """
        Extract unique Twitter handles from TwStalker search page HTML.

        TwStalker search shows tweets, and we extract the authors.
        """
        soup = BeautifulSoup(html, "lxml")
        handles = []

        # Method 1: Look for links to user profiles in tweets
        # Pattern: <a href="/@username"> or <a href="/username">
        user_links = soup.find_all("a", href=re.compile(r"^/[@]?[a-zA-Z0-9_]+$"))
        for link in user_links:
            href = link.get("href", "").strip("/").lstrip("@")
            # Filter out common non-user paths
            if href and href not in [
                "search",
                "about",
                "privacy",
                "terms",
                "login",
                "signup",
            ]:
                if len(href) > 1:  # Avoid single char handles which are likely not real
                    handles.append(href.lower())

        # Method 2: Look for @mentions in tweet text
        tweet_texts = soup.find_all(text=re.compile(r"@[a-zA-Z0-9_]+"))
        for text in tweet_texts:
            mentions = re.findall(r"@([a-zA-Z0-9_]+)", str(text))
            for mention in mentions:
                if mention.lower() not in [h.lower() for h in handles]:
                    handles.append(mention.lower())

        # Remove duplicates while preserving order
        seen = set()
        unique_handles = []
        for h in handles:
            if h not in seen:
                seen.add(h)
                unique_handles.append(h)

        return unique_handles

    def _load_more_handles(self, page, remaining_slots: int) -> List[str]:
        """
        Click 'Load more' buttons to get additional handles.

        TwStalker uses: <a class="add-nw-event" data-cursor="...">
        When clicked, renders additional content at the bottom.
        """
        additional_handles = []
        max_load_more_clicks = 10  # Prevent infinite loops

        for click_attempt in range(max_load_more_clicks):
            if len(additional_handles) >= remaining_slots:
                break

            # Find load more button
            load_more = page.locator("a.add-nw-event[data-cursor]").first

            if not load_more or load_more.count() == 0:
                print(
                    f"  No more 'Load more' buttons found after {click_attempt} clicks"
                )
                break

            try:
                # Get current handles to detect new content
                current_html = page.content()
                current_handles = set(self._extract_handles_from_search(current_html))

                # Click the load more button
                print(f"  Clicking 'Load more' button (attempt {click_attempt + 1})...")
                load_more.click()

                # Wait for new content to load
                time.sleep(2)
                self._random_delay()

                # Check if new content was added
                new_html = page.content()
                new_handles = self._extract_handles_from_search(new_html)
                new_handles_set = set(new_handles)

                # Find newly added handles
                newly_added = list(new_handles_set - current_handles)

                if newly_added:
                    slots_available = remaining_slots - len(additional_handles)
                    to_add = newly_added[:slots_available]
                    additional_handles.extend(to_add)
                    print(
                        f"    ✓ Loaded {len(to_add)} more handles (total: {len(additional_handles)}/{remaining_slots})"
                    )
                else:
                    print(f"    No new handles loaded")
                    break

            except Exception as e:
                print(f"    Error clicking load more: {e}")
                break

        return additional_handles

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
        """Get detailed profile information with rate limit respect."""
        if not self.context:
            self._init_browser()

        profile = None

        for attempt in range(self.MAX_RETRIES):
            try:
                # Enforce rate limit before request
                self._enforce_rate_limit()

                page = self._create_page()

                handle = handle.strip().lstrip("@").lower()
                url = f"{self.BASE_URL}/{handle}"

                print(f"Fetching profile: {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                time.sleep(3)
                self._random_delay()

                # Check for rate limiting or Cloudflare challenge
                if self._handle_rate_limit_response(page):
                    # Check if it's specifically a Cloudflare challenge
                    if self._is_cloudflare_challenge(page):
                        # Try to wait for human resolution
                        resolved = self._wait_for_cloudflare_resolution(page)
                        if resolved:
                            # Challenge resolved, continue with parsing
                            html = page.content()
                            profile = self._parse_profile(html, handle)
                            page.close()
                            if profile:
                                print(
                                    f"✓ Found profile: @{profile.handle} after challenge"
                                )
                                break
                            else:
                                print(f"⚠️ Profile not found after challenge resolution")
                                continue
                        else:
                            # Challenge not resolved, use backoff
                            backoff = self._exponential_backoff(attempt)
                            print(
                                f"⚠️ Challenge not resolved. Backing off for {backoff:.1f}s..."
                            )
                            page.close()
                            time.sleep(backoff)
                            continue
                    else:
                        # Regular rate limit (not Cloudflare), use backoff
                        backoff = self._exponential_backoff(attempt)
                        print(
                            f"⚠️ Rate limited or blocked. Backing off for {backoff:.1f}s..."
                        )
                        page.close()
                        time.sleep(backoff)
                        continue

                html = page.content()
                profile = self._parse_profile(html, handle)

                if profile:
                    print(f"✓ Found profile: @{profile.handle}")
                    page.close()
                    break
                else:
                    # Check if profile genuinely doesn't exist (not an error)
                    if self._is_profile_not_found(page):
                        print(f"⚠️ Profile @{handle} does not exist (not found page)")
                        page.close()
                        break  # Don't retry - profile genuinely not found
                    else:
                        print(
                            f"⚠️ Profile not found on attempt {attempt + 1} (will retry)"
                        )
                        page.close()
                        # Continue to next retry attempt

            except Exception as e:
                print(f"Error on attempt {attempt + 1}: {e}", file=sys.stderr)
                if attempt < self.MAX_RETRIES - 1:
                    backoff = self._exponential_backoff(attempt)
                    print(f"Retrying in {backoff:.1f}s...")
                    time.sleep(backoff)
                else:
                    print(f"Max retries reached. Giving up.")
                    break

        return profile

    def _parse_profile(self, html: str, handle: str) -> Optional[XProfile]:
        """Parse profile page HTML from TwStalker."""
        soup = BeautifulSoup(html, "lxml")

        try:
            # Check if profile exists - look for specific error indicators
            # Only check in title and main content areas, not anywhere on page
            title = soup.find("title")
            if title:
                title_text = title.get_text().lower()
                # Specific error patterns in title
                if any(
                    pattern in title_text
                    for pattern in [
                        "not found",
                        "doesn't exist",
                        "does not exist",
                        "page not found",
                        "404",
                        "error",
                        "user not found",
                        "account not found",
                        "profile not found",
                        "suspended",
                    ]
                ):
                    return None

            # Check for main error message (h1/h2 elements often contain error messages)
            for header in soup.find_all(["h1", "h2"]):
                header_text = header.get_text().lower()
                if any(
                    pattern in header_text
                    for pattern in [
                        "this account doesn't exist",
                        "this account does not exist",
                        "user not found",
                        "account not found",
                        "profile not found",
                        "account suspended",
                        "page not found",
                    ]
                ):
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

    def _is_profile_not_found(self, page) -> bool:
        """Check if the page shows a 'profile not found' error."""
        try:
            html = page.content()
            soup = BeautifulSoup(html, "lxml")

            # Check for common "not found" indicators
            not_found_patterns = [
                r"not found",
                r"doesn't exist",
                r"does not exist",
                r"page not found",
                r"404",
                r"error",
                r"user not found",
                r"account not found",
                r"profile not found",
                r"suspended",
                r"this account",
            ]

            # Check page title
            title = soup.find("title")
            if title:
                title_text = title.get_text().lower()
                for pattern in not_found_patterns:
                    if re.search(pattern, title_text, re.I):
                        return True

            # Check for error messages in page content
            page_text = soup.get_text().lower()
            error_indicators = [
                "this account doesn’t exist",
                "this account does not exist",
                "user not found",
                "profile not found",
                "page not found",
                "404 not found",
                "account suspended",
                "this user",
            ]
            for indicator in error_indicators:
                if indicator in page_text:
                    return True

            # Check for specific error elements
            error_elem = soup.find(
                text=re.compile(r"(not found|doesn't exist|does not exist)", re.I)
            )
            if error_elem:
                return True

            return False
        except Exception:
            # If we can't determine, assume it might be retriable
            return False

    def close(self):
        """Close browser and cleanup."""
        if self.context:
            self.context.close()
        if self._playwright:
            self._playwright.stop()

        # Print statistics
        print(f"\n📊 Request Statistics:")
        print(f"  Total requests: {self._request_count}")
        print(f"  Rate limit hits: {self._rate_limit_hits}")
        if self._request_count > 0:
            success_rate = (
                (self._request_count - self._rate_limit_hits)
                / self._request_count
                * 100
            )
            print(f"  Success rate: {success_rate:.1f}%")
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
    search_parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode: skip profile enrichment (faster)",
    )

    # Profile command
    profile_parser = subparsers.add_parser("profile", help="Get profile info")
    profile_parser.add_argument("handle", help="X/Twitter handle (without @)")
    profile_parser.add_argument("--output", "-o", help="Output JSON file")

    # Common options
    parser.add_argument(
        "--headless", action="store_true", help="Run headless (not recommended)"
    )
    parser.add_argument(
        "--delay-min",
        type=float,
        default=3.0,
        help="Min delay between actions (default: 3s)",
    )
    parser.add_argument(
        "--delay-max",
        type=float,
        default=7.0,
        help="Max delay between actions (default: 7s)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    delay_range = (args.delay_min, args.delay_max)
    enrich_profiles = not getattr(args, "quick", False)

    try:
        with TwStalkerSearcher(
            headless=args.headless,
            delay_range=delay_range,
            enrich_profiles=enrich_profiles,
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
