import feedparser
from typing import List, Dict

class RssFetcher:
    def __init__(self):
        pass

    def fetch_feed(self, feed_url: str) -> List[Dict]:
        """Fetches and parses an RSS feed."""
        print(f"[*] Fetching RSS Feed: {feed_url}")
        results = []
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                results.append({
                    "title": entry.title,
                    "url": entry.link,
                    "snippet": entry.get("summary", ""),
                    "published": entry.get("published", "")
                })
        except Exception as e:
            print(f"[-] Error fetching RSS feed {feed_url}: {e}")
        return results

if __name__ == "__main__":
    # Quick test
    fetcher = RssFetcher()
    # Using a generic Reddit RSS feed for testing
    res = fetcher.fetch_feed("https://www.reddit.com/r/SaaS/.rss")
    for r in res[:3]:
        print(r)
