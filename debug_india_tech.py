import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("NEWS_API_KEY")
BASE_URL = "https://newsapi.org/v2"

def test_api():
    if not API_KEY:
        print("Error: NEWS_API_KEY not found")
        return

    # Test: India Tech Fallback
    print("\n--- Testing India Tech Fallback (Everything) ---")
    params = {
        "apiKey": API_KEY,
        "q": "technology AND India",
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": 5
    }
    url = f"{BASE_URL}/everything"
    print(f"Requesting: {url} with {params}")
    
    try:
        resp = requests.get(url, params=params)
        print(f"Status: {resp.status_code}")
        data = resp.json()
        if resp.status_code == 200:
            articles = data.get('articles', [])
            print(f"Articles found: {len(articles)}")
            for idx, art in enumerate(articles):
                print(f"{idx+1}. {art.get('title')}")
        else:
            print("Error response:", data)
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_api()
