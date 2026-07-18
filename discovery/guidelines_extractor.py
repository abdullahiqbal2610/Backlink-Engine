import os
import requests
import psycopg2
import urllib.parse
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "backlink_engine"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432")
    )

def extract_reddit_guidelines(subreddit: str) -> str:
    url = f"https://www.reddit.com/r/{subreddit}/about/rules.json"
    headers = {"User-Agent": "windows:backlink.ai.engine:v1.0.0 (by /u/Baba-Bandook-4747)"}
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            data = res.json()
            rules = data.get("rules", [])
            rules_text = ""
            for i, rule in enumerate(rules):
                rules_text += f"{i+1}. {rule.get('short_name', '')}: {rule.get('description', '')}\\n"
            print(f"[*] Found {len(rules)} rules.")
            return rules_text
        else:
            print(f"[-] Status code: {res.status_code}")
    except Exception as e:
        print(f"[-] Error fetching guidelines for {subreddit}: {e}")
    return ""

def fetch_and_cache_guidelines(url: str):
    parsed = urllib.parse.urlparse(url)
    
    if "reddit.com" in parsed.netloc:
        parts = parsed.path.split('/')
        if len(parts) >= 3 and parts[1] == 'r':
            subreddit = parts[2]
            platform_key = f"reddit_{subreddit}"
            
            # Check if cached
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT rules_text FROM platform_guidelines WHERE platform = %s", (platform_key,))
            row = cur.fetchone()
            
            if not row:
                print(f"[*] Extracting guidelines for {platform_key}...")
                rules = extract_reddit_guidelines(subreddit)
                if rules:
                    cur.execute(
                        "INSERT INTO platform_guidelines (platform, url, rules_text) VALUES (%s, %s, %s)",
                        (platform_key, f"https://www.reddit.com/r/{subreddit}/about/rules", rules)
                    )
                    conn.commit()
                    print("[+] Guidelines cached!")
            else:
                print(f"[~] Guidelines for {platform_key} already cached.")
            
            cur.close()
            conn.close()

if __name__ == "__main__":
    fetch_and_cache_guidelines("https://www.reddit.com/r/SaaS/comments/1uv227n/first_6_months_dealing_with_chargebacks_on_my/")
