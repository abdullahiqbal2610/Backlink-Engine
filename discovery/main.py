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
    serp = SerpFetcher()

    # ── SERP Targets: 3 per platform, balanced across all 4 platforms ──
    # Each platform gets equal queries → equal representation in final queue
    serp_targets_by_platform = {
        "devto_article": [
            {"site": "stackoverflow.com",        "keyword": "python microservices architecture best practices"},
            {"site": "reddit.com/r/webdev",      "keyword": "how to implement robust authentication in Next.js"},
            {"site": "news.ycombinator.com",     "keyword": "optimizing postgres database queries"},
        ],
        "github_gist": [
            {"site": "stackoverflow.com",        "keyword": "python asyncio rate limiter decorator example"},
            {"site": "stackoverflow.com",        "keyword": "react custom hook for localstorage syncing"},
            {"site": "reddit.com/r/programming", "keyword": "golang concurrent worker pool implementation"},
        ],
        "medium": [
            {"site": "news.ycombinator.com",     "keyword": "how AI is replacing software engineers 2026"},
            {"site": "reddit.com/r/programming", "keyword": "future of web development frameworks"},
            {"site": "reddit.com/r/SaaS",        "keyword": "building an AI agent for customer support"},
        ],
        "hashnode": [
            {"site": "news.ycombinator.com",     "keyword": "scaling postgres with read replicas"},
            {"site": "stackoverflow.com",        "keyword": "react server components best practices"},
            {"site": "reddit.com/r/programming", "keyword": "rust versus go for backend microservices"},
        ],
    }

    print(f"[*] Running SERP discovery across {sum(len(v) for v in serp_targets_by_platform.values())} query target(s)...")

    # Fetch per platform first, then interleave (round-robin) so queue is balanced
    items_by_platform = {}
    for platform, queries in serp_targets_by_platform.items():
        items_by_platform[platform] = []
        for q in queries:
            query = serp.generate_dork(q["site"], q["keyword"])
            results = serp.fetch_results(query, max_results=8)
            for item in results:
                item["_target_platform"] = platform
                item["_target_scrape_type"] = 2
                items_by_platform[platform].append(item)
        random.shuffle(items_by_platform[platform])
        print(f"[*] {platform}: {len(items_by_platform[platform])} items found")

    # Round-robin interleave: pick 1 from each platform in turn
    all_discovered = []
    platforms = list(items_by_platform.keys())
    max_len = max(len(v) for v in items_by_platform.values())
    for i in range(max_len):
        for p in platforms:
            lst = items_by_platform[p]
            if i < len(lst):
                all_discovered.append(lst[i])

    print(f"[*] Total {len(all_discovered)} items queued in round-robin order across {len(platforms)} platforms")

    for item in all_discovered:
        pipeline.process_item(item, platform=item["_target_platform"], scrape_type=item["_target_scrape_type"])

    pipeline.close()
    print("=== Discovery Engine Run Complete ===")


if __name__ == "__main__":
    run_discovery()
