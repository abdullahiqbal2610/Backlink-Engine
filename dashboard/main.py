import os
import json
import redis
import psycopg2
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv, set_key

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

app = FastAPI(title="Gaper Intern Panel Review")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(redis_url)

def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "backlink_engine"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432")
    )

class ReviewAction(BaseModel):
    thread_id: str
    final_comment: str
    feedback: Optional[str] = None

class ToggleAction(BaseModel):
    enabled: bool

@app.post("/api/upload-cookies/{platform}")
async def upload_cookies(platform: str, file: UploadFile = File(...)):
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Only JSON files are allowed")
    
    content = await file.read()
    try:
        json.loads(content) # validate JSON
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
        
    # Store JSON string in Redis
    try:
        r.set(f"cookies_{platform}", content.decode('utf-8'))
        return {"status": "success", "message": f"{platform} cookies uploaded to Redis successfully!"}
    except Exception as e:
        # Fallback to local disk for local testing if Redis fails
        save_path = os.path.join(os.path.dirname(__file__), '..', 'browser_profiles', f"{platform}_cookies.json")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        with open(save_path, "wb") as f:
            f.write(content)
            
        return {"status": "success", "message": f"{platform} cookies saved locally! (Redis fallback)"}

@app.get("/api/health")
def health_check():
    health = {"redis": False, "postgres": False}
    try:
        r.ping()
        health["redis"] = True
    except:
        pass
        
    try:
        conn = get_db_connection()
        conn.close()
        health["postgres"] = True
    except:
        pass
        
    return health

@app.get("/api/autonomous/status")
def get_autonomous_status():
    status = os.getenv("AUTONOMOUS_MODE", "false").lower() == "true"
    return {"enabled": status}

@app.post("/api/autonomous/toggle")
def toggle_autonomous(action: ToggleAction):
    val = "true" if action.enabled else "false"
    set_key(dotenv_path, "AUTONOMOUS_MODE", val)
    os.environ["AUTONOMOUS_MODE"] = val
    return {"status": "success", "enabled": action.enabled}

@app.get("/api/reviews")
def get_reviews():
    """Fetch all pending reviews from the review_queue"""
    items = r.lrange("review_queue", 0, -1)
    reviews = []
    for item in items:
        try:
            reviews.append(json.loads(item.decode("utf-8")))
        except Exception:
            pass
    return {"reviews": reviews}

def remove_from_queue(thread_id: str):
    """Helper to remove an item from review_queue"""
    items = r.lrange("review_queue", 0, -1)
    for item in items:
        data = json.loads(item.decode("utf-8"))
        if data.get("thread_id") == thread_id:
            r.lrem("review_queue", 1, item)
            return data
    return None

@app.post("/api/reviews/approve")
def approve_review(action: ReviewAction):
    """Approves a review and pushes to posting_queue (Contract C)"""
    data = remove_from_queue(action.thread_id)
    if not data:
        raise HTTPException(status_code=404, detail="Review not found in queue")
    
    # Contract C Payload for Phase 3 (Posting Engine)
    contract_c = {
        "thread_id": data["thread_id"],
        "platform": data["platform"],
        "url": data["url"],
        "final_comment": action.final_comment,
        "posting_type": data.get("posting_type", "A")
    }
    
    r.lpush("posting_queue", json.dumps(contract_c))
    
    # Update DB Status
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE threads SET status = 'approved', updated_at = CURRENT_TIMESTAMP WHERE thread_id = %s", (action.thread_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")
        
    return {"status": "success", "message": "Moved to posting queue."}

@app.post("/api/reviews/reject")
def reject_review(action: ReviewAction):
    """Rejects a review"""
    data = remove_from_queue(action.thread_id)
    if not data:
        raise HTTPException(status_code=404, detail="Review not found in queue")
        
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE threads SET status = 'rejected', updated_at = CURRENT_TIMESTAMP WHERE thread_id = %s", (action.thread_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")
        
    return {"status": "success", "message": "Rejected and archived."}

@app.post("/api/reviews/rewrite")
def rewrite_review(action: ReviewAction):
    """Sends back to drafting phase (Discovery Queue) with feedback"""
    data = remove_from_queue(action.thread_id)
    if not data:
        raise HTTPException(status_code=404, detail="Review not found in queue")
        
    # In a real scenario, this goes back to the DrafterAgent with feedback.
    # For now we simulate this by marking it 'needs_rewrite'
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE threads SET status = 'needs_rewrite', updated_at = CURRENT_TIMESTAMP WHERE thread_id = %s", (action.thread_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")
        
    return {"status": "success", "message": "Sent for rewrite."}

@app.get("/api/published")
def get_published_links():
    """Fetch successfully posted live backlinks from the database"""
    results = []
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.post_url, p.posted_at, t.platform, t.title 
                FROM post_results p
                JOIN threads t ON p.thread_id = t.thread_id
                WHERE p.post_status = 'success' AND p.post_url IS NOT NULL
                ORDER BY p.posted_at DESC
                LIMIT 100
            """)
            rows = cur.fetchall()
            for row in rows:
                results.append({
                    "url": row[0],
                    "posted_at": row[1].isoformat() if row[1] else None,
                    "platform": row[2],
                    "title": row[3]
                })
        conn.close()
    except Exception as e:
        print(f"DB Error fetching published links: {e}")
        return {"status": "error", "message": str(e)}
        
    return {"published": results}

@app.get("/api/history/{status}")
def get_history(status: str):
    """Fetch history of approved or rejected threads"""
    if status not in ["approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    results = []
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT title, url, platform, updated_at 
                FROM threads 
                WHERE status = %s
                ORDER BY updated_at DESC
                LIMIT 50
            """, (status,))
            rows = cur.fetchall()
            for row in rows:
                results.append({
                    "title": row[0],
                    "url": row[1],
                    "platform": row[2],
                    "updated_at": row[3].isoformat() if row[3] else None
                })
        conn.close()
    except Exception as e:
        print(f"DB Error fetching history: {e}")
        return {"status": "error", "message": str(e)}
        
    return {"history": results}

@app.get("/api/analytics")
def get_analytics():
    """Fetch high-level analytics for the dashboard"""
    stats = {
        "total_discovered": 0,
        "total_approved": 0,
        "total_rejected": 0,
        "total_published": 0,
        "platform_breakdown": {}
    }
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Basic counts
            cur.execute("SELECT status, COUNT(*) FROM threads GROUP BY status")
            for row in cur.fetchall():
                if row[0] == "approved": stats["total_approved"] = row[1]
                elif row[0] == "rejected": stats["total_rejected"] = row[1]
                stats["total_discovered"] += row[1]
                
            # Published count
            cur.execute("SELECT COUNT(*) FROM post_results WHERE post_status = 'success'")
            stats["total_published"] = cur.fetchone()[0]
            
            # Platform breakdown for published
            cur.execute("""
                SELECT t.platform, COUNT(*) 
                FROM post_results p 
                JOIN threads t ON p.thread_id = t.thread_id 
                WHERE p.post_status = 'success' 
                GROUP BY t.platform
            """)
            for row in cur.fetchall():
                stats["platform_breakdown"][row[0]] = row[1]
                
        conn.close()
    except Exception as e:
        print(f"DB Error fetching analytics: {e}")
        return {"status": "error", "message": str(e)}
        
    return stats

# Mount static files for the frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
