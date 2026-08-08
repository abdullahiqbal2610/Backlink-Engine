"""
GitHub Discussions Poster — Type A (GraphQL API)

GitHub Discussions uses GitHub's GraphQL API v4.
We post comments to open discussions on relevant repos.
No Playwright needed — pure API calls.

Target repos for The Company: repos related to hiring, remote-work tools,
dev team management, etc.

Setup: Create a GitHub PAT (Personal Access Token) with 'repo' or 'public_repo' scope.
Add GITHUB_TOKEN=<your_token> to .env
"""

import os
import requests
from typing import List, Dict
from dotenv import load_dotenv
from .base import PosterBase

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"


def _check_token_scopes(token: str) -> list:
    """Returns list of OAuth scopes the token has."""
    try:
        resp = requests.get(
            "https://api.github.com/user",
            headers={"Authorization": f"bearer {token}"},
            timeout=5
        )
        scopes_header = resp.headers.get("X-OAuth-Scopes", "")
        return [s.strip() for s in scopes_header.split(",") if s.strip()]
    except Exception:
        return []

class GitHubDiscussionsPoster(PosterBase):

    @property
    def platform_name(self) -> str:
        return "github"

    @classmethod
    def discover_feeds(cls) -> List[Dict]:
        """
        GitHub doesn't have RSS for discussions, but repos have Atom feeds for commits.
        We discover via SERP: site:github.com/discussions "looking for developers" etc.
        These are registered as SERP targets in the discovery engine.
        """
        return []   # Discovery happens via SERP dorks, not RSS

    def _get_discussion_id(self, url: str, token: str) -> str | None:
        """
        Converts a GitHub Discussion URL to its GraphQL node ID.
        URL format: https://github.com/<owner>/<repo>/discussions/<number>
        """
        try:
            parts = url.rstrip("/").split("/")
            # [..., 'github.com', owner, repo, 'discussions', number]
            idx = parts.index("discussions")
            owner = parts[idx - 2]
            repo  = parts[idx - 1]
            number = int(parts[idx + 1])
        except (ValueError, IndexError) as e:
            print(f"[-] Cannot parse GitHub discussion URL: {url} — {e}")
            return None

        query = """
        query GetDiscussionId($owner: String!, $repo: String!, $number: Int!) {
          repository(owner: $owner, name: $repo) {
            discussion(number: $number) {
              id
            }
          }
        }
        """
        variables = {"owner": owner, "repo": repo, "number": number}
        headers = {
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
        }
        resp = requests.post(
            GITHUB_GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            try:
                return data["data"]["repository"]["discussion"]["id"]
            except (KeyError, TypeError):
                print(f"[-] Could not extract discussion ID from response: {data}")
                return None
        else:
            print(f"[-] GitHub GraphQL error {resp.status_code}: {resp.text}")
            return None

    def post(self, url: str, content: str) -> bool:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            print("[-] GITHUB_TOKEN not set in .env — cannot post to GitHub Discussions")
            return False

        # Check that the token has the right scope
        scopes = _check_token_scopes(token)
        if scopes and "repo" not in scopes and "public_repo" not in scopes:
            print(f"[-] GitHub token is missing 'repo' or 'public_repo' scope.")
            print(f"    Current scopes: {scopes}")
            print(f"    Fix: Go to github.com/settings/tokens → edit token → enable 'repo' scope")
            return False

        print(f"[*] GitHub Discussions API Poster starting for: {url}")

        discussion_id = self._get_discussion_id(url, token)
        if not discussion_id:
            print(f"[-] Could not resolve discussion node ID for: {url}")
            return False

        print(f"[*] Resolved discussion node ID: {discussion_id}")

        mutation = """
        mutation AddDiscussionComment($discussionId: ID!, $body: String!) {
          addDiscussionComment(input: {discussionId: $discussionId, body: $body}) {
            comment {
              id
              url
            }
          }
        }
        """
        variables = {"discussionId": discussion_id, "body": content}
        headers = {
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            resp = requests.post(
                GITHUB_GRAPHQL_URL,
                json={"query": mutation, "variables": variables},
                headers=headers,
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                if "errors" in data:
                    print(f"[-] GitHub GraphQL mutation error: {data['errors']}")
                    return False
                comment_url = data["data"]["addDiscussionComment"]["comment"]["url"]
                print(f"[+] GitHub Discussion comment posted! URL: {comment_url}")
                return True
            else:
                print(f"[-] GitHub API error {resp.status_code}: {resp.text}")
                return False
        except Exception as e:
            print(f"[-] GitHub Discussions Poster exception: {e}")
            return False


if __name__ == "__main__":
    poster = GitHubDiscussionsPoster()
    print("Platform:", poster.platform_name)
    print("Feeds:", poster.discover_feeds())
