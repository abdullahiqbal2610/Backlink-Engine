"""
dev.to Poster — Type B (Playwright + API hybrid)

dev.to removed comment creation from their public API.
We use Playwright for posting comments (persistent session login).
The API key is still used for discovery (reading articles/feeds).

dev.to has no AutoModerator, no karma gates, and is much more permissive
than Reddit. Links to Gaper are totally fine in context.
"""

import os
import time
from typing import List, Dict
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from .base import PosterBase

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))


class DevToPoster(PosterBase):
    DEVTO_EMAIL_ENV    = "DEVTO_EMAIL"
    DEVTO_PASSWORD_ENV = "DEVTO_PASSWORD"

    def __init__(self):
        self.profile_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "browser_profiles", "devto"
        )
        os.makedirs(self.profile_dir, exist_ok=True)

    @property
    def platform_name(self) -> str:
        return "devto"

    @classmethod
    def discover_feeds(cls) -> List[Dict]:
        """RSS feeds for dev.to discovery — no API key needed for reading."""
        return [
            {"url": "https://dev.to/feed/tag/startup",          "platform": "devto", "scrape_type": 1},
            {"url": "https://dev.to/feed/tag/showdev",          "platform": "devto", "scrape_type": 1},
            {"url": "https://dev.to/feed/tag/entrepreneurship",  "platform": "devto", "scrape_type": 1},
            {"url": "https://dev.to/feed/tag/hiring",           "platform": "devto", "scrape_type": 1},
            {"url": "https://dev.to/feed/tag/saas",             "platform": "devto", "scrape_type": 1},
        ]

    def _is_logged_in(self, page) -> bool:
        """Check for user avatar nav icon — present only when logged in."""
        try:
            return (
                page.locator('[aria-label="Navigation user menu"]').count() > 0
                or page.locator('a[href="/signout_confirm"]').count() > 0
            )
        except Exception:
            return False

    def _manual_login_wait(self, page):
        """Beep and wait for user to login manually."""
        try:
            import winsound
            winsound.Beep(1000, 600)
        except Exception:
            pass

        print("\n" + "="*60)
        print("[!] DEV.TO: Not logged in!")
        print("[!] Please log in manually in the open browser window.")
        print("[!] Waiting indefinitely until login is detected...")
        print("="*60 + "\n")

        while not self._is_logged_in(page):
            time.sleep(4)
        print("[+] dev.to Login detected! Resuming...")

    def post(self, url: str, content: str) -> bool:
        print(f"[*] dev.to Playwright Poster starting for: {url}")

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

                print("[+] dev.to login verified!")

                # dev.to comment box: a contenteditable div inside the comment form
                # First scroll to the comment section
                page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                time.sleep(1)

                # The comment textarea uses CodeMirror or a simple textarea
                # Try textarea first (simpler dev.to comment boxes)
                comment_box = page.locator('textarea#comment-textarea, textarea[name="comment[body_markdown]"]').first
                if comment_box.count() == 0:
                    # Try contenteditable
                    comment_box = page.locator('#comment-form .comment-textarea, [data-testid="comment-field"]').first

                if comment_box.count() == 0:
                    print("[-] dev.to comment box not found on this page.")
                    context.close()
                    return False

                comment_box.click()
                time.sleep(0.5)
                comment_box.fill(content)
                time.sleep(1)

                # Submit button
                submit = page.locator('input[type="submit"][value="Submit"], button:has-text("Submit comment"), button[type="submit"]').first
                if submit.count() == 0:
                    print("[-] dev.to submit button not found.")
                    context.close()
                    return False

                submit.click()
                time.sleep(3)

                print("[+] dev.to comment submitted successfully!")
                context.close()
                return True

        except Exception as e:
            print(f"[-] dev.to Poster exception: {e}")
            return False


if __name__ == "__main__":
    poster = DevToPoster()
    print("Platform:", poster.platform_name)
    print("Feeds:", poster.discover_feeds())
