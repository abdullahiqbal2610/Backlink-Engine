"""
Discovery Engine — Main

Reads RSS/API feeds from all registered platform posters (via DISCOVERY_FEEDS)
and pushes new threads into the Redis discovery_queue.

Adding a new platform: implement poster.discover_feeds() in its poster class
and register it in execution_router/posters/__init__.py. Nothing here changes.
"""

import os
import sys
import time
import random

# Allow importing from sibling packages
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rss_fetcher  import RssFetcher
from serp_fetcher import SerpFetcher
from pipeline     import DiscoveryPipeline

# Import aggregated feed list from the poster registry (plug-and-play)
# from execution_router.posters import DISCOVERY_FEEDS
DISCOVERY_FEEDS = [] # Hardcoded empty to avoid Playwright dependency in LLM worker

def run_discovery():
    print("=== Starting Discovery Engine ===")

    pipeline = DiscoveryPipeline()
    rss  = RssFetcher()
    serp = SerpFetcher()

    # ── 1. RSS / API Feed Discovery (auto-aggregated from all poster modules) ──
    rss_targets = DISCOVERY_FEEDS   # Comes from every platform's discover_feeds()

    print(f"[*] Running RSS discovery across {len(rss_targets)} feed(s)...")

    # TEMPORARILY DISABLED to prioritize SERP high-value targets
    # for target in rss_targets:
    #     if target.get("scrape_type", 1) == 1:
    #         items = rss.fetch_feed(target["url"])
    #         for item in items:
    #             pipeline.process_item(item, platform=target["platform"], scrape_type=1)

    # ── 2. SERP / Dork Discovery (manually curated high-value queries) ──
    serp_targets = [
        # Dev.to Article Targets
        {"site": "stackoverflow.com",        "keyword": "python microservices architecture best practices", "platform": "devto_article", "scrape_type": 2},
        {"site": "news.ycombinator.com",     "keyword": "fastapi vs django performance 2027",               "platform": "devto_article", "scrape_type": 2},
        {"site": "reddit.com/r/webdev",      "keyword": "how to implement robust authentication in Next.js", "platform": "devto_article", "scrape_type": 2},
        {"site": "stackoverflow.com",        "keyword": "designing scalable REST APIs",                     "platform": "devto_article", "scrape_type": 2},
        {"site": "news.ycombinator.com",     "keyword": "optimizing postgres database queries",             "platform": "devto_article", "scrape_type": 2},
        
        # GitHub Gist Targets
        {"site": "stackoverflow.com",        "keyword": "python asyncio rate limiter decorator example",    "platform": "github_gist",   "scrape_type": 2},
        {"site": "news.ycombinator.com",     "keyword": "python clean architecture repository pattern",     "platform": "github_gist",   "scrape_type": 2},
        {"site": "stackoverflow.com",        "keyword": "react custom hook for localstorage syncing",       "platform": "github_gist",   "scrape_type": 2},
        {"site": "reddit.com/r/programming", "keyword": "golang concurrent worker pool implementation",     "platform": "github_gist",   "scrape_type": 2},
        {"site": "stackoverflow.com",        "keyword": "docker compose local development setup for nodejs", "platform": "github_gist",   "scrape_type": 2},
        
        # Medium Targets
        {"site": "news.ycombinator.com",     "keyword": "how AI replaces software engineers 2026",          "platform": "medium",        "scrape_type": 2},
        {"site": "reddit.com/r/programming", "keyword": "future of web development frameworks",             "platform": "medium",        "scrape_type": 2},
        {"site": "news.ycombinator.com",     "keyword": "why we moved from microservices back to monolith", "platform": "medium",        "scrape_type": 2},
        {"site": "reddit.com/r/SaaS",        "keyword": "building an AI agent for customer support",        "platform": "medium",        "scrape_type": 2},
        {"site": "news.ycombinator.com",     "keyword": "the real cost of cloud infrastructure in 2025",    "platform": "medium",        "scrape_type": 2},
        
        # Hashnode Targets
        {"site": "news.ycombinator.com",     "keyword": "scaling postgres database replication",            "platform": "hashnode",      "scrape_type": 2},
        {"site": "stackoverflow.com",        "keyword": "react server components best practices",           "platform": "hashnode",      "scrape_type": 2},
        {"site": "reddit.com/r/programming", "keyword": "rust versus go for backend microservices",         "platform": "hashnode",      "scrape_type": 2},
    ]

    print(f"[*] Running SERP discovery across {len(serp_targets)} query target(s)...")

    all_discovered_items = []
    
    for target in serp_targets:
        query = serp.generate_dork(target["site"], target["keyword"])
        items = serp.fetch_results(query, max_results=10)
        for item in items:
            # Attach target info to the item so we can process it later
            item["_target_platform"] = target["platform"]
            item["_target_scrape_type"] = target["scrape_type"]
            all_discovered_items.append(item)
            
    # Shuffle the items so the LLM pipeline gets a healthy mix of platforms
    print(f"[*] Discovered {len(all_discovered_items)} items. Shuffling before queueing...")
    random.shuffle(all_discovered_items)
    
    # Now process them in randomized order
    for item in all_discovered_items:
        pipeline.process_item(item, platform=item["_target_platform"], scrape_type=item["_target_scrape_type"])

    pipeline.close()
    print("=== Discovery Engine Run Complete ===")


if __name__ == "__main__":
    run_discovery()
