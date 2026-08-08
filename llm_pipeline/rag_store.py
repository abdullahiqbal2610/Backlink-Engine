import os
import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv

load_dotenv()

class RagStore:
    def __init__(self):
        # We will use an in-memory or simple local persistent chroma db for now.
        persist_directory = os.path.join(os.path.dirname(__file__), "chroma_db")
        
        # Simple client for testing
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(name="company_knowledge_base")
        
        # Seed dummy data if empty
        if self.collection.count() == 0:
            self._seed_dummy_data()
            
    def _seed_dummy_data(self):
        print("[*] Scraping company website for live RAG knowledge base...")
        try:
            from company_scraper import scrape_company_website
            documents = scrape_company_website()
            if documents:
                ids = [f"company_doc_{i}" for i in range(len(documents))]
                self.collection.add(documents=documents, ids=ids)
                print(f"[+] Added {len(documents)} real paragraphs to ChromaDB.")
            else:
                print("[-] Scraping returned no data. Using fallback data.")
                self._fallback_data()
        except Exception as e:
            print(f"[-] Failed to scrape company website during RAG seed: {e}")
            self._fallback_data()
            
    def _fallback_data(self):
        desc = os.getenv("COMPANY_DESCRIPTION", "A technology company providing solutions.")
        name = os.getenv("COMPANY_NAME", "The Company")
        documents = [
            desc,
            f"{name} is focused on delivering high-quality products and services."
        ]
        ids = ["fallback_1", "fallback_2"]
        self.collection.add(documents=documents, ids=ids)
        
    def retrieve_context(self, query: str, n_results: int = 2) -> str:
        """Retrieves relevant context for the given query from the Vector DB."""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        if results and results["documents"]:
            # Combine the returned chunks into a single string
            return "\n\n".join(results["documents"][0])
        return ""

if __name__ == "__main__":
    store = RagStore()
    ctx = store.retrieve_context("What does the company do?")
    print("Retrieved Context:\n", ctx)
