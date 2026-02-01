import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("NEWS_API_KEY")
BASE_URL = "https://newsapi.org/v2"

def test_india_all():
    if not API_KEY:
        print("Error: NEWS_API_KEY not found")
        return

    categories = ["general", "technology", "business"]
    
    for cat in categories:
        print(f"\n--- Testing India {cat} (Top Headlines) ---")
        params = {
            "apiKey": API_KEY,
            "country": "in",
            "category": cat,
            "pageSize": 5
        }
        url = f"{BASE_URL}/top-headlines"
        
        try:
            resp = requests.get(url, params=params)
            print(f"Status: {resp.status_code}")
            data = resp.json()
            if resp.status_code == 200:
                articles = data.get('articles', [])
                print(f"Articles found: {len(articles)}")
                if len(articles) > 0:
                    print(f"Sample: {articles[0]['title']}")
            else:
                print("Error:", data)
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    test_india_all()
