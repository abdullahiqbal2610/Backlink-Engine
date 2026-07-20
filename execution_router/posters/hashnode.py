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

                if "/drafts" in page.url:
                    print("[*] Landed on drafts dashboard. Clicking 'New' button to open editor...")
                    try:
                        time.sleep(3)
                        try:
                            # Try Playwright's get_by_text with exact match
                            new_btn = page.get_by_text("New", exact=True).first
                            new_btn.wait_for(state="visible", timeout=5000)
                            new_btn.click()
                        except:
                            print("[*] Falling back to JS click for 'New' button...")
                            page.evaluate("""
                                () => {
                                    const els = Array.from(document.querySelectorAll('*'));
                                    // Find innermost element with exact text 'New'
                                    const newBtn = els.reverse().find(e => e.textContent.trim() === 'New' && e.children.length === 0);
                                    if(newBtn) {
                                        newBtn.click();
                                        if(newBtn.closest('a')) newBtn.closest('a').click();
                                        else if(newBtn.closest('button')) newBtn.closest('button').click();
                                        else if(newBtn.parentElement) newBtn.parentElement.click();
                                    }
                                }
                            """)
                        time.sleep(5)
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
        
        print("[*] Searching for final publish button in drawer...")
        clicked = False
        
        try:
            for btn_text in ["Publish", "Publish Now", "Publish Article"]:
                btns = page.locator(f'button:has-text("{btn_text}")')
                count = btns.count()
                if count > 0:
                    # Click the last visible one (the one in the drawer)
                    for i in range(count - 1, -1, -1):
                        btn = btns.nth(i)
                        if btn.is_visible():
                            btn.click()
                            clicked = True
                            print(f"[+] Clicked '{btn_text}' button at index {i}")
                            break
                if clicked:
                    break
        except Exception as e:
            print(f"[-] Error finding publish button: {e}")
                
        if not clicked:
            print("[*] Trying generic JS fallback...")
            try:
                page.evaluate("""
                    () => {
                        const buttons = Array.from(document.querySelectorAll('button'));
                        const publishBtns = buttons.filter(b => 
                            b.textContent.trim().toLowerCase().includes('publish') &&
                            b.offsetParent !== null
                        );
                        if (publishBtns.length > 0) {
                            publishBtns[publishBtns.length - 1].click();
                        }
                    }
                """)
                clicked = True
                print("[+] Clicked via JS fallback")
            except Exception as e:
                print(f"[-] JS fallback failed: {e}")
                
        print("[*] Waiting for publish request to process (up to 25s)...")
        try:
            # Hashnode changes URL from /draft/... to /edit/... upon successful publish
            page.wait_for_url(lambda url: "/draft" not in url, timeout=25000)
            print("[+] URL changed! Publication successful.")
        except Exception as e:
            print("[-] Timeout waiting for URL change after publish.")
            
        current_url = page.url
        
        # If the URL STILL contains "draft", it definitely failed.
        if "/draft" in current_url:
            print(f"[-] URL still shows editor: {current_url}")
            print("[-] Publishing might have failed (missing tags, rate limit, etc).")
            return False, current_url, "Local Profile"

        print(f"[*] Post successful. Current URL is: {current_url}")
        
        # Try to extract the actual live blog URL instead of the /edit/ URL
        live_url = current_url
        try:
            extracted = page.evaluate("""
                () => {
                    // Try to find a link that goes to the live post
                    const links = Array.from(document.querySelectorAll('a'));
                    
                    // Often there is a toast or a button saying "View"
                    const viewBtn = links.find(a => 
                        a.textContent.trim().toLowerCase() === 'view' ||
                        a.textContent.trim().toLowerCase() === 'view post' ||
                        a.textContent.trim().toLowerCase() === 'view article'
                    );
                    if (viewBtn && viewBtn.href) return viewBtn.href;
                    
                    // Otherwise look for any .hashnode.dev or custom domain link that has a slug
                    const articleLink = links.reverse().find(a => 
                        a.href && !a.href.includes('/edit') && !a.href.includes('/draft') && 
                        !a.href.includes('hashnode.com') && a.href.startsWith('http') &&
                        !a.href.includes('linkedin.com') && !a.href.includes('twitter.com') &&
                        !a.href.includes('x.com') && !a.href.includes('instagram.com') && 
                        !a.href.includes('facebook.com') && !a.href.includes('discord.com') &&
                        !a.href.includes('youtube.com') && !a.href.includes('utm_source')
                    );
                    if (articleLink) return articleLink.href;
                    
                    return null;
                }
            """)
            if extracted:
                live_url = extracted
                print(f"[+] Extracted live URL from page: {live_url}")
        except:
            pass

        # Try to clean up URL if it has query params
        live_url = live_url.split("?")[0]
        
        print(f"[+] Successfully posted to Hashnode! URL: {live_url}")
        return True, live_url, "Local Profile"
