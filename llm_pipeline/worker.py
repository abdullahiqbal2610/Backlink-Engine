import os
# Suppress ChromaDB telemetry warnings
os.environ["ANONYMIZED_TELEMETRY"] = "False"
import time
import json
from datetime import datetime, timezone
import redis
import psycopg2
from dotenv import load_dotenv

from rag_store import RagStore
from relevance_agent import RelevanceAgent
from drafter_agent import DrafterAgent

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

class LlmWorker:
    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_client = redis.from_url(redis_url)
        
        self.rag_store = RagStore()
        self.relevance_agent = RelevanceAgent()
        self.drafter_agent = DrafterAgent()
        
        try:
            self.db_conn = psycopg2.connect(
                dbname=os.getenv("POSTGRES_DB", "backlink_engine"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "postgres"),
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=os.getenv("POSTGRES_PORT", "5432")
            )
        except Exception as e:
            print(f"[-] DB Connection error in worker: {e}")
            self.db_conn = None

    def update_thread_status(self, thread_id: str, is_relevant: bool, new_status: str):
        if not self.db_conn:
            return
        try:
            with self.db_conn.cursor() as cur:
                cur.execute(
                    "UPDATE threads SET is_relevant = %s, status = %s, updated_at = CURRENT_TIMESTAMP WHERE thread_id = %s",
                    (is_relevant, new_status, thread_id)
                )
            self.db_conn.commit()
        except Exception as e:
            self.db_conn.rollback()
            print(f"[-] Error updating thread status: {e}")

    def run(self):
        print("=== Starting LLM Pipeline Worker ===")
        print("Listening on 'discovery_queue'...")
        
        is_paused = False
        while True:
            # Check review queue size for throttling
            review_queue_size = self.redis_client.llen("review_queue")
            
            if is_paused:
                if review_queue_size == 0:
                    print("\n[!] Review queue is empty! Waking up LLM Pipeline...")
                    is_paused = False
                else:
                    # Still paused, wait and check again
                    time.sleep(5)
                    continue
            else:
                if review_queue_size >= 20:
                    print("\n[!] Review queue reached 20 items. Pausing LLM Pipeline to prevent overload...")
                    is_paused = True
                    continue

            # Block until an item is available in the queue (timeout 5s)
            item = self.redis_client.brpop("discovery_queue", timeout=5)
            
            if not item:
                # No items, loop again
                continue
                
            _, data_bytes = item
            payload = json.loads(data_bytes.decode('utf-8'))
            
            thread_id = payload.get("thread_id")
            platform = payload.get("platform")
            title = payload.get("title")
            body = payload.get("body")
            url = payload.get("url")
            
            try:
                print(f"\n[>] Processing thread: {title[:30]}... ({platform})")
            except UnicodeEncodeError:
                print(f"\n[>] Processing thread: {title[:30].encode('ascii', 'ignore').decode()}... ({platform})")
            
            # 1. Relevance Check
            is_relevant = self.relevance_agent.is_relevant(title, body, platform)
            
            if not is_relevant:
                print("   [x] Decision: IRRELEVANT. Archiving.")
                self.update_thread_status(thread_id, False, "irrelevant")
                continue
                
            print("   [v] Decision: RELEVANT. Drafting...")
            
            # 2. RAG Retrieval
            context = self.rag_store.retrieve_context(f"{title} {body}")
            
            # 3. Draft Comment
            draft = self.drafter_agent.draft_comment(platform, title, body, context)
            print(f"   [+] Draft Generated: {draft[:50]}...")
            
            self.update_thread_status(thread_id, True, "drafted")
            
            # 4. Route Output
            autonomous_mode = os.getenv("AUTONOMOUS_MODE", "false").lower() == "true"
            is_auto_approved = autonomous_mode and platform in ["devto_article", "github_gist", "medium", "hashnode"]
            
            contract_b = {
                "thread_id": thread_id,
                "platform": platform,
                "url": url,
                "is_relevant": True,
                "drafted_comment": draft,
                "review_status": "approved" if is_auto_approved else "pending",
                "feedback_note": None,
                "posting_type": "B" if platform in ["medium", "hashnode"] else ("A" if platform in ["devto_article", "github_gist"] else "M"),
                "approved_at": datetime.now(timezone.utc).isoformat() if is_auto_approved else None
            }
            
            if is_auto_approved:
                self.redis_client.lpush("posting_queue", json.dumps(contract_b))
                print(f"   [>>] AUTO-APPROVED. Pushed directly to posting_queue for {platform}.")
            else:
                self.redis_client.lpush("review_queue", json.dumps(contract_b))
                print("   [>>] Pushed to review_queue.")

if __name__ == "__main__":
    worker = LlmWorker()
    try:
        worker.run()
    except KeyboardInterrupt:
        print("\nWorker stopped.")
