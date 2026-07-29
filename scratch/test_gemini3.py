import os
import asyncio
from dotenv import load_dotenv
from browser_use import ChatGoogle, Agent

# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)

async def main():
    api_key = os.getenv("GEMINI_API_KEY")

    models_to_test = [
        "gemini-3.5-flash",
        "gemini-3.6-flash",
        "gemini-flash-latest"
    ]
    
    for model in models_to_test:
        print(f"\nTesting {model}...")
        try:
            llm = ChatGoogle(model=model, api_key=api_key)
            agent = Agent(task="Respond with the word SUCCESS only.", llm=llm, use_vision=False)
            result = await agent.run(max_steps=1)
            print(f"Success with {model}!")
        except Exception as e:
            print(f"Failed with {model}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
