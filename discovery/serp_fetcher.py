import os
import requests
import json
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

class SerpFetcher:
    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY")
        if not self.api_key:
            print("[!] SERPER_API_KEY not found in .env")

    def generate_dork(self, site: str, keyword: str) -> str:
        """Generates a search query for a specific site and keyword."""
        return f'site:{site} {keyword}'

    def fetch_results(self, query: str, max_results: int = 10) -> List[Dict]:
        """Fetches SERP results for the given query using Serper API."""
        print(f"[*] Searching Serper for query: {query}")
        results = []
        
        if not self.api_key:
            return results

        url = "https://google.serper.dev/search"
        payload = json.dumps({
          "q": query,
          "num": max_results
        })
        headers = {
          'X-API-KEY': self.api_key,
          'Content-Type': 'application/json'
        }

        try:
            response = requests.request("POST", url, headers=headers, data=payload)
            response.raise_for_status()
            data = response.json()
            
            organic_results = data.get("organic", [])
            for r in organic_results:
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "snippet": r.get("snippet", "")
                })
        except Exception as e:
            print(f"[-] Error fetching SERP: {e}")
            
        return results

if __name__ == "__main__":
    # Quick test
    fetcher = SerpFetcher()
    query = fetcher.generate_dork("stackoverflow.com", "python microservices architecture best practices")
    res = fetcher.fetch_results(query, max_results=3)
    for r in res:
        print(r)
