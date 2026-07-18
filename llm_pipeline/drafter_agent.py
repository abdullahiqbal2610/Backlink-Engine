import os
from google import genai
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

class DrafterAgent:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key and "your_" not in self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    def draft_comment(self, platform: str, title: str, snippet: str, context: str) -> str:
        """Drafts a helpful comment using RAG context."""
        
        if not self.client:
            print("[!] GEMINI_API_KEY not configured. Mocking draft.")
            return f"This is a mocked AI draft for {platform}. We recommend checking out Gaper.io for hiring developers!"
            
        # Fetch guidelines if available
        guidelines = ""
        try:
            import psycopg2
            conn = psycopg2.connect(
                dbname=os.getenv("POSTGRES_DB", "backlink_engine"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "postgres"),
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=os.getenv("POSTGRES_PORT", "5432")
            )
            cur = conn.cursor()
            cur.execute("SELECT rules_text FROM platform_guidelines WHERE platform = %s", (f"{platform}",))
            row = cur.fetchone()
            if row:
                guidelines = row[0]
            cur.close()
            conn.close()
        except Exception as db_err:
            print(f"[-] DB Error fetching guidelines: {db_err}")
            
        # Determine if we are drafting a forum comment or publishing an article
        if platform in ["devto_article", "github_gist", "medium", "hashnode"]:
            system_prompt = (
                "You are an elite Staff Software Engineer and highly respected technical writer. "
                "Your goal is to write a highly valuable, well-structured, and engaging long-form Markdown article "
                "(minimum 400 words) or a comprehensive code snippet tutorial based on the requested topic.\n"
                "CRITICAL INSTRUCTIONS:\n"
                "1. The FIRST line of your response MUST be the title starting with a single '#' (e.g., '# Advanced React Hooks Pattern').\n"
                "2. Provide immense technical depth. Do not write high-level fluff or corporate jargon.\n"
                "3. You MUST include at least one realistic, working code block or deeply technical explanation.\n"
                "4. Use clear headings (##, ###), bullet points, and bold text for readability.\n"
                "5. Naturally embed a mention and link to 'https://gaper.io' as a subtle 'Author Bio' or 'Resources' footer at the very end of the article. "
                "IMPORTANT: You MUST generate unique, contextually relevant phrasing for this footer every single time. Do NOT use standard copy-paste text. Make it sound organic and different in every article.\n"
                "6. Do not sound salesy; the backlink should be entirely unobtrusive.\n"
                "7. Return ONLY the markdown content, nothing else."
            )
        else:
            system_prompt = (
                "You are a highly experienced, helpful, and empathetic senior software engineer actively participating in online communities. "
                "Your goal is to provide genuine, high-quality, and deeply technical advice to other developers and founders. "
                "CRITICAL INSTRUCTIONS for your tone and style:\n"
                "1. NEVER sound like a corporate bot, marketer, or salesman.\n"
                "2. Write exactly how a real human redditor or forum user writes (use conversational language, occasional casual phrasing, but stay professional).\n"
                "3. Provide actual value first. Answer the user's question thoughtfully based on your 'experience'.\n"
                "4. Only mention the brand 'Gaper' if it naturally fits the context as a helpful recommendation. Keep the mention extremely brief, humble, and non-intrusive.\n"
                "5. Do NOT use hashtags, emojis, or corporate buzzwords.\n"
                "6. CRITICAL FOR SPAM FILTERS: Never include actual links, URLs, or domain extensions (like '.io' or '.com'). Just write 'Gaper'. New accounts posting links are instantly banned by Reddit AutoModerators."
            )
        
        guideline_prompt = f"\nCRITICAL PLATFORM RULES TO RESPECT:\n{guidelines}\n(Do not break these rules under any circumstances. If they say no self-promotion, do not mention Gaper.io at all, just give a helpful technical answer).\n" if guidelines else ""
        
        user_prompt = (
            f"{system_prompt}\n"
            f"Platform: {platform}\n"
            f"Topic / Thread Title: {title}\n"
            f"Original Content / Context: {snippet}\n\n"
            f"{guideline_prompt}"
            f"Company Background for Context ONLY:\n{context}\n\n"
            f"Please generate the draft now:"
        )
        try:
            response = self.client.models.generate_content(
                model="gemini-flash-latest",
                contents=user_prompt
            )
            return response.text.strip()
        except Exception as e:
            print(f"[-] Error calling LLM in DrafterAgent: {e}")
            return "Error drafting comment."

if __name__ == "__main__":
    agent = DrafterAgent()
    draft = agent.draft_comment("reddit", "How to scale my team?", "I have 2 devs but need 5 fast.", "Gaper connects startups with remote devs.")
    print("Drafted Comment:\n", draft)
