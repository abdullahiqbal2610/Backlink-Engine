import os
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError
from .base import PosterBase

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

class RedditPoster(PosterBase):
    def __init__(self):
        self.username = os.getenv("REDDIT_USERNAME")
        self.password = os.getenv("REDDIT_PASSWORD")
        self.proxy_url = os.getenv("PROXY_URL")
        self.captcha_key = os.getenv("TWOCAPTCHA_API_KEY")

    @property
    def platform_name(self) -> str:
        return "reddit"

    @classmethod
    def discover_feeds(cls):
        return [
            {"url": "https://www.reddit.com/r/SaaS/.rss",         "platform": "reddit", "scrape_type": 1},
            {"url": "https://www.reddit.com/r/startups/.rss",      "platform": "reddit", "scrape_type": 1},
            {"url": "https://www.reddit.com/r/Entrepreneur/.rss",  "platform": "reddit", "scrape_type": 1},
            {"url": "https://www.reddit.com/r/webdev/.rss",        "platform": "reddit", "scrape_type": 1},
            {"url": "https://www.reddit.com/r/programming/.rss",   "platform": "reddit", "scrape_type": 1},
        ]

    def post(self, url: str, content: str) -> bool:
        print(f"[*] Starting Reddit automation for {url}")

        # Ensure url is absolute
        if not url.startswith("http"):
            # just for safety if queue has partial links
            url = "https://www.reddit.com" + url

        try:
            with sync_playwright() as p:
                launch_options = {
                    "headless": False,  # Must be visible so user can login if needed
                    "args": [
                        "--disable-blink-features=AutomationControlled",
                        "--ignore-certificate-errors"
                    ]
                }
                
                proxy_dict = None
                if self.proxy_url:
                    print(f"[*] Using Proxy: {self.proxy_url}")
                    import urllib.parse
                    parsed_proxy = urllib.parse.urlparse(self.proxy_url)
                    proxy_dict = {
                        "server": f"{parsed_proxy.scheme}://{parsed_proxy.hostname}:{parsed_proxy.port}"
                    }
                    if parsed_proxy.username and parsed_proxy.password:
                        proxy_dict["username"] = parsed_proxy.username
                        proxy_dict["password"] = parsed_proxy.password
                    launch_options["proxy"] = proxy_dict
                
                # Use a persistent profile so cookies/sessions are saved forever!
                profile_dir = os.path.join(os.path.dirname(__file__), "..", "..", "browser_profiles", "reddit")
                
                print("[*] Launching Persistent Browser Profile...")
                context = p.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    **launch_options
                )
                
                # Persistent context already has a default page
                page = context.pages[0] if context.pages else context.new_page()
                
                print(f"[*] Navigating to target URL: {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                time.sleep(5) # Let React render
                
                # Check if we are logged in by looking for the comment box directly
                comment_selectors = ['shreddit-composer', 'div[role="textbox"]', '.DraftEditor-root']
                
                def is_comment_box_present():
                    for selector in comment_selectors:
                        if page.locator(selector).count() > 0:
                            return True
                    return False
                    
                if not is_comment_box_present():
                    print("\n" + "="*50)
                    print("[!] YOU ARE NOT LOGGED IN!")
                    print("[!] BROWSER WAITING... PLEASE LOG INTO REDDIT MANUALLY.")
                    print("[!] Take your time. The script will automatically continue once you are logged in.")
                    print("="*50 + "\n")
                    import winsound
                    winsound.Beep(1000, 500)
                    
                    # Infinite loop waiting for user to login
                    # When user logs in, Reddit usually redirects them back to the post URL.
                    # We just check every 5 seconds if the comment box has appeared!
                    waiting_time = 0
                    while not is_comment_box_present():
                        time.sleep(5)
                        waiting_time += 5
                        if waiting_time % 30 == 0:
                            print(f"[*] Still waiting for you to login... ({waiting_time}s elapsed)")
                        
                        # Sometimes after login Reddit goes to homepage instead of redirecting back.
                        # If the URL changes to something else entirely and stays there, 
                        # we might want to navigate back, but let's assume standard redirect first.
                        if "login" not in page.url and url not in page.url:
                            # if they drifted away, bring them back to the post
                            page.goto(url, wait_until="domcontentloaded", timeout=60000)
                            
                print("\n[+] Login detected! Comment box found. Proceeding with automation...\n")
                
                try:
                    self._real_post(page, url, content)
                    return True
                except Exception as post_err:
                    print(f"[-] Failed to post: {post_err}")
                    return False
                finally:
                    context.close()
                
        except Exception as e:
            print(f"[-] Automation error: {e}")
            return False
            
    def _real_post(self, page, url: str, content: str):
        
        print("[*] Attempting to locate comment box...")
        # Scroll down slightly to ensure comment box is in view
        page.evaluate("window.scrollBy(0, 500)")
        time.sleep(2)
        
        print("[*] Attempting to locate comment box via Pure JavaScript...")
        # Pure JS Injection is bulletproof against Playwright's strict actionability timeouts
        box_type = page.evaluate('''() => {
            // 1. Try New Reddit (Shreddit)
            const composer = document.querySelector('shreddit-composer');
            if (composer) {
                // Focus the composer to activate it
                composer.focus();
                composer.click();
                
                // Find the actual typing area inside the shadow DOM
                const internalBox = composer.shadowRoot?.querySelector('div[contenteditable="true"], textarea, div[role="textbox"]');
                if (internalBox) {
                    internalBox.focus();
                    return "shreddit-composer";
                }
            }
            
            // 2. Try Old Reddit / Standard UIs
            const oldBox = document.querySelector('.DraftEditor-root, div[role="textbox"]');
            if (oldBox) {
                oldBox.focus();
                return "standard-ui";
            }
            
            return null;
        }''')
        
        if not box_type:
            print("[-] Could not find the comment box. Reddit UI may have changed.")
            raise Exception("Comment box not found")
            
        print(f"[+] Found {box_type}! Typing comment...")
        # Give the browser a second to actually place the blinking cursor inside the box
        time.sleep(1)
        
        # Now that the box is focused natively by JS, Playwright's keyboard will type directly into it!
        page.keyboard.type(content, delay=30)
        time.sleep(1)
        
        print("[*] Clicking Reply...")
        
        # Try finding the Comment/Reply button
        # In shreddit, it's often a button with slot="submitButton"
        try:
            submit_btn = page.locator('button[slot="submitButton"]').first
            if submit_btn and submit_btn.is_visible():
                submit_btn.click()
            else:
                # Fallback to keyboard shortcut
                page.keyboard.press("Control+Enter")
        except Exception:
            page.keyboard.press("Control+Enter")
            
        time.sleep(4)
        print("[+] Successfully posted to Reddit!")

    def _get_db_conn(self):
        import psycopg2
        return psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB", "backlink_engine"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432")
        )

    def _load_cookies(self, context) -> bool:
        try:
            conn = self._get_db_conn()
            cur = conn.cursor()
            cur.execute("SELECT cookies_json FROM cookie_vault WHERE platform = 'reddit' AND account_username = %s", (self.username,))
            row = cur.fetchone()
            if row:
                import json
                cookies = json.loads(row[0])
                context.add_cookies(cookies)
                cur.close()
                conn.close()
                return True
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[-] Error loading cookies: {e}")
        return False

    def _save_cookies(self, context):
        try:
            cookies = context.cookies()
            import json
            cookies_json = json.dumps(cookies)
            conn = self._get_db_conn()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO cookie_vault (platform, account_username, cookies_json) VALUES ('reddit', %s, %s) "
                "ON CONFLICT (platform, account_username) DO UPDATE SET cookies_json = EXCLUDED.cookies_json, updated_at = CURRENT_TIMESTAMP",
                (self.username, cookies_json)
            )
            conn.commit()
            cur.close()
            conn.close()
            print("[+] Session cookies saved to vault.")
        except Exception as e:
            print(f"[-] Error saving cookies: {e}")
