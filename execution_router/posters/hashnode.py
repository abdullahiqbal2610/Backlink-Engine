import os
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from .base import PosterBase

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

class HashnodePoster(PosterBase):
    def __init__(self):
        pass

    @property
    def platform_name(self) -> str:
        return "hashnode"

    @classmethod
    def discover_feeds(cls):
        return []

    def post(self, url: str, content: str) -> tuple[bool, str, str]:
        print("[*] Starting Hashnode automation via Cookie Injection...")

        cookies_path = os.path.join(os.path.dirname(__file__), "..", "..", "browser_profiles", "hashnode_cookies.json")
        
        if not os.path.exists(cookies_path):
            print(f"[-] hashnode_cookies.json not found at {cookies_path}")
            print("[-] Run hashnode_login.py first to extract cookies from Chrome!")
            return False, None, "N/A"
        
        try:
            import json
            with open(cookies_path, "r", encoding="utf-8") as f:
                raw = f.read().strip()
            saved_cookies = json.loads(raw)
            # Handle case where JSON is double-encoded
            if isinstance(saved_cookies, str):
                saved_cookies = json.loads(saved_cookies)
            if not isinstance(saved_cookies, list):
                print(f"[-] Unexpected cookie format: {type(saved_cookies)}")
                return False, None, "N/A"
        except Exception as e:
            print(f"[-] Failed to load cookies: {e}")
            return False, None, "N/A"

        try:
            with sync_playwright() as p:
                # Use Playwright's Chromium in non-headless mode
                browser = p.chromium.launch(
                    headless=False,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--start-maximized"
                    ]
                )
                
                context = browser.new_context(
                    no_viewport=True,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
                )
                
                # Inject saved cookies BEFORE navigating
                print("[*] Injecting Hashnode session cookies...")
                playwright_cookies = []
                for c in saved_cookies:
                    cookie = {
                        "name": c["name"],
                        "value": c["value"],
                        "domain": c["domain"],
                        "path": c.get("path", "/"),
                        "secure": c.get("secure", True),
                        "httpOnly": c.get("httpOnly", False),
                    }
                    # sameSite must be one of Strict, Lax, None
                    same_site = c.get("sameSite", "Lax")
                    if same_site == "no_restriction":
                        cookie["sameSite"] = "None"
                    elif same_site and same_site.lower() in ["strict", "lax", "none"]:
                        cookie["sameSite"] = same_site.capitalize()
                    else:
                        cookie["sameSite"] = "Lax"
                    playwright_cookies.append(cookie)
                
                context.add_cookies(playwright_cookies)
                print(f"[+] Injected {len(playwright_cookies)} cookies.")
                
                page = context.new_page()
                
                print("[*] Navigating to Hashnode editor via hn.new...")
                page.goto("https://hn.new", wait_until="domcontentloaded", timeout=60000)
                time.sleep(5)
                
                # Verify we are actually in the editor and not on login page
                if "login" in page.url or "onboard" in page.url:
                    print("[-] Cookie injection failed — still being redirected to login!")
                    print("[-] Please re-export cookies from Chrome (they may have expired) and try again.")
                    browser.close()
                    return False, None, "N/A"

                if page.url.rstrip("/").endswith("drafts"):
                    print("[*] Landed on drafts dashboard. Clicking 'New' button to open editor...")
                    try:
                        new_btn = page.locator('a:has-text("New"), button:has-text("New")').first
                        new_btn.wait_for(state="visible", timeout=10000)
                        new_btn.click()
                        time.sleep(4)
                        print(f"[*] Navigated to: {page.url}")
                    except Exception as e:
                        print(f"[-] Failed to click 'New': {e}")
                        
                print(f"[+] Cookie injection successful! Editor loaded at: {page.url}")
                
                try:
                    success, live_url, account_used = self._real_post(page, content)
                    return success, live_url, account_used
                except Exception as post_err:
                    print(f"[-] Failed to post: {post_err}")
                    return False, None, "N/A"
                finally:
                    browser.close()
                
        except Exception as e:
            print(f"[-] Automation error: {e}")
            return False, None, "N/A"
            
    def _real_post(self, page, content: str) -> tuple[bool, str, str]:
        print("[*] Extracting Title and Body...")
        lines = content.strip().split("\n")
        title = "An Insight into Modern Tech"
        if lines and lines[0].startswith("# "):
            title = lines[0].replace("# ", "").strip()
            content = "\n".join(lines[1:]).strip()
            
        print("[*] Waiting for Hashnode Editor to be ready...")
        time.sleep(5)
        
        # Hashnode editor often uses a textarea with placeholder "Article Title"
        # and another textarea or contenteditable for the body.
        print("[*] Clicking editor to focus...")
        try:
            # Let's try to find the title input specifically
            title_inputs = page.locator('textarea[placeholder*="Title"], input[placeholder*="Title"], [data-placeholder*="Title"], textarea[placeholder*="title"]')
            if title_inputs.count() > 0:
                title_inputs.first.click()
                time.sleep(0.5)
                # Clear existing if any
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                page.keyboard.type(title, delay=50)
                print("[+] Typed Title in specific field.")
                
                # Tab should go to the body
                page.keyboard.press("Tab")
                time.sleep(0.5)
                page.keyboard.type(content, delay=10)
            else:
                print("[-] Could not find explicit title field. Using center-click fallback...")
                # Fallback: Just click the center of the page and use keyboard navigation
                page.mouse.click(500, 300)
                time.sleep(0.5)
                page.keyboard.press("Control+Home")
                page.keyboard.type(title, delay=50)
                page.keyboard.press("Enter")
                page.keyboard.type(content, delay=10)
                
        except Exception as e:
            print(f"[-] Error typing in editor: {e}")
            return False, None, "Local Profile"
        
        time.sleep(2)
        
        # Escape to dismiss any floating toolbar before clicking Publish
        page.keyboard.press("Escape")
        time.sleep(1)
        
        print("[*] Clicking first Publish button (opens drawer)...")
        try:
            publish_btn = page.locator('button:has-text("Publish")').first
            publish_btn.wait_for(state="visible", timeout=10000)
            publish_btn.click()
        except Exception as e:
            print(f"[-] Could not click Publish: {e}")
            return False, None, "Local Profile"
        
        print("[*] Waiting for publish drawer to open...")
        time.sleep(4)
        
        # Take a debug screenshot
        screenshot_path = os.path.join(os.path.dirname(__file__), "..", "..", "browser_profiles", "hashnode_debug.png")
        try:
            page.screenshot(path=screenshot_path)
            print(f"[*] Debug screenshot saved: {screenshot_path}")
        except:
            pass
        
        print("[*] Searching for final publish button...")
        clicked = False
        
        for btn_text in ["Publish", "Publish Now", "Publish Article"]:
            try:
                btns = page.locator(f'button:has-text("{btn_text}")')
                count = btns.count()
                if count >= 2:
                    # Second button is usually the confirmation one
                    btns.nth(1).click()
                    clicked = True
                    break
                elif count == 1:
                    btns.first.click()
                    clicked = True
                    break
            except:
                pass
                
        if not clicked:
            print("[*] Trying generic JS fallback...")
            try:
                page.evaluate("""
                    () => {
                        const buttons = Array.from(document.querySelectorAll('button'));
                        const publishBtn = buttons.find(b => 
                            b.textContent.trim().toLowerCase().includes('publish') &&
                            b.offsetParent !== null
                        );
                        if (publishBtn) publishBtn.click();
                    }
                """)
                clicked = True
            except:
                pass
                
        print("[*] Waiting a few seconds for publish request to fire...")
        time.sleep(8)
            
        current_url = page.url
        
        # If the URL contains "draft", it probably failed.
        # Published Hashnode articles usually don't contain "draft"
        if "draft" in current_url and not clicked:
            print(f"[-] URL still shows editor: {current_url}")
            print("[-] Publishing might have failed. Check debug screenshot.")
            return False, current_url, "Local Profile"

        # Try to clean up URL if it has query params
        live_url = current_url.split("?")[0]
        
        print(f"[+] Successfully posted to Hashnode! URL: {live_url}")
        return True, live_url, "Local Profile"
