import os
import requests
from bs4 import BeautifulSoup
from ollama import Client
from tavily import TavilyClient
from duckduckgo_search import DDGS

# --- Config ---
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME = "qwen3.5:2b" # Extremely fast & lightweight for 2026
TAVILY_KEY = os.getenv("TAVILY_API_KEY", "") 

client = Client(host=OLLAMA_HOST)


def search_serper(query, api_key):
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": query})
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    return response.json()

def scrape_url(url):
    """Fetches and cleans text from a URL."""
    try:
        response = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, 'html.parser')
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
        text = soup.get_text(separator=' ')
        return " ".join(text.split())[:2000] # Limit to first 2000 chars for speed
    except Exception as e:
        return f"Could not scrape {url}: {e}"

def get_search_links(query):
    """Gets top URLs from DuckDuckGo."""
    print(f"Searching for: {query}")
    with DDGS() as ddgs:
        return [r['href'] for r in ddgs.text(query, max_results=3)]

def main():
    query = "Why is red a color?"
    
    # 1. Search for links
    links = get_search_links(query)
    
    # 2. Scrape the content of those links
    web_context = ""
    for link in links:
        print(f"Reading: {link}...")
        web_context += f"\nSource ({link}):\n" + scrape_url(link)
    
    # 3. Final Answer from LLM
    prompt = f"""
    You are an automated researcher. Use the web data below to answer the question.
    DATA: {web_context}
    ---
    QUESTION: {query}
    """
    
    print("\n--- Final Analysis ---")
    for chunk in client.generate(model=MODEL_NAME, prompt=prompt, stream=True):
        print(chunk['response'], end='', flush=True)

if __name__ == "__main__":
    main()