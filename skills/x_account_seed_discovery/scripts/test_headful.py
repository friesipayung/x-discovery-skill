#!/usr/bin/env python3
"""Simple test to verify headful Playwright with Chrome profile works."""

import nest_asyncio

nest_asyncio.apply()

from playwright.sync_api import sync_playwright
from pathlib import Path
import time


def get_chrome_executable():
    possible_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    for path in possible_paths:
        expanded = Path(path).expanduser()
        if expanded.exists():
            return str(expanded)
    return None


print("Starting headful browser test...")

with sync_playwright() as p:
    profile_path = str(Path.home() / ".x-discovery/chrome-profile")
    chrome_exe = get_chrome_executable()

    print(f"Profile: {profile_path}")
    print(f"Chrome: {chrome_exe}")
    print("Launching browser (headful - you should see a window)...")

    context = p.chromium.launch_persistent_context(
        user_data_dir=profile_path,
        headless=False,
        executable_path=chrome_exe,
        viewport={"width": 1920, "height": 1080},
    )

    page = context.new_page()
    print("Browser opened! Navigating to Google...")

    page.goto("https://www.google.com", wait_until="networkidle")
    print(f"Page loaded: {page.title()}")
    print("Browser will stay open for 10 seconds...")

    time.sleep(10)

    print("Closing browser...")
    context.close()

print("Test completed successfully!")
