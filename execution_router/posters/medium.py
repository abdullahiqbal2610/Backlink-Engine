import os
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from .base import PosterBase

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

class MediumPoster(PosterBase):
    def __init__(self):
        pass

    @property
    def platform_name(self) -> str:
        return "medium"

    @classmethod
    def discover_feeds(cls):
        return []

    def post(self, url: str, content: str) -> tuple[bool, str]:
        print("[*] Starting Medium automation...")

        try:
            with sync_playwright() as p:
                launch_options = {
                    "headless": False,  # Visible browser
                    "args": [
                        "--disable-blink-features=AutomationControlled",
                        "--ignore-certificate-errors"
                    ]
                }
                
                # Use a persistent profile so cookies/sessions are saved forever!
                profile_dir = os.path.join(os.path.dirname(__file__), "..", "..", "browser_profiles", "medium")
                
                print("[*] Launching Persistent Browser Profile...")
                context = p.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    **launch_options
                )
                
                page = context.pages[0] if context.pages else context.new_page()
                
                print("[*] Navigating to Medium's New Story page...")
                page.goto("https://medium.com/new-story", wait_until="domcontentloaded", timeout=60000)
                time.sleep(5) 
                
                # Check if we are logged in by checking if the URL redirected to login or homepage
                if "m/signin" in page.url or page.locator('a[data-action="sign-in-prompt"]').count() > 0:
                    print("\n" + "="*50)
                    print("[!] YOU ARE NOT LOGGED IN!")
                    print("[!] BROWSER WAITING... PLEASE LOG INTO MEDIUM MANUALLY.")
                    print("[!] Take your time. The script will automatically continue once you are logged in.")
                    print("="*50 + "\n")
                    import winsound
                    winsound.Beep(1000, 500)
                    
                    waiting_time = 0
                    while "new-story" not in page.url:
                        time.sleep(5)
                        waiting_time += 5
                        if waiting_time % 30 == 0:
                            print(f"[*] Still waiting for you to login... ({waiting_time}s elapsed)")
                        
                        if "m/signin" not in page.url and "new-story" not in page.url:
                            # if they drifted away after login, bring them back to the editor
                            try:
                                page.goto("https://medium.com/new-story", wait_until="domcontentloaded", timeout=60000)
                            except:
                                pass
                            
                print("\n[+] Login detected! Editor found. Proceeding with automation...\n")
                
                try:
                    success, live_url, account_used = self._real_post(page, content)
                    return success, live_url, account_used
                except Exception as post_err:
                    print(f"[-] Failed to post: {post_err}")
                    return False, None, "Local Profile"
                finally:
                    context.close()
                
        except Exception as e:
            print(f"[-] Automation error: {e}")
            return False, None, "Local Profile"
            
    def _real_post(self, page, content: str) -> tuple[bool, str, str]:
        print("[*] Extracting Title and Body...")
        lines = content.strip().split("\n")
        title = "An Insight into Modern Tech"
        if lines and lines[0].startswith("# "):
            title = lines[0].replace("# ", "").strip()
            content = "\n".join(lines[1:]).strip()
            
        print("[*] Waiting for Medium Editor to be ready...")
        time.sleep(5)
        
        print("[*] Clicking editor to focus...")
        try:
            editor = page.locator('[contenteditable="true"]').first
            editor.click()
            time.sleep(0.5)
            page.keyboard.press("Control+Home")
            time.sleep(0.5)
            print("[+] Focused editor, cursor at top. Typing Title...")
        except Exception as e:
            print(f"[-] Error focusing editor: {e}")
        
        time.sleep(1)
        page.keyboard.type(title, delay=50)
        time.sleep(1)
        
        print("[*] Pressing Enter to start Body...")
        page.keyboard.press("Enter")
        time.sleep(1)
        
        print("[*] Typing Body (this will take a while)...")
        page.keyboard.type(content, delay=10)
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
        
        # Take a debug screenshot to see what's on screen
        screenshot_path = os.path.join(os.path.dirname(__file__), "..", "..", "browser_profiles", "medium_debug.png")
        try:
            page.screenshot(path=screenshot_path)
            print(f"[*] Debug screenshot saved: {screenshot_path}")
        except:
            pass
        
        print("[*] Searching for final publish button using multiple strategies...")
        clicked = False
        
        # Strategy 1: "Publish now" text (most common)
        for btn_text in ["Publish now", "Publish story", "Publish"]:
            try:
                btns = page.locator(f'button:has-text("{btn_text}")')
                count = btns.count()
                print(f"[*] Found {count} button(s) with text '{btn_text}'")
                if count >= 2:
                    # Second Publish button = final confirm
                    btns.nth(1).click()
                    clicked = True
                    print(f"[+] Clicked 2nd '{btn_text}' button!")
                    break
                elif count == 1:
                    btns.first.click()
                    clicked = True
                    print(f"[+] Clicked '{btn_text}' button!")
                    break
            except Exception as e:
                print(f"    [-] Strategy with '{btn_text}' failed: {e}")
        
        # Strategy 2: JS — find and click all submit-type buttons visible in the drawer
        if not clicked:
            print("[*] Trying JavaScript button search as last resort...")
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
                print("[+] JS fallback clicked a publish button!")
            except Exception as e:
                print(f"[-] JS fallback failed: {e}")
        
        print("[*] Waiting a few seconds for publish request to fire...")
        time.sleep(5)
            
        current_url = page.url
        
        # Extract the shortlink from the URL (e.g., https://medium.com/p/1234567890ab)
        # Even if it stays on the submission page, the shortlink will redirect to the published post.
        import re
        match = re.search(r'(https://medium\.com/p/[a-zA-Z0-9]+)', current_url)
        if match:
            live_url = match.group(1)
        else:
            live_url = current_url

        print(f"[+] Successfully posted to Medium! URL: {live_url}")
        return True, live_url, "Local Profile"

