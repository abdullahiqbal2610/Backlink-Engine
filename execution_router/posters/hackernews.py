"""
Hacker News Poster — Type B (Playwright + Session Auth)

HN uses a simple form-based login with a session cookie. Once logged in,
we navigate to the item page and submit the comment form directly.

No AutoModerator, no karma gates on comments. Links are allowed in HN comments.
Audience: senior engineers, founders, investors — perfect for Gaper.
"""

import os
import time
from typing import List, Dict
from playwright.sync_api import sync_playwright
from .base import PosterBase


class HackerNewsPoster(PosterBase):
    HN_USERNAME_ENV = "HN_USERNAME"
    HN_PASSWORD_ENV = "HN_PASSWORD"

    def __init__(self):
        self.profile_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "browser_profiles", "hackernews"
        )
        os.makedirs(self.profile_dir, exist_ok=True)

    @property
    def platform_name(self) -> str:
        return "hackernews"

    @classmethod
    def discover_feeds(cls) -> List[Dict]:
        """HN RSS feeds for discovery."""
        return [
            {"url": "https://news.ycombinator.com/rss",           "platform": "hackernews", "scrape_type": 1},
            {"url": "https://news.ycombinator.com/jobs.rss",       "platform": "hackernews", "scrape_type": 1},
        ]

    def _is_logged_in(self, page) -> bool:
        """Check if we are logged into HN by looking for the logout link."""
        try:
            return page.locator('a[href^="logout"]').count() > 0
        except Exception:
            return False

    def _login(self, page):
        """Navigate to HN login page and submit credentials."""
        username = os.getenv(self.HN_USERNAME_ENV)
        password = os.getenv(self.HN_PASSWORD_ENV)

        if not username or not password:
            print("\n" + "="*60)
            print("[!] HN_USERNAME / HN_PASSWORD not set in .env!")
            print("[!] Please create a HN account and add credentials.")
            print("[!] Waiting 120s for manual login in the open browser...")
            print("="*60 + "\n")
            # Let user manually login
            deadline = time.time() + 120
            while time.time() < deadline:
                if self._is_logged_in(page):
                    return True
                time.sleep(3)
            return False

        print(f"[*] Logging into HN as {username}...")
        page.goto("https://news.ycombinator.com/login", wait_until="domcontentloaded")
        page.fill('input[name="acct"]', username)
        page.fill('input[name="pw"]', password)
        page.click('input[type="submit"]')
        time.sleep(2)
        return self._is_logged_in(page)

    def post(self, url: str, content: str) -> bool:
        print(f"[*] HackerNews Poster starting for: {url}")

        # Extract the HN item ID from the URL
        # Expected: https://news.ycombinator.com/item?id=XXXXXXX
        if "item?id=" not in url:
            print(f"[-] Not a valid HN item URL: {url}")
            return False

        item_id = url.split("item?id=")[-1].split("&")[0].strip()
        print(f"[*] Resolved HN item ID: {item_id}")

        try:
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=self.profile_dir,
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                page = context.pages[0] if context.pages else context.new_page()

                # Navigate to the item page
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(2)

                # Login if needed (persistent context means usually 1-time only)
                if not self._is_logged_in(page):
                    logged_in = self._login(page)
                    if not logged_in:
                        print("[-] HN login failed.")
                        context.close()
                        return False
                    # Re-navigate to target after login
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    time.sleep(2)

                print("[+] HN Login verified!")

                # Find the top-level comment textarea
                textarea = page.locator('textarea[name="text"]').first
                if textarea.count() == 0:
                    print("[-] HN comment textarea not found. Thread may be closed.")
                    context.close()
                    return False

                # Type the comment
                textarea.click()
                time.sleep(0.5)
                textarea.fill(content)
                time.sleep(1)

                # Submit the form — HN uses an <input type="submit"> with value "add comment"
                submit_btn = page.locator('input[type="submit"][value="add comment"]').first
                if submit_btn.count() == 0:
                    # Fallback: any submit in the reply form
                    submit_btn = page.locator('form[action="comment"] input[type="submit"]').first

                submit_btn.click()
                time.sleep(3)

                # Verify success: page should reload to the item with our new comment
                current_url = page.url
                if "item?id=" in current_url:
                    print(f"[+] HN comment submitted successfully!")
                    context.close()
                    return True
                else:
                    print(f"[-] HN redirect unexpected after submit. URL: {current_url}")
                    context.close()
                    return False

        except Exception as e:
            print(f"[-] HN Poster exception: {e}")
            return False


if __name__ == "__main__":
    poster = HackerNewsPoster()
    print("Platform:", poster.platform_name)
    print("Feeds:", poster.discover_feeds())
