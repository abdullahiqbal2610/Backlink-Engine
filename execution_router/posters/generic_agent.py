import os
import json
import time
from playwright.sync_api import sync_playwright
from google import genai
from google.genai import types

class GenericAgentPoster:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        
        # Identity to use for guest posts
        self.guest_name = os.getenv("GUEST_NAME", "Abdullah Iqbal")
        self.guest_email = os.getenv("GUEST_EMAIL", "abdullahiqbal2610@gmail.com")
        self.guest_website = os.getenv("GUEST_WEBSITE", "https://gaper.io")
        
    def post(self, url: str, final_comment: str):
        if not self.client:
            print("[-] GEMINI_API_KEY not configured. Generic Agent requires LLM.")
            return False, None
            
        print(f"[*] Starting Generic Computer Use Agent for {url}")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                page = context.new_page()
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                time.sleep(3) # wait for dynamic forms to render
                
                # 1. Inject IDs into interactive elements
                page.evaluate("""
                    () => {
                        let idCounter = 1;
                        document.querySelectorAll('input, textarea, button').forEach(el => {
                            el.setAttribute('data-agent-id', idCounter++);
                        });
                    }
                """)
                
                # 2. Extract simplified HTML of just the forms
                simplified_html = page.evaluate("""
                    () => {
                        let forms = [];
                        document.querySelectorAll('form').forEach(f => {
                            let formHtml = '';
                            f.querySelectorAll('input, textarea, button').forEach(el => {
                                let label = '';
                                if(el.id) {
                                    let l = document.querySelector(`label[for="${el.id}"]`);
                                    if(l) label = l.innerText;
                                }
                                let type = el.type ? el.type : '';
                                let name = el.name ? el.name : '';
                                let placeholder = el.placeholder ? el.placeholder : '';
                                let agentId = el.getAttribute('data-agent-id');
                                let text = el.innerText ? el.innerText.trim() : '';
                                formHtml += `<${el.tagName.toLowerCase()} type="${type}" name="${name}" placeholder="${placeholder}" data-agent-id="${agentId}">Label: ${label} Text: ${text}</${el.tagName.toLowerCase()}>\n`;
                            });
                            forms.push(formHtml);
                        });
                        return forms.join('\\n---FORM---\\n');
                    }
                """)
                
                if not simplified_html.strip():
                    print("[-] No forms found on the page.")
                    browser.close()
                    return False, None
                    
                # 3. Ask Gemini for the plan
                prompt = (
                    "You are an automated web agent trying to submit a guest comment/post on a website.\n"
                    "Below is the simplified HTML of the forms found on the page.\n"
                    f"I need to submit a comment with this content:\n{final_comment}\n\n"
                    f"My name is {self.guest_name} and my email is {self.guest_email}. Website: {self.guest_website}.\n"
                    "Identify the data-agent-id for the fields I should fill, and the data-agent-id for the submit button.\n"
                    "Return ONLY a valid JSON object matching this exact schema:\n"
                    '{"fields": {"<data-agent-id>": "<value_to_type>"}, "submit_button_id": "<data-agent-id>"}\n\n'
                    f"Forms HTML:\n{simplified_html}"
                )
                
                response = self.client.models.generate_content(
                    model="gemini-flash-latest",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                    )
                )
                
                plan = json.loads(response.text.strip())
                
                # 4. Execute the plan
                fields = plan.get("fields", {})
                submit_id = plan.get("submit_button_id")
                
                if not submit_id:
                    print("[-] LLM did not find a submit button.")
                    browser.close()
                    return False, None
                    
                for agent_id, value in fields.items():
                    selector = f"[data-agent-id='{agent_id}']"
                    if page.locator(selector).count() > 0:
                        page.fill(selector, value)
                        time.sleep(0.5)
                        
                # Click submit
                print(f"[*] Submitting form using button {submit_id}")
                page.click(f"[data-agent-id='{submit_id}']")
                
                # wait for submission
                page.wait_for_timeout(4000) 
                
                live_url = page.url
                browser.close()
                print(f"[+] Generic Agent successfully submitted to {live_url}")
                return True, live_url, "Guest (Generic Agent)"
                
        except Exception as e:
            print(f"[-] Generic Agent Error: {e}")
            return False, None
