import os
import asyncio
from browser_use import ChatGoogle, Agent, BrowserProfile

async def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Set GEMINI_API_KEY")
        return

    models_to_test = [
        "gemini-1.5-flash",
        "gemini-2.0-flash-exp",
        "gemini-flash-latest"
    ]
    
    for model in models_to_test:
        print(f"\nTesting {model}...")
        try:
            llm = ChatGoogle(model=model, api_key=api_key)
            # Use a dummy test instead of starting full browser
            agent = Agent(task="just say hello and finish", llm=llm)
            result = await agent.run(max_steps=1)
            print(f"Success with {model}!")
            return
        except Exception as e:
            print(f"Failed with {model}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
