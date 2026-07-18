"""
dev.to Article Publisher — Type A (REST API)

Uses DEVTO_API_KEY to publish articles directly.
Returns the URL of the published article.
"""

import os
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv
from .base import PosterBase

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

class DevToArticlePoster(PosterBase):
    DEVTO_API_KEY_ENV = "DEVTO_API_KEY"
    BASE_URL = "https://dev.to/api/articles"

    @property
    def platform_name(self) -> str:
        return "devto_article"

    @classmethod
    def discover_feeds(cls) -> List[Dict]:
        """We do not scrape dev.to for API publishing. We just publish."""
        return []

    def post(self, url: str, content: str) -> tuple[bool, Optional[str]]:
        api_key = os.getenv(self.DEVTO_API_KEY_ENV)
        if not api_key:
            print("[-] DEVTO_API_KEY missing in .env")
            return False, None

        headers = {
            "api-key": api_key,
            "Content-Type": "application/json"
        }
        
        # We assume the content from the LLM contains a Markdown title on the first line (e.g. "# My Article Title")
        # Let's extract it.
        lines = content.strip().split("\n")
        title = "An insight on modern software development"
        if lines and lines[0].startswith("# "):
            title = lines[0].replace("# ", "").strip()
            content = "\n".join(lines[1:]).strip()
            
        payload = {
            "article": {
                "title": title,
                "published": True,
                "body_markdown": content,
                "tags": ["webdev", "programming", "technology"]
            }
        }

        print("[*] Submitting article to dev.to API (as Draft)...")
        try:
            resp = requests.post(self.BASE_URL, headers=headers, json=payload, timeout=15)
            if resp.status_code == 201:
                data = resp.json()
                live_url = data.get("url")
                print(f"[+] Dev.to article created! URL: {live_url}")
                return True, live_url
            else:
                print(f"[-] Dev.to API Error: {resp.status_code} - {resp.text}")
                return False, None
        except Exception as e:
            print(f"[-] Exception calling Dev.to API: {e}")
            return False, None
