# Poster registry — auto-loads all available platform posters.
# To add a new platform, just import it here and add to POSTER_REGISTRY.

from .reddit           import RedditPoster
from .hackernews       import HackerNewsPoster
from .devto            import DevToPoster
from .indiehackers     import IndieHackersPoster
from .github_discussions import GitHubDiscussionsPoster
from .devto_article    import DevToArticlePoster
from .github_gist      import GithubGistPoster
from .medium           import MediumPoster
from .hashnode         import HashnodePoster

# ============================================================
# POSTER_REGISTRY: maps platform name -> poster class instance
# The execution router uses this to dispatch posts automatically.
# ============================================================
POSTER_REGISTRY = {
    "reddit":        RedditPoster(),
    "hackernews":    HackerNewsPoster(),
    "devto":         DevToPoster(),
    "indiehackers":  IndieHackersPoster(),
    "github":        GitHubDiscussionsPoster(),
    "devto_article": DevToArticlePoster(),
    "github_gist":   GithubGistPoster(),
    "medium":        MediumPoster(),
    "hashnode":      HashnodePoster(),
}

# ============================================================
# DISCOVERY_FEEDS: aggregated list of all RSS/API feed targets
# from every registered poster. Discovery engine reads this.
# ============================================================
DISCOVERY_FEEDS = []
for _poster_class in [RedditPoster, HackerNewsPoster, DevToPoster, IndieHackersPoster, GitHubDiscussionsPoster, DevToArticlePoster, GithubGistPoster, HashnodePoster]:
    DISCOVERY_FEEDS.extend(_poster_class.discover_feeds())
