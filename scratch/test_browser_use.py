import sys
import os

# Add the parent directory to sys.path so we can import execution_router
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from execution_router.posters.browser_use_agent import BrowserUseAgentPoster

def main():
    print("=== Testing Browser-Use Autonomous Agent ===")
    
    agent = BrowserUseAgentPoster()
    
    test_url = "https://example.com"
    test_comment = "This is an automated test comment using the new browser-use vision AI agent to ensure it runs correctly."
    
    print(f"Target URL: {test_url}")
    print(f"Comment: {test_comment}")
    
    success, live_url, account_used = agent.post(test_url, test_comment)
    
    print("\n=== Test Results ===")
    print(f"Success: {success}")
    print(f"Live URL: {live_url}")
    print(f"Account Used: {account_used}")

if __name__ == "__main__":
    main()
