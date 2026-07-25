"""
Execution Router Worker

Listens on 'posting_queue' (Redis) for approved Contract C payloads.
Dispatches each item to the correct platform poster via POSTER_REGISTRY.

Adding a new platform: just update posters/__init__.py. Nothing here changes.
"""

import os
import sys
import json
import time
import redis
import psycopg2
from dotenv import load_dotenv

# Path setup so posters can import cleanly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

from execution_router.posters import POSTER_REGISTRY  # auto-populated from all platform modules

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(redis_url)


def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB",     "backlink_engine"),
        user=os.getenv("POSTGRES_USER",     "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        host=os.getenv("POSTGRES_HOST",     "localhost"),
        port=os.getenv("POSTGRES_PORT",     "5432"),
    )


def mark_thread_status(thread_id: str, status: str):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE threads SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE thread_id = %s",
            (status, thread_id),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[-] DB Error updating status: {e}")

def log_to_google_sheet(platform: str, live_url: str, account_used: str):
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        return
        
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        from datetime import datetime
        
        creds_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'gcp_credentials.json')
        if not os.path.exists(creds_path):
            print("    [-] gcp_credentials.json not found. Skipping Google Sheet log.")
            return
            
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
        client = gspread.authorize(creds)
        
        sheet = client.open_by_key(sheet_id).worksheet("Abdullah backlinks")
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Headings: Timestamp, Platform, Live URL, Account Used
        row_data = [timestamp, platform, live_url or "Draft Saved", account_used]
        
        # To avoid shifting when user adds other tables (like Tally) to the right,
        # explicitly find the next empty row based ONLY on Column A
        col_values = sheet.col_values(1)
        next_row = len(col_values) + 1
        sheet.update(values=[row_data], range_name=f"A{next_row}:D{next_row}")
        
        print(f"    [+] Logged successfully to Google Sheets!")
        
    except Exception as e:
        print(f"    [-] Failed to log to Google Sheets: {e}")


def main():
    print("=== Execution Router Worker ===")
    print(f"[+] Loaded {len(POSTER_REGISTRY)} platform poster(s): {', '.join(POSTER_REGISTRY.keys())}")
    print("Listening on 'posting_queue'...")

    while True:
        try:
            result = r.brpop("posting_queue", timeout=0)
            if result is None:
                continue
            _, item = result
            payload = json.loads(item.decode("utf-8"))

            thread_id     = payload.get("thread_id")
            # 1) Check if we already posted this thread to prevent duplicates
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM post_results WHERE thread_id = %s AND post_status = 'success'", (thread_id,))
                    if cur.fetchone():
                        print(f"[!] Thread {thread_id} already posted. Skipping to prevent duplicate.")
                        conn.close()
                        continue
                conn.close()
            except Exception as e:
                print(f"[-] DB Error checking duplicate: {e}")

            platform      = (payload.get("platform") or "").lower()
            url           = payload.get("url")
            final_comment = payload.get("final_comment") or payload.get("drafted_comment")

            print(f"\n[>] Routing post - Platform: {platform} | URL: {url[:60]}...")

            poster = POSTER_REGISTRY.get(platform)
            if not poster:
                print(f"[-] No poster registered for platform: '{platform}'")
                print(f"    Available platforms: {', '.join(POSTER_REGISTRY.keys())}")
                mark_thread_status(thread_id, "failed")
                continue

            result = poster.post(url, final_comment)
            
            # Handle both old (bool), new (tuple of 2), and newest (tuple of 3) return types during migration
            if isinstance(result, tuple):
                if len(result) == 3:
                    success, live_url, account_used = result
                else:
                    success, live_url = result
                    account_used = "Auto-rotated"
            else:
                success = result
                live_url = None
                account_used = "Auto-rotated"

            # Fallback: Try to extract username from URL if it's "Auto-rotated"
            if account_used == "Auto-rotated" and live_url:
                if "dev.to/" in live_url:
                    parts = live_url.split("dev.to/")
                    if len(parts) > 1:
                        account_used = "@" + parts[1].split("/")[0]
                elif "medium.com/" in live_url:
                    parts = live_url.split("medium.com/")
                    if len(parts) > 1 and parts[1].startswith("@"):
                        account_used = parts[1].split("/")[0]
                elif "gist.github.com/" in live_url:
                    parts = live_url.split("gist.github.com/")
                    if len(parts) > 1:
                        account_used = "@" + parts[1].split("/")[0]

            if success:
                print(f"[+] Successfully posted to {platform}!")
                mark_thread_status(thread_id, "posted")
                
                if live_url:
                    try:
                        conn = get_db_connection()
                        with conn.cursor() as cur:
                            cur.execute("""
                                INSERT INTO post_results (thread_id, post_status, post_url, posted_at)
                                VALUES (%s, 'success', %s, CURRENT_TIMESTAMP)
                            """, (thread_id, live_url))
                        conn.commit()
                        conn.close()
                        print(f"    [+] Saved live URL: {live_url}")
                        
                        # Log to Google Sheets
                        log_to_google_sheet(platform, live_url, account_used)
                        
                    except Exception as e:
                        print(f"    [-] Failed to save post_result to DB: {e}")
                
            else:
                print(f"[-] Failed to post to {platform}.")
                mark_thread_status(thread_id, "failed")

        except json.JSONDecodeError:
            print("[-] Error decoding JSON payload from queue.")
        except Exception as e:
            print(f"[-] Unexpected error in router: {e}")
            time.sleep(5)  # backoff before retrying


if __name__ == "__main__":
    main()
