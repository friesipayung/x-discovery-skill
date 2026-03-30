#!/usr/bin/env python3
"""
Chrome Profile Manager for X Account Seed Discovery
Creates and manages a dedicated Chrome profile for Playwright automation.

Usage:
    python chrome_profile.py create
    python chrome_profile.py test
    python chrome_profile.py info
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


# Default profile location
DEFAULT_PROFILE_DIR = Path.home() / ".x-discovery" / "chrome-profile"
PROFILE_NAME = "X-Discovery"


def get_chrome_executable() -> str:
    """Find Chrome executable path."""
    # Common Chrome paths by platform
    possible_paths = [
        # macOS
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        # Linux
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/snap/bin/chromium",
        # Windows
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    ]

    for path in possible_paths:
        expanded = Path(path).expanduser()
        if expanded.exists():
            return str(expanded)

    # Try to find in PATH
    try:
        result = subprocess.run(
            ["which", "google-chrome"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except:
        pass

    return None


def create_profile():
    """Create the X-Discovery Chrome profile."""
    profile_dir = DEFAULT_PROFILE_DIR

    # Create directory structure
    profile_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories that Chrome expects
    (profile_dir / "Default").mkdir(exist_ok=True)
    (profile_dir / "System Profile").mkdir(exist_ok=True)

    # Create a README
    readme = profile_dir / "README.txt"
    readme.write_text(f"""X-Discovery Chrome Profile
==========================

Profile Name: {PROFILE_NAME}
Location: {profile_dir}

This profile is used by the X Account Seed Discovery skill for Playwright automation.

Usage:
    - The profile persists cookies, localStorage, and session data
    - You can manually open Chrome with this profile to pre-login to sites
    - Playwright will use this profile for all X-Discovery operations

Manual Chrome Launch:
    {get_chrome_executable() or "google-chrome"} --user-data-dir="{profile_dir}"

Created: {__import__("datetime").datetime.now().isoformat()}
""")

    print(f"✅ Created Chrome profile: {PROFILE_NAME}")
    print(f"📁 Profile location: {profile_dir}")
    print(
        f"🌐 Chrome executable: {get_chrome_executable() or 'Not found - please install Chrome'}"
    )
    print()
    print("You can manually launch Chrome with this profile:")
    chrome = get_chrome_executable() or "google-chrome"
    print(f'  {chrome} --user-data-dir="{profile_dir}"')
    print()
    print("Or use it in Playwright:")
    print(f"  context = browser.new_context(user_data_dir='{profile_dir}')")

    return profile_dir


def test_profile():
    """Test the profile by launching Chrome."""
    profile_dir = DEFAULT_PROFILE_DIR

    if not profile_dir.exists():
        print(f"❌ Profile not found at: {profile_dir}")
        print("Run: python chrome_profile.py create")
        return 1

    chrome = get_chrome_executable()
    if not chrome:
        print("❌ Chrome not found. Please install Google Chrome.")
        return 1

    print(f"🚀 Launching Chrome with profile: {PROFILE_NAME}")
    print(f"📁 Profile: {profile_dir}")
    print()
    print("Chrome will open. Close it manually when done.")
    print()

    try:
        subprocess.run(
            [
                chrome,
                f"--user-data-dir={profile_dir}",
                "--no-first-run",
                "--no-default-browser-check",
                "https://www.google.com",
            ]
        )
        return 0
    except Exception as e:
        print(f"❌ Error launching Chrome: {e}")
        return 1


def get_profile_info():
    """Get information about the profile."""
    profile_dir = DEFAULT_PROFILE_DIR

    info = {
        "profile_name": PROFILE_NAME,
        "profile_dir": str(profile_dir),
        "exists": profile_dir.exists(),
        "chrome_executable": get_chrome_executable(),
        "size_mb": 0,
    }

    if profile_dir.exists():
        # Calculate size
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(profile_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        info["size_mb"] = round(total_size / (1024 * 1024), 2)

    return info


def show_info():
    """Display profile information."""
    info = get_profile_info()

    print("X-Discovery Chrome Profile Information")
    print("=" * 50)
    print(f"Profile Name: {info['profile_name']}")
    print(f"Profile Directory: {info['profile_dir']}")
    print(f"Exists: {'✅ Yes' if info['exists'] else '❌ No'}")
    if info["exists"]:
        print(f"Size: {info['size_mb']} MB")
    print(f"Chrome Executable: {info['chrome_executable'] or '❌ Not found'}")
    print()

    if info["exists"]:
        print("Playwright Usage:")
        print(f"  profile_dir = '{info['profile_dir']}'")
        print("  context = browser.new_context(")
        print("      user_data_dir=profile_dir,")
        print("      viewport={'width': 1920, 'height': 1080}")
        print("  )")
    else:
        print("Profile not created yet. Run:")
        print("  python chrome_profile.py create")


def main():
    parser = argparse.ArgumentParser(
        description="Chrome Profile Manager for X-Discovery"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Create command
    subparsers.add_parser("create", help="Create the X-Discovery Chrome profile")

    # Test command
    subparsers.add_parser("test", help="Test the profile by launching Chrome")

    # Info command
    subparsers.add_parser("info", help="Show profile information")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "create":
        create_profile()
        return 0
    elif args.command == "test":
        return test_profile()
    elif args.command == "info":
        show_info()
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
