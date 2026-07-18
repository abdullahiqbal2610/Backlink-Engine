import requests
from bs4 import BeautifulSoup

def scrape_gaper_io():
    print("[*] Scraping gaper.io for RAG context...")
    url = "https://gaper.io"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer"]):
            script.extract()
            
        # Get text
        text = soup.get_text(separator=' ', strip=True)
        
        # Split into chunks of roughly 500 characters
        chunks = []
        words = text.split()
        current_chunk = []
        current_length = 0
        
        for word in words:
            current_chunk.append(word)
            current_length += len(word) + 1
            if current_length >= 500:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_length = 0
                
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            
        print(f"[+] Scraped {len(chunks)} chunks from gaper.io")
        return chunks
        
    except Exception as e:
        print(f"[-] Failed to scrape gaper.io: {e}")
        return []

if __name__ == "__main__":
    chunks = scrape_gaper_io()
    for i, c in enumerate(chunks[:2]):
        print(f"Chunk {i+1}:\n{c}\n")
