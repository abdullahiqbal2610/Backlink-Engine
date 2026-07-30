import os
from google import genai
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

class RelevanceAgent:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if self.api_key and "your_" not in self.api_key:
            from groq import Groq
            self.client = Groq(api_key=self.api_key)
        else:
            self.client = None

    def is_relevant(self, title: str, snippet: str, platform: str) -> bool:
        """Decides if the thread is relevant to Gaper.io's backlink strategy."""
        
        if not self.client:
            print("[!] GROQ_API_KEY not configured. Mocking relevance: True")
            return True
            
        system_prompt = (
            "You are an AI assistant filtering forum threads for backlink opportunities. "
            "Your company is Gaper.io, which provides top-tier remote engineering talent to startups. "
            "Given the title and snippet of a post, reply ONLY with 'YES' if it's relevant to software engineering, "
            "hiring developers, startups, or SaaS, or 'NO' if it is completely unrelated."
        )
        
        user_prompt = f"Platform: {platform}\nTitle: {title}\nSnippet: {snippet}"
        
        try:
            response = self.client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0
            )
            decision = response.choices[0].message.content.strip().upper()
            return "YES" in decision
        except Exception as e:
            print(f"[-] Error calling LLM in RelevanceAgent: {e}")
            return True

if __name__ == "__main__":
    agent = RelevanceAgent()
    print("Is relevant?", agent.is_relevant("Need to hire a React developer", "Our startup is growing fast...", "reddit"))
