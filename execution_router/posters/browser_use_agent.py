import os
import asyncio
from urllib.parse import urlparse
from browser_use import Agent, BrowserProfile, ChatGoogle

class BrowserUseAgentPoster:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        
        # Identity to use for guest posts
        self.guest_name = os.getenv("GUEST_NAME", "Abdullah Iqbal")
        self.guest_email = os.getenv("GUEST_EMAIL", "abdullahiqbal2610@gmail.com")
        self.guest_website = os.getenv("GUEST_WEBSITE", "https://gaper.io")
        
    def post(self, url: str, final_comment: str):
        if not self.api_key:
            print("[-] GEMINI_API_KEY not configured. Browser-Use Agent requires LLM.")
            return False, None, None
            
        print(f"[*] Starting Autonomous Browser-Use Agent for {url}")
        # Using Gemini 3.5 Flash natively via browser_use (modern endpoint)
        llm = ChatGoogle(model="gemini-3.5-flash", api_key=self.api_key)
        
        domain = urlparse(url).netloc
        state_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "browser_profiles", f"{domain}_state.json")
        
        account_used = "Guest (Browser-Use)"
        profile = BrowserProfile(headless=True)
        
        if os.path.exists(state_file):
            print(f"[*] Found authenticated session state for {domain}")
            profile.storage_state = state_file
            account_used = f"Authenticated ({domain}_state.json)"
            
        try:
            result = asyncio.run(self._run_agent(profile, llm, url, final_comment))
            print(f"[+] Browser-Use Agent execution completed.")
            
            # Check if the agent actually succeeded
            is_success = result.is_successful()
            
            if is_success:
                print(f"    [+] Agent reported SUCCESS.")
                final_url = result.urls()[-1] if hasattr(result, "urls") and result.urls() else url
                return True, final_url, account_used
            else:
                print(f"    [-] Agent reported FAILURE or gracefully stopped.")
                return False, None, None
                
        except Exception as e:
            print(f"[-] Browser-Use Agent Error: {e}")
            return False, None, None
            
    async def _run_agent(self, profile: BrowserProfile, llm, url: str, final_comment: str):
        from browser_use import Controller
        import browser_use.browser.session as browser_session
        
        controller = Controller()
        safe_comment = final_comment.replace('`', '\\`').replace('$', '\\$')
        
        @controller.action('Instantly paste the FULL guest post article into the currently focused input/textarea. You MUST click/focus the input box first before using this action!')
        async def paste_article(confirm: bool, browser: browser_session.BrowserSession):
            page = await browser.get_current_page()
            script = f"""
            () => {{
                const el = document.activeElement;
                if (!el || (el.tagName !== 'TEXTAREA' && el.tagName !== 'INPUT' && !el.isContentEditable)) {{
                    return "Error: No text input field is currently focused. Please click the input field first.";
                }}
                if (el.isContentEditable) {{
                    el.innerText = `{safe_comment}`;
                }} else {{
                    el.value = `{safe_comment}`;
                }}
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return "Success: Article pasted into focused element.";
            }}
            """
            result = await page.evaluate(script)
            return result
            
        task_prompt = (
            f"You are an automated SDR agent trying to submit a highly valuable guest post/comment. You are already logged in to your account!\n"
            f"1. Navigate to: {url} \n"
            f"2. Locate the main post submission form, comment box, or 'New Article' button.\n"
            f"3. Fill in the required details. If it requires a title, extract a logical title from the content.\n\n"
            f"CRITICAL INSTRUCTION FOR ARTICLE BODY:\n"
            f"DO NOT use the normal 'input_text' tool to type the main article body! The article is too long and will cause a timeout or ModelOutputTruncatedError.\n"
            f"INSTEAD, you must:\n"
            f"   a) Click on the textarea/input box for the article body to focus it.\n"
            f"   b) Use your 'paste_article' action (with confirm=True).\n"
            f"   c) DO NOT use the 'evaluate' action to run JS. DO NOT search for the article in local files. The article is already securely loaded into the 'paste_article' action! Just execute the action.\n\n"
            f"If it asks for Guest Info: Name is {self.guest_name}, Email is {self.guest_email}.\n"
            f"4. Click submit or publish.\n"
            f"5. If you cannot find a place to post, or if the site demands a complex ID verification paywall, stop and fail gracefully."
        )
        
        agent = Agent(
            task=task_prompt,
            llm=llm,
            browser_profile=profile,
            controller=controller
        )
        result = await agent.run()
        return result
