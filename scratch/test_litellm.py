import os
import asyncio
from dotenv import load_dotenv
from browser_use import ChatLiteLLM, Agent

# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)

async def main():
    api_key = os.getenv("GEMINI_API_KEY")
    os.environ["GEMINI_API_KEY"] = api_key # litellm looks for this
    
    if not api_key:
        print("GEMINI_API_KEY not found in .env")
        return

    print("\nTesting ChatLiteLLM with gemini/gemini-1.5-flash-latest...")
    try:
        llm = ChatLiteLLM(model="gemini/gemini-1.5-flash-latest")
        agent = Agent(task="Respond with the word SUCCESS only.", llm=llm, use_vision=False)
        result = await agent.run(max_steps=1)
        if result.is_done():
            print(f"Success with ChatLiteLLM!")
        else:
            print(f"Failed to complete task.")
    except Exception as e:
        print(f"Exception with ChatLiteLLM: {e}")

if __name__ == "__main__":
    asyncio.run(main())
