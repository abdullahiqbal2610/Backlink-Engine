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

# Allow importing from sibling packages
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rss_fetcher  import RssFetcher
from serp_fetcher import SerpFetcher
from pipeline     import DiscoveryPipeline

# Import aggregated feed list from the poster registry (plug-and-play)
from execution_router.posters import DISCOVERY_FEEDS


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
        {"site": "stackoverflow.com",        "keyword": "building custom LLM wrappers in Python",          "platform": "devto_article", "scrape_type": 2},
        {"site": "news.ycombinator.com",     "keyword": "migrating from Next.js pages to app router",      "platform": "devto_article", "scrape_type": 2},
        {"site": "reddit.com/r/webdev",      "keyword": "integrating Stripe subscriptions for SaaS",       "platform": "devto_article", "scrape_type": 2},
        {"site": "stackoverflow.com",        "keyword": "handling WebSockets at scale in Node.js",         "platform": "devto_article", "scrape_type": 2},
        {"site": "news.ycombinator.com",     "keyword": "GraphQL federation Apollo vs Hasura",             "platform": "devto_article", "scrape_type": 2},
        {"site": "dev.to",                   "keyword": "building internal tools with Retool and SQL",     "platform": "devto_article", "scrape_type": 2},
        {"site": "reddit.com/r/reactjs",     "keyword": "Zustand vs Redux Toolkit for complex apps",       "platform": "devto_article", "scrape_type": 2},
        {"site": "stackoverflow.com",        "keyword": "deploying FastAPI on AWS Lambda Serverless",      "platform": "devto_article", "scrape_type": 2},
        
        # GitHub Gist Targets
        {"site": "stackoverflow.com",        "keyword": "python script for scraping dynamic sites playwright", "platform": "github_gist", "scrape_type": 2},
        {"site": "news.ycombinator.com",     "keyword": "React custom hook for infinite scrolling API",    "platform": "github_gist", "scrape_type": 2},
        {"site": "stackoverflow.com",        "keyword": "PostgreSQL optimize full text search query",      "platform": "github_gist", "scrape_type": 2},
        {"site": "reddit.com/r/programming", "keyword": "Go language goroutine worker pool pattern",       "platform": "github_gist", "scrape_type": 2},
        {"site": "stackoverflow.com",        "keyword": "Docker multi stage build for Python poetry",      "platform": "github_gist", "scrape_type": 2},
        {"site": "gist.github.com",          "keyword": "Terraform AWS RDS Postgres setup snippet",        "platform": "github_gist", "scrape_type": 2},
        {"site": "gist.github.com",          "keyword": "Kubernetes deployment YAML for Node microservice", "platform": "github_gist", "scrape_type": 2},
        
        # Medium Targets
        {"site": "news.ycombinator.com",     "keyword": "why finding good senior remote developers is hard", "platform": "medium", "scrape_type": 2},
        {"site": "reddit.com/r/programming", "keyword": "how to properly interview AI engineers",          "platform": "medium", "scrape_type": 2},
        {"site": "news.ycombinator.com",     "keyword": "lessons learned scaling a B2B SaaS startup",      "platform": "medium", "scrape_type": 2},
        {"site": "reddit.com/r/SaaS",        "keyword": "hiring remote vs local engineers in 2026",        "platform": "medium", "scrape_type": 2},
        {"site": "news.ycombinator.com",     "keyword": "building AI automation agency workflows",         "platform": "medium", "scrape_type": 2},
        {"site": "medium.com",               "keyword": "software development outsourcing best practices", "platform": "medium", "scrape_type": 2},
        {"site": "medium.com",               "keyword": "how to build a remote engineering culture",       "platform": "medium", "scrape_type": 2},
        {"site": "medium.com",               "keyword": "the impact of generative AI on software testing", "platform": "medium", "scrape_type": 2},
        {"site": "reddit.com/r/devops",      "keyword": "why we chose Kubernetes over Docker Swarm",       "platform": "medium", "scrape_type": 2},
        
        # Hashnode Targets
        {"site": "news.ycombinator.com",     "keyword": "caching strategies for high traffic web apps",    "platform": "hashnode", "scrape_type": 2},
        {"site": "stackoverflow.com",        "keyword": "React context API vs prop drilling",              "platform": "hashnode", "scrape_type": 2},
        {"site": "reddit.com/r/programming", "keyword": "Python vs Go for building CLI tools",             "platform": "hashnode", "scrape_type": 2},
        {"site": "hashnode.com",             "keyword": "securing REST APIs with JWT and OAuth",           "platform": "hashnode", "scrape_type": 2},
        {"site": "hashnode.com",             "keyword": "building a rag pipeline with LangChain",          "platform": "hashnode", "scrape_type": 2},
        
        # Open Discovery Targets (Unknown Domains)
        {"site": None, "keyword": '"write for us" "SaaS growth"', "platform": "unknown", "scrape_type": 4},
        {"site": None, "keyword": '"submit a guest post" "remote work culture"', "platform": "unknown", "scrape_type": 4},
        {"site": None, "keyword": '"contribute an article" "LLM development"', "platform": "unknown", "scrape_type": 4},
        {"site": None, "keyword": '"guest post guidelines" "startup funding tech"', "platform": "unknown", "scrape_type": 4},
        {"site": None, "keyword": '"write for us" "generative AI"', "platform": "unknown", "scrape_type": 4},
        {"site": None, "keyword": '"submit an article" "CTO advice"', "platform": "unknown", "scrape_type": 4},
    ]

    print(f"[*] Running SERP discovery across {len(serp_targets)} query target(s)...")

    for target in serp_targets:
        query = serp.generate_dork(target["site"], target["keyword"])
        items = serp.fetch_results(query, max_results=10)
        for item in items:
            pipeline.process_item(item, platform=target["platform"], scrape_type=target["scrape_type"])

    pipeline.close()
    print("=== Discovery Engine Run Complete ===")


if __name__ == "__main__":
    run_discovery()
