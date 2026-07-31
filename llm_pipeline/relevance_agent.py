import os
from google import genai
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

class RelevanceAgent:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key and "your_" not in self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    def is_relevant(self, title: str, snippet: str, platform: str) -> bool:
        """Decides if the thread is relevant to Gaper.io's backlink strategy."""
        
        if not self.client:
            print("[!] GEMINI_API_KEY not configured. Mocking relevance: True")
            return True
            
        system_prompt = (
            "You are an AI assistant filtering forum threads for backlink opportunities. "
            "Your company is Gaper.io, which provides top-tier remote engineering talent to startups. "
            "Given the title and snippet of a post, reply ONLY with 'YES' if it's relevant to software engineering, "
            "hiring developers, startups, or SaaS, or 'NO' if it is completely unrelated."
        )
        
        user_prompt = f"{system_prompt}\n\nPlatform: {platform}\nTitle: {title}\nSnippet: {snippet}"
        
        try:
            response = self.client.models.generate_content(
                model="gemini-flash-lite-latest",
                contents=user_prompt
            )
            decision = response.text.strip().upper()
            return "YES" in decision
        except Exception as e:
            print(f"[-] Error calling LLM in RelevanceAgent: {e}")
            return True

if __name__ == "__main__":
    agent = RelevanceAgent()
    print("Is relevant?", agent.is_relevant("Need to hire a React developer", "Our startup is growing fast...", "reddit"))
