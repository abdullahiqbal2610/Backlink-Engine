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
        print("    [!] GOOGLE_SHEET_ID not set. Skipping sheet log.")
        return
        
    try:
        import gspread
        from datetime import datetime
        
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        
        # Try file-based credentials first (local dev), then fall back to ADC (Cloud Run)
        creds_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'gcp_credentials.json')
        if os.path.exists(creds_path):
            from google.oauth2.service_account import Credentials
            creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
            client = gspread.authorize(creds)
            print("    [*] Using file-based GCP credentials for Sheets.")
        else:
            # On Cloud Run: use the service account attached to the job (ADC)
            import google.auth
            creds, _ = google.auth.default(scopes=scopes)
            client = gspread.authorize(creds)
            print("    [*] Using Application Default Credentials for Sheets.")
        
        sheet = client.open_by_key(sheet_id).sheet1
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row_data = [timestamp, platform, live_url or "Draft Saved", account_used]
        
        # Find next empty row in Column A to avoid overwriting
        col_values = sheet.col_values(1)
        next_row = len(col_values) + 1
        sheet.update(values=[row_data], range_name=f"A{next_row}:D{next_row}")
        
        print(f"    [+] Logged to Google Sheets: row {next_row}")
        
    except Exception as e:
        print(f"    [-] Failed to log to Google Sheets: {e}")



def main():
    print("=== Execution Router Worker ===")
    print(f"[+] Loaded {len(POSTER_REGISTRY)} platform poster(s): {', '.join(POSTER_REGISTRY.keys())}")
    print("Processing 'posting_queue'...")

    while True:
        try:
            # timeout=5 means if queue is empty for 5 seconds, it returns None
            result = r.brpop("posting_queue", timeout=5)
            if result is None:
                print("[*] Queue is empty. Exiting for Serverless scale-to-zero.")
                break
            _, item = result
            payload = json.loads(item.decode("utf-8"))

            thread_id     = payload.get("thread_id")
            # 1) Check if we already posted this thread to prevent duplicates
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 1 FROM post_results pr 
                        JOIN threads t ON pr.thread_id = t.thread_id 
                        WHERE t.url = %s AND pr.post_status = 'success'
                    """, (payload.get("url"),))
                    if cur.fetchone():
                        print(f"[!] Thread {payload.get('url')} already posted. Skipping to prevent duplicate.")
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
                
            # Download cookies from Redis
            if platform in ["hashnode", "medium", "reddit"]:
                cookie_str = r.get(f"cookies_{platform}")
                if cookie_str:
                    try:
                        save_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'browser_profiles', f"{platform}_cookies.json")
                        os.makedirs(os.path.dirname(save_path), exist_ok=True)
                        with open(save_path, "wb") as f:
                            f.write(cookie_str)
                        print(f"    [+] Loaded {platform} cookies from Redis to local disk.")
                    except Exception as e:
                        print(f"    [-] Failed to write cookies to disk: {e}")

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
                    # 1. Log to Google Sheets first (doesn't depend on DB)
                    log_to_google_sheet(platform, live_url, account_used)
                    
                    # 2. Try to save to Postgres DB
                    try:
                        conn = get_db_connection()
                        with conn.cursor() as cur:
                            # Ensure the thread exists (upsert) to satisfy foreign key
                            cur.execute("""
                                INSERT INTO platforms (name, scrape_type, posting_type) 
                                VALUES (%s, 'API', 'C') ON CONFLICT (name) DO NOTHING
                            """, (platform,))
                            # Try to get existing thread_id for this URL
                            cur.execute("SELECT thread_id FROM threads WHERE url = %s", (url,))
                            existing_thread = cur.fetchone()
                            
                            if existing_thread:
                                actual_thread_id = existing_thread[0]
                                cur.execute("""
                                    UPDATE threads SET status='posted', updated_at=CURRENT_TIMESTAMP
                                    WHERE thread_id=%s
                                """, (actual_thread_id,))
                            else:
                                actual_thread_id = thread_id
                                cur.execute("""
                                    INSERT INTO threads (thread_id, platform, url, title, status)
                                    VALUES (%s, %s, %s, %s, 'posted')
                                    ON CONFLICT DO NOTHING
                                """, (thread_id, platform, url, url))
                            
                            cur.execute("""
                                INSERT INTO post_results (thread_id, post_status, post_url, posted_at)
                                SELECT %s, 'success', %s, CURRENT_TIMESTAMP
                                WHERE NOT EXISTS (SELECT 1 FROM post_results WHERE post_url=%s)
                            """, (actual_thread_id, live_url, live_url))
                        conn.commit()
                        conn.close()
                        print(f"    [+] Saved live URL to DB: {live_url}")
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
