import os
import asyncio
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key)
    try:
        res = llm.invoke("respond with exactly the word SUCCESS")
        print("Response:", res.content)
    except Exception as e:
        print("Failed:", e)

if __name__ == "__main__":
    main()
