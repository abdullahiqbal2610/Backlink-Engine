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
        """Decides if the thread is relevant to the company's backlink strategy."""
        
        if not self.client:
            print("[!] GEMINI_API_KEY not configured. Mocking relevance: True")
            return True
            
        company_name = os.getenv("COMPANY_NAME", "our company")
        company_desc = os.getenv("COMPANY_DESCRIPTION", "We provide technical solutions.")
        
        system_prompt = (
            "You are an AI assistant filtering forum threads for backlink opportunities. "
            f"Your company is {company_name}, which does the following: {company_desc}. "
            "Given the title and snippet of a post, reply ONLY with 'YES' if it's relevant to the company's niche or services, "
            "or 'NO' if it is completely unrelated."
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
