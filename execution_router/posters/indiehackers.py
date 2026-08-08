"""
Indie Hackers Poster — Type B (Playwright + Auth)

Indie Hackers uses standard form login (email + password).
Comments are posted to product/group discussions.
Perfect The Company audience: indie founders actively looking for dev talent & tools.

No public API exists, so we use Playwright for both discovery and posting.
"""

import os
import time
from typing import List, Dict
from playwright.sync_api import sync_playwright
from .base import PosterBase


class IndieHackersPoster(PosterBase):
    IH_EMAIL_ENV    = "IH_EMAIL"
    IH_PASSWORD_ENV = "IH_PASSWORD"
    BASE_URL        = "https://www.indiehackers.com"

    def __init__(self):
        self.profile_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "browser_profiles", "indiehackers"
        )
        os.makedirs(self.profile_dir, exist_ok=True)

    @property
    def platform_name(self) -> str:
        return "indiehackers"

    @classmethod
    def discover_feeds(cls) -> List[Dict]:
        """
        Indie Hackers has no RSS. We use their public API endpoints
        that return JSON, which the RssFetcher can handle via a custom fetcher.
        For now, we register placeholder URLs — the IH Discovery module handles them.
        """
        return [
            # These are handled by a custom IndieHackersDiscovery class
            {"url": "https://www.indiehackers.com/group/startups", "platform": "indiehackers", "scrape_type": 3},
            {"url": "https://www.indiehackers.com/group/growing-a-team", "platform": "indiehackers", "scrape_type": 3},
            {"url": "https://www.indiehackers.com/group/hiring", "platform": "indiehackers", "scrape_type": 3},
        ]

    def _is_logged_in(self, page) -> bool:
        """Check for user avatar / profile link that only appears when logged in."""
        try:
            return page.locator('[data-testid="user-avatar"], .nav__user-avatar, a[href*="/post/new"]').count() > 0
        except Exception:
            return False

    def _manual_login_wait(self, page):
        """Beep and wait for manual login."""
        try:
            import winsound
            winsound.Beep(1000, 600)
        except Exception:
            pass

        print("\n" + "="*60)
        print("[!] INDIE HACKERS: Not logged in!")
        print("[!] Please log in manually in the open browser window.")
        print("[!] Waiting indefinitely until login is detected...")
        print("="*60 + "\n")

        while not self._is_logged_in(page):
            time.sleep(4)
        print("[+] Login detected! Resuming...")

    def post(self, url: str, content: str) -> bool:
        print(f"[*] Indie Hackers Poster starting for: {url}")

        try:
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=self.profile_dir,
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                page = context.pages[0] if context.pages else context.new_page()

                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(3)

                if not self._is_logged_in(page):
                    self._manual_login_wait(page)
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    time.sleep(3)

                print("[+] Indie Hackers login verified!")

                # Indie Hackers has a rich text editor (ProseMirror / Quill)
                # The comment box is a div with contenteditable="true"
                comment_box = page.locator('[data-testid="comment-form"] [contenteditable="true"]').first
                if comment_box.count() == 0:
                    # Fallback selector
                    comment_box = page.locator('.content-editor__editor [contenteditable="true"]').first

                if comment_box.count() == 0:
                    print("[-] Could not find comment editor on this IH page.")
                    context.close()
                    return False

                # Click and type into the rich text editor
                comment_box.click()
                time.sleep(0.5)
                page.keyboard.type(content, delay=30)
                time.sleep(1)

                # Find and click the submit button
                submit = page.locator('[data-testid="submit-comment-button"], button:has-text("Submit"), button:has-text("Comment")').first
                if submit.count() == 0:
                    print("[-] Could not find comment submit button.")
                    context.close()
                    return False

                submit.click()
                time.sleep(3)
                print("[+] Indie Hackers comment submitted!")
                context.close()
                return True

        except Exception as e:
            print(f"[-] Indie Hackers Poster exception: {e}")
            return False


if __name__ == "__main__":
    poster = IndieHackersPoster()
    print("Platform:", poster.platform_name)
    print("Feeds:", poster.discover_feeds())
