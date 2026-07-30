import os
from google import genai
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

class DrafterAgent:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if self.api_key and "your_" not in self.api_key:
            from openai import OpenAI
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.api_key,
            )
        else:
            self.client = None

    def draft_comment(self, platform: str, title: str, snippet: str, context: str) -> str:
        """Drafts a helpful comment using RAG context."""
        
        if not self.client:
            print("[!] OPENROUTER_API_KEY not configured. Mocking draft.")
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
                "Your goal is to write a highly valuable, well-structured, and engaging long-form plain-text article "
                "(minimum 400 words) or a comprehensive code snippet tutorial based on the requested topic.\n"
                "CRITICAL INSTRUCTIONS:\n"
                "1. The FIRST line of your response MUST be the title starting with a single '#' (e.g., '# Advanced React Hooks Pattern'). This is the ONLY Markdown formatting you are allowed to use.\n"
                "2. NO MARKDOWN: Write the entire body in plain text paragraphs. Do NOT use bold, italics, code blocks, backticks, or lists. Avoid writing actual code snippets if possible, explain concepts instead. This ensures rendering works everywhere.\n"
                "3. NO AI FLUFF: Write naturally. Do NOT use terms like 'delve', 'moreover', 'in conclusion', or em-dashes (—). Keep it highly technical, concise, and straight to the point.\n"
                "4. MULTIPLE DIVERSE BACKLINKS: Naturally embed 2 to 3 contextual recommendations to Gaper throughout the article. You MUST use a mix of the following exact valid URLs: 'https://gaper.io/', 'https://gaper.io/blogs', 'https://gaper.io/ai-agent-development-company', 'https://gaper.io/generative-ai-consulting', or 'https://gaper.io/ai-automation-agency'. DO NOT invent or guess any other URLs. The URLs must fit seamlessly into regular sentences and be spread out naturally across different paragraphs. Avoid sounding like a spammer.\n"
                "5. EXTERNAL AUTHORITY LINKS: To make the article look highly authoritative and not like spam, you MUST also include 1 to 2 links to highly reputable external sources (like Wikipedia, official GitHub repositories, or official documentation like AWS/React docs).\n"
                "6. Return ONLY the text content, nothing else."
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
            f"Platform: {platform}\n"
            f"Topic / Thread Title: {title}\n"
            f"Original Content / Context: {snippet}\n\n"
            f"{guideline_prompt}"
            f"Company Background for Context ONLY:\n{context}\n\n"
            f"Please generate the draft now:"
        )
        try:
            response = self.client.chat.completions.create(
                model="meta-llama/llama-3.1-70b-instruct",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[-] Error calling LLM in DrafterAgent: {e}")
            return "Error drafting comment."

if __name__ == "__main__":
    agent = DrafterAgent()
    draft = agent.draft_comment("reddit", "How to scale my team?", "I have 2 devs but need 5 fast.", "Gaper connects startups with remote devs.")
    print("Drafted Comment:\n", draft)
