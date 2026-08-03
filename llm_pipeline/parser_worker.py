import os
import time
import json
import requests
from bs4 import BeautifulSoup
import redis
import psycopg2
from google import genai
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

class ParserWorker:
    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_client = redis.from_url(redis_url)
        
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key and "your_" not in self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None
            print("[!] GEMINI_API_KEY not configured. LLM Parser will be mocked.")
            
    def get_db_connection(self):
        return psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB", "backlink_engine"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432")
        )

    def scrape_text(self, url: str) -> str:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
            for script in soup(["script", "style", "nav", "footer"]):
                script.extract()
            text = soup.get_text(separator=' ', strip=True)
            return text[:10000] # Limiting to avoid huge context
        except Exception as e:
            print(f"[-] Failed to scrape {url}: {e}")
            return ""

    def process_url(self, item_payload: dict):
        url = item_payload.get("url")
        if not url: return
        
        domain = urlparse(url).netloc
        print(f"[*] Processing new domain: {domain}")
        
        try:
            conn = self.get_db_connection()
        except Exception as e:
            print(f"[-] Failed to connect to DB: {e}")
            return
            
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM discovered_platforms WHERE domain = %s", (domain,))
            if cur.fetchone():
                print(f"[~] Domain {domain} already in discovered_platforms.")
                conn.close()
                return
        
        scraped_text = self.scrape_text(url)
        
        ai_summary = "This site appears to be a blog or forum."
        guidelines = ""
        relevance_score = 0
        is_posting_difficult = False
        
        if self.client and scraped_text:
            prompt = (
                f"Analyze the following text extracted from {url}.\n"
                f"1. Summarize what this website is about and whether they accept guest posts, articles, or comments (ai_summary).\n"
                f"2. Extract any specific community guidelines or rules for posting (guidelines).\n"
                f"3. Score how relevant this site is to a B2B startup selling remote software engineering, AI developers, and tech talent (relevance_score from 1 to 10).\n"
                f"4. Determine if posting on this site is 'difficult' (is_posting_difficult = true if it requires complex ID verification, paid memberships, lacks any obvious guest-posting/commenting forms, or if it requires you to manually email pitches/articles to an editor instead of a direct submission form. If it simply requires a standard user account or login, it is NOT difficult).\n"
                f"Return ONLY a valid JSON object with the keys: 'ai_summary', 'guidelines', 'relevance_score' (int), and 'is_posting_difficult' (bool).\n\nText:\n{scraped_text}"
            )
            try:
                from google.genai import types
                response = self.client.models.generate_content(
                    model="gemini-flash-latest",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                    )
                )
                data = json.loads(response.text.strip())
                ai_summary = data.get("ai_summary", "")
                guidelines = data.get("guidelines", "")
                relevance_score = data.get("relevance_score", 0)
                is_posting_difficult = data.get("is_posting_difficult", False)
                
            except Exception as e:
                print(f"[-] Error calling LLM in ParserWorker: {e}")
                
        if is_posting_difficult:
            print(f"[-] Dropping {domain}: LLM determined posting is too difficult or restricted.")
            conn.close()
            return
            
        if relevance_score < 6:
            print(f"[-] Dropping {domain}: Relevance score too low ({relevance_score}/10).")
            conn.close()
            return
                
        # Insert into DB
        # Insert into DB
        try:
            # Check autonomous mode
            auto_val = self.redis_client.get("AUTONOMOUS_MODE")
            if auto_val is None:
                autonomous_mode = os.getenv("AUTONOMOUS_MODE", "false").lower() == "true"
            else:
                autonomous_mode = auto_val.decode('utf-8') == "true"

            with conn.cursor() as cur:
                if autonomous_mode:
                    cur.execute("""
                        INSERT INTO discovered_platforms (domain, sample_url, ai_summary, guidelines, status, relevance_score)
                        VALUES (%s, %s, %s, %s, 'approved', %s)
                        ON CONFLICT (domain) DO UPDATE SET status = 'approved' RETURNING id
                    """, (domain, url, ai_summary, guidelines, relevance_score))
                    row = cur.fetchone()
                    platform_id = row[0] if row else None
                    
                    platform_name = domain.replace('.', '_')
                    cur.execute("""
                        INSERT INTO platforms (name, scrape_type, posting_type) 
                        VALUES (%s, 'HTML', 'A') 
                        ON CONFLICT (name) DO NOTHING
                    """, (platform_name,))
                    
                    if guidelines:
                        cur.execute("""
                            INSERT INTO platform_guidelines (platform, url, rules_text) 
                            VALUES (%s, %s, %s)
                            ON CONFLICT (platform) DO UPDATE SET rules_text = EXCLUDED.rules_text
                        """, (platform_name, f"https://{domain}", guidelines))
                        
                    import uuid
                    from datetime import datetime, timezone
                    thread_id = str(uuid.uuid4())
                    title = "The Future of Remote Engineering Teams and AI"
                    body_context = f"Site Context: {ai_summary}\n\nPlease write a comprehensive guest post about hiring remote developers, scaling engineering teams, and integrating AI."
                    
                    cur.execute(
                        "INSERT INTO threads (thread_id, platform, url, title, status) VALUES (%s, %s, %s, %s, 'discovered') ON CONFLICT DO NOTHING",
                        (thread_id, platform_name, url, title)
                    )
                    
                    contract_a = {
                        "thread_id": thread_id,
                        "platform": platform_name,
                        "url": url,
                        "title": title,
                        "body": body_context,
                        "author": "unknown",
                        "posted_at": datetime.now(timezone.utc).isoformat(),
                        "scraped_at": datetime.now(timezone.utc).isoformat(),
                        "scrape_type": 4,
                        "community_guidelines": guidelines,
                        "guidelines_version": "1.0"
                    }
                    self.redis_client.lpush(f"discovery_queue_{platform_name}", json.dumps(contract_a))
                    self.redis_client.sadd("active_discovery_queues", f"discovery_queue_{platform_name}")
                    
                    print(f"[+] AUTONOMOUS MODE: Auto-approved {domain} and pushed to discovery_queue_{platform_name}")
                else:
                    cur.execute("""
                        INSERT INTO discovered_platforms (domain, sample_url, ai_summary, guidelines, status, relevance_score)
                        VALUES (%s, %s, %s, %s, 'pending', %s)
                        ON CONFLICT (domain) DO NOTHING
                    """, (domain, url, ai_summary, guidelines, relevance_score))
                    print(f"[+] Successfully added {domain} (Score: {relevance_score}/10) to discovered platforms. Waiting for manual approval.")
                    
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"[-] DB Error inserting {domain}: {e}")
        finally:
            conn.close()

    def run(self):
        print("=== LLM Parser Worker Started ===")
        while True:
            try:
                item = self.redis_client.brpop("llm_parser_queue", timeout=5)
                if item:
                    _, payload_str = item
                    payload = json.loads(payload_str.decode("utf-8"))
                    self.process_url(payload)
            except Exception as e:
                print(f"[-] Error in parser loop: {e}")
                time.sleep(2)

if __name__ == "__main__":
    worker = ParserWorker()
    worker.run()
