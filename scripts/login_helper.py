import os
import sys
from playwright.sync_api import sync_playwright

def main():
    if len(sys.argv) < 2:
        print("Usage: python login_helper.py <url>")
        print("Example: python login_helper.py https://news.ycombinator.com")
        sys.exit(1)
        
    url = sys.argv[1]
    
    from urllib.parse import urlparse
    domain = urlparse(url).netloc
    
    profiles_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "browser_profiles")
    os.makedirs(profiles_dir, exist_ok=True)
    
    state_file = os.path.join(profiles_dir, f"{domain}_state.json")
    
    print(f"[*] Launching browser for {domain}...")
    print("[*] Please log into the website. The browser will stay open until you close it.")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = context.new_page()
        page.goto(url)
        
        # Wait for the user to close the page manually
        try:
            page.wait_for_event("close", timeout=0) # wait infinitely until closed
        except Exception:
            pass
            
        print("[*] Browser closed. Saving session state...")
        context.storage_state(path=state_file)
        
    print(f"[+] Session state saved to: {state_file}")
    print("[+] The Generic Agent will now automatically use this account when posting to this domain!")

if __name__ == "__main__":
    main()
