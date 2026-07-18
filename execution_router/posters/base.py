from abc import ABC, abstractmethod
from typing import List, Dict

class PosterBase(ABC):
    """
    Abstract base class for all platform posters.
    
    To add a new platform, create a new file in this directory that:
    1. Inherits from PosterBase
    2. Implements the `post()` method
    3. Implements the `discover_feeds()` class method
    4. Adds itself to execution_router/worker.py posters dict
    5. Adds its feeds to discovery/main.py rss_targets list
    
    That's it. The entire rest of the system (LLM, Queue, Dashboard) is shared.
    """
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """The canonical platform identifier (lowercase, no spaces). e.g. 'reddit', 'devto'"""
        pass
    
    @classmethod
    @abstractmethod
    def discover_feeds(cls) -> List[Dict]:
        """
        Returns a list of discovery feed configs for this platform.
        Each dict must have: { 'url': str, 'platform': str, 'scrape_type': int }
        This allows the discovery engine to auto-register feeds just by importing the poster.
        """
        pass
    
    @abstractmethod
    def post(self, url: str, content: str) -> tuple[bool, str | None]:
        """
        Executes the posting action.
        Returns (True, "https://live-url") if successful, or (False, None) on failure.
        """
        pass
