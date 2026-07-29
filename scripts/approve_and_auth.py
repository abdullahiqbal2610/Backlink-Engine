import os
import sys
import psycopg2
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "backlink_engine"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432")
    )

def main():
    print("=== Platform Approval & Authentication Workflow ===")
    
    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"[-] Database connection failed: {e}")
        return

    cur = conn.cursor()
    cur.execute("SELECT id, domain, sample_url, relevance_score, ai_summary FROM discovered_platforms WHERE status = 'pending' ORDER BY relevance_score DESC")
    rows = cur.fetchall()

    if not rows:
        print("[*] No pending platforms to approve!")
        cur.close()
        conn.close()
        return

    print(f"[*] Found {len(rows)} pending platforms.\n")

    for row in rows:
        platform_id, domain, sample_url, relevance_score, ai_summary = row
        print("-" * 50)
        print(f"Domain: {domain}")
        print(f"Sample URL: {sample_url}")
        print(f"Relevance Score: {relevance_score}/10")
        print(f"AI Summary: {ai_summary}")
        print("-" * 50)
        
        choice = input(f"Do you want to approve this platform and create an account? (y/n/skip): ").strip().lower()
        if choice == 'skip':
            continue
        elif choice == 'n':
            cur.execute("UPDATE discovered_platforms SET status = 'rejected' WHERE id = %s", (platform_id,))
            conn.commit()
            print(f"[!] Rejected {domain}.")
            continue
        elif choice == 'y':
            print(f"\n[*] Launching Browser for {domain}...")
            print("[*] INSTRUCTIONS: Please create an account, log in, and verify your email if necessary.")
            print("[*] Close the browser window when you are fully logged in and ready for the AI to take over.")
            
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
                
            # Update DB to approved
            cur.execute("UPDATE discovered_platforms SET status = 'approved' WHERE id = %s", (platform_id,))
            conn.commit()
            print(f"[+] Approved {domain} for Autonomous Agent posting!")
        
    cur.close()
    conn.close()
    print("\n=== Workflow Complete ===")

if __name__ == "__main__":
    main()
