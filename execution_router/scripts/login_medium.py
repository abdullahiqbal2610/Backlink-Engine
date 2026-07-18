import os
import time
from playwright.sync_api import sync_playwright

def login_and_save_session():
    profile_dir = os.path.join(os.path.dirname(__file__), "..", "..", "browser_profiles", "medium")
    os.makedirs(profile_dir, exist_ok=True)
    
    print(f"[*] Will save persistent profile to: {profile_dir}")
    print("[*] Launching browser...")
    
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--ignore-certificate-errors"
            ]
        )
        
        page = context.pages[0] if context.pages else context.new_page()
        print("[*] Navigating to Medium login page...")
        page.goto("https://medium.com/m/signin")
        
        print("\n" + "="*60)
        print("BROWSER IS OPEN! PLEASE DO THE FOLLOWING:")
        print("1. Log in to your Medium account using Google, Email, or X.")
        print("2. Wait until you are fully logged in and see the Medium homepage.")
        print("3. DO NOT close the browser manually.")
        print("4. This script will detect when you're logged in and close automatically.")
        print("="*60 + "\n")
        
        waiting_time = 0
        while True:
            time.sleep(5)
            waiting_time += 5
            
            # If the user is on the homepage or the editor, they are logged in
            if "m/signin" not in page.url and "medium.com" in page.url:
                # Extra check: does the profile menu or write button exist?
                if page.locator('a[aria-label="Write"]').count() > 0 or page.locator('a[href="/new-story"]').count() > 0:
                    print("\n[+] SUCCESS! Login detected. Medium session saved permanently to browser_profiles/medium!")
                    break
            
            if waiting_time % 30 == 0:
                print(f"[*] Still waiting for you to login... ({waiting_time}s elapsed) Current URL: {page.url}")

        time.sleep(3)
        context.close()
        print("[*] Browser closed. You can now use the execution router for Medium!")

if __name__ == "__main__":
    login_and_save_session()
