import os
import json
import uuid
from datetime import datetime, timezone
import redis
import psycopg2
from dotenv import load_dotenv

# Load env variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

class DiscoveryPipeline:
    def __init__(self):
        # Redis connection
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_client = redis.from_url(redis_url)
        
        # Postgres connection
        self.db_conn = None
        try:
            self.db_conn = psycopg2.connect(
                dbname=os.getenv("POSTGRES_DB", "backlink_engine"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "postgres"),
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=os.getenv("POSTGRES_PORT", "5432")
            )
        except Exception as e:
            print(f"[-] Database connection failed. Running without DB dedup. Error: {e}")

    def is_duplicate(self, url: str) -> bool:
        """Checks if URL is already in the database."""
        if not self.db_conn:
            return False # Skip check if no DB
            
        try:
            with self.db_conn.cursor() as cur:
                cur.execute("SELECT 1 FROM threads WHERE url = %s", (url,))
                return cur.fetchone() is not None
        except Exception as e:
            print(f"[-] Error checking dedup: {e}")
            return False

    def insert_thread_record(self, thread_id: str, platform: str, url: str, title: str):
        """Inserts the basic thread record into Postgres to prevent future duplicates."""
        if not self.db_conn:
            return
            
        try:
            with self.db_conn.cursor() as cur:
                # Ensure platform exists to prevent foreign key violation
                cur.execute(
                    "INSERT INTO platforms (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
                    (platform,)
                )
                
                # Insert the thread
                cur.execute(
                    """
                    INSERT INTO threads (thread_id, platform, url, title, status)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (url) DO NOTHING
                    """,
                    (thread_id, platform, url, title, 'discovered')
                )
            self.db_conn.commit()
        except Exception as e:
            self.db_conn.rollback()
            print(f"[-] Error inserting thread: {e}")

    def normalize_to_contract_a(self, raw_data: dict, platform: str, scrape_type: int) -> dict:
        """Transforms raw data into the Contract A JSON format."""
        now = datetime.now(timezone.utc).isoformat()
        
        return {
            "thread_id": str(uuid.uuid4()),
            "platform": platform,
            "url": raw_data.get("url", ""),
            "title": raw_data.get("title", ""),
            "body": raw_data.get("snippet", ""), # Initially we only have a snippet
            "author": raw_data.get("author", "unknown"),
            "posted_at": raw_data.get("published", now),
            "scraped_at": now,
            "scrape_type": scrape_type,
            "community_guidelines": None,
            "guidelines_version": None
        }

    def process_item(self, item: dict, platform: str, scrape_type: int):
        """Runs an item through dedup, normalization, and queueing."""
        url = item.get("url")
        if not url:
            return

        if self.is_duplicate(url):
            print(f"[~] Skipping duplicate URL: {url}")
            return

        # Normalize
        payload = self.normalize_to_contract_a(item, platform, scrape_type)
        
        # Save to DB to mark as discovered
        self.insert_thread_record(payload["thread_id"], platform, url, payload["title"])
        
        # Push to Redis Queue
        try:
            self.redis_client.lpush("discovery_queue", json.dumps(payload))
            print(f"[+] Queued new opportunity: {payload['title'][:50]}... ({url})")
        except Exception as e:
            print(f"[-] Error pushing to Redis: {e}")

    def close(self):
        if self.db_conn:
            self.db_conn.close()
