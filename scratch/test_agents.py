import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'llm_pipeline'))

from relevance_agent import RelevanceAgent
from drafter_agent import DrafterAgent

def test_agents():
    print("Testing Relevance Agent...")
    rel_agent = RelevanceAgent()
    is_rel = rel_agent.is_relevant("Need help scaling", "Our company is looking for ways to scale our software engineering team...", "reddit")
    print(f"Is Relevant? {is_rel}")
    
    print("\nTesting Drafter Agent...")
    draft_agent = DrafterAgent()
    draft = draft_agent.draft_comment("reddit", "How to scale my team?", "I have 2 devs but need 5 fast.", "We connect startups with remote devs.")
    print(f"Draft:\n{draft}")

if __name__ == '__main__':
    test_agents()
