import asyncio
from browser_use import Agent, BrowserProfile, ChatGoogle
import os

async def main():
    llm = ChatGoogle(model="gemini-3.5-flash", api_key=os.getenv("GEMINI_API_KEY"))
    profile = BrowserProfile(headless=True)
    agent = Agent(
        task="Navigate to example.com and immediately call done with success=False",
        llm=llm,
        browser_profile=profile
    )
    result = await agent.run()
    print("DIR RESULT:", dir(result))
    try:
        print("is_successful:", result.is_successful())
    except Exception as e:
        print("Error calling is_successful:", e)

if __name__ == "__main__":
    asyncio.run(main())
