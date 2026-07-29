import os
import sys
from playwright.sync_api import sync_playwright

def main(domain):
    print(f"[*] Launching Browser for {domain}...")
    
    profiles_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "browser_profiles")
    os.makedirs(profiles_dir, exist_ok=True)
    state_file = os.path.join(profiles_dir, f"{domain}_state.json")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        try:
            page.goto(f"https://{domain}")
        except Exception as e:
            print(f"[-] Failed to load {domain}: {e}")
        
        print("[!] Waiting for you to close the browser...")
        try:
            page.wait_for_event("close", timeout=0) # wait indefinitely until closed
        except Exception:
            pass
        
        # Save state
        context.storage_state(path=state_file)
        print(f"[+] Saved authentication state to {state_file}")
        browser.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
