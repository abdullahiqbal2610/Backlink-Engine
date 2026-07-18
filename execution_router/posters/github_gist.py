"""
GitHub Gist Publisher — Type A (REST API)

Uses GITHUB_TOKEN to publish code snippets / gists directly.
Returns the HTML URL of the published gist.
"""

import os
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv
from .base import PosterBase

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

class GithubGistPoster(PosterBase):
    GITHUB_TOKEN_ENV = "GITHUB_TOKEN"
    BASE_URL = "https://api.github.com/gists"

    @property
    def platform_name(self) -> str:
        return "github_gist"

    @classmethod
    def discover_feeds(cls) -> List[Dict]:
        """We do not scrape for Gists. We just publish."""
        return []

    def post(self, url: str, content: str) -> tuple[bool, Optional[str]]:
        token = os.getenv(self.GITHUB_TOKEN_ENV)
        if not token:
            print("[-] GITHUB_TOKEN missing in .env")
            return False, None

        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        
        # We assume the content from the LLM contains a Markdown title on the first line
        lines = content.strip().split("\n")
        title = "Gaper Snippet"
        if lines and lines[0].startswith("# "):
            title = lines[0].replace("# ", "").strip()
            content = "\n".join(lines[1:]).strip()
            
        # Create a safe filename from the title
        safe_title = "".join(c if c.isalnum() else "_" for c in title.lower())
        filename = f"{safe_title[:30]}_gaper.md"
        if not filename.endswith(".md"):
            filename += ".md"
            
        payload = {
            "description": title,
            "public": True,
            "files": {
                filename: {
                    "content": content
                }
            }
        }

        print("[*] Submitting snippet to GitHub Gists...")
        try:
            resp = requests.post(self.BASE_URL, headers=headers, json=payload, timeout=15)
            if resp.status_code == 201:
                data = resp.json()
                live_url = data.get("html_url")
                print(f"[+] GitHub Gist created! URL: {live_url}")
                return True, live_url
            else:
                print(f"[-] GitHub API Error: {resp.status_code} - {resp.text}")
                return False, None
        except Exception as e:
            print(f"[-] Exception calling GitHub API: {e}")
            return False, None
