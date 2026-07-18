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
                    success, live_url = self._real_post(page, content)
                    return success, live_url
                except Exception as post_err:
                    print(f"[-] Failed to post: {post_err}")
                    return False, None
                finally:
                    context.close()
                
        except Exception as e:
            print(f"[-] Automation error: {e}")
            return False, None
            
    def _real_post(self, page, content: str) -> tuple[bool, str]:
        print("[*] Extracting Title and Body from Markdown...")
        lines = content.strip().split("\n")
        title = "An Insight into Modern Tech"
        if lines and lines[0].startswith("# "):
            title = lines[0].replace("# ", "").strip()
            content = "\n".join(lines[1:]).strip()
            
        print("[*] Waiting for Medium Editor to be ready...")
        time.sleep(5)
        
        # Click the editor area first to ensure focus, then go to very top
        print("[*] Clicking editor to focus...")
        try:
            # Click anywhere on the editor
            editor = page.locator('[contenteditable="true"]').first
            editor.click()
            time.sleep(0.5)
            # Jump to top of document to make sure we are in the title
            page.keyboard.press("Control+Home")
            time.sleep(0.5)
            print("[+] Focused editor, cursor at top. Typing Title...")
        except Exception as e:
            print(f"[-] Error focusing editor: {e}")
        
        time.sleep(1)
        
        # Typing the title
        page.keyboard.type(title, delay=50)
        time.sleep(1)
        
        print("[*] Pressing Enter to start Body...")
        page.keyboard.press("Enter")
        time.sleep(1)
        
        print("[*] Typing Body (this will take a while)...")
        # Typing the whole body with delay=10 to simulate human typing
        page.keyboard.type(content, delay=10)
        time.sleep(2)
        
        print("[*] Clicking Publish button...")
        # Medium's publish button usually has the text "Publish"
        publish_btn = page.locator('button:has-text("Publish")').first
        publish_btn.click()
        
        print("[*] Waiting for the slide-in panel or submission page...")
        # The submission page can take a few seconds to load
        try:
            page.wait_for_url("**/submission**", timeout=10000)
            print("[+] Navigated to Submission page.")
        except:
            pass # It might just be a slide-in panel
            
        time.sleep(3) # Wait for animations/rendering
        
        try:
            print("[*] Looking for Final Publish button on submission page...")
            # Screenshot of submission page shows the final button text is simply "Publish"
            # We wait for ALL "Publish" buttons and pick the one that's a dark/submit button
            # The first publish button is now gone (we already navigated away), so the next one is the final one
            final_publish_btn = page.locator('button:has-text("Publish")').first
            final_publish_btn.wait_for(state="visible", timeout=10000)
            print("[*] Clicking Final Publish button on submission page...")
            final_publish_btn.click()
        except Exception as e:
            print(f"[-] Could not click final 'Publish': {e}")
            
        print("[*] Waiting for redirect to published story...")
        # Wait for the story to be published (URL should no longer contain /submission)
        time.sleep(5)
        for _ in range(15):
            if "submission" not in page.url and "edit" not in page.url and "new-story" not in page.url:
                break
            time.sleep(2)
            
        live_url = page.url
        print(f"[+] Successfully posted to Medium! URL: {live_url}")
        return True, live_url
