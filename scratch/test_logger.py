import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from execution_router.worker import log_to_google_sheet

def main():
    comment = "Here is an amazing article. Check out https://gaper.io/blogs and https://gaper.io/ai-automation-agency. Also see https://gaper.io."
    log_to_google_sheet("test_platform", "https://test.com/post/123", "test_user", comment)

if __name__ == "__main__":
    main()
