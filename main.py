import json
import os
import time
import requests
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Optional
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Configuration
API_KEY = os.getenv("NEWS_API_KEY")
if not API_KEY:
    raise ValueError("No NEWS_API_KEY found in environment variables")

BASE_URL = "https://newsapi.org/v2"
CACHE_FILE = "news_cache.json"
CACHE_DURATION = 200 # 10 minutes in seconds

def get_cached_data(key: str):
    """Retrieve data from file-based cache if valid."""
    if not os.path.exists(CACHE_FILE):
        return None
    
    try:
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
        
        if key in cache:
            entry = cache[key]
            if time.time() - entry["timestamp"] < CACHE_DURATION:
                print(f"Serving from cache: {key}")
                return entry["data"]
            else:
                print(f"Cache expired: {key}")
    except Exception as e:
        print(f"Cache read error: {e}")
    
    return None

def save_to_cache(key: str, data: dict):
    """Save data to file-based cache."""
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                cache = json.load(f)
        except Exception:
            cache = {}
            
    cache[key] = {
        "timestamp": time.time(),
        "data": data
    }
    
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except Exception as e:
        print(f"Cache write error: {e}")

@app.get("/news")
def get_news(
    category: str = Query("general", description="News category"),
    location: str = Query("World", description="Location: World, India, Bangalore")
):
    """
    Fetch news based on Category and Location filters using independent logic.
    """
    # Create a unique cache key
    cache_key = f"{location}_{category}"
    cached_response = get_cached_data(cache_key)
    if cached_response:
        return cached_response

    params = {
        "apiKey": API_KEY,
        "pageSize": 20  # Limit to save bandwidth
    }

    endpoint = "/top-headlines"
    
    # 1. Handle BANGALORE (City specific logic requested by user)
    if location.lower() == "bangalore":
        endpoint = "/everything"
        params["q"] = "Bangalore"
        params["sortBy"] = "publishedAt"
        params["language"] = "en"
        
        # Add category context to query if not general
        if category != "general":
             params["q"] += f" AND {category}"

    # 2. Handle INDIA (Country specific)
    elif location.lower() == "india":
        params["country"] = "in"
        
        if category == "finance":
             # NewsAPI has no 'finance' category, use business + q
             params["category"] = "business"
             params["q"] = "finance"
        elif category == "tech":
             params["category"] = "technology"
        elif category == "home":
             params["category"] = "general"
        else:
             # business, general, etc.
             params["category"] = category

    # 3. Handle WORLD (Default/International)
    else:
        # Default to US/English for "World" or just language=en without country (if source allows)
        params["language"] = "en"
        
        if category == "finance":
             # Use business category for finance, drop 'q' to ensure results
             params["category"] = "business"
             # params["q"] = "finance" # strict filtering often yields 0 results on headlines
        elif category == "tech":
             params["category"] = "technology"
        elif category == "home":
             # For world home, general category
             params["category"] = "general"
        else:
             params["category"] = category

    # Clean up params for /top-headlines vs /everything differences
    # /everything does NOT accept 'country' or 'category' in the same way top-headlines does (usually).
    # However, user Logic says: "Bangalore" -> /everything. Others -> implicitly /top-headlines (default)
    
    # Correction for Bangalore logic collision above:
    if location.lower() == "bangalore":
        # Ensure we don't send incompatible params if switching to /everything
        if "country" in params: del params["country"]
        if "category" in params: del params["category"]  # everything endpoint doesn't support category param
    
    
    # Make request
    try:
        print(f"Requesting: {BASE_URL}{endpoint} with params {params}")
        response = requests.get(f"{BASE_URL}{endpoint}", params=params)
        data = response.json()
        
        articles = []
        if response.status_code == 200:
            articles = data.get("articles", [])
            
            # FALLBACK LOGIC
            # If no articles found for India (General, Tech, Business, etc), try /everything
            if not articles and location.lower() == "india":
                print(f"No headlines found for India {category}. Attempting fallback to /everything...")
                
                query = "India" # Default for 'home'/'general'
                if category == "finance": query = "finance India"
                elif category == "business": query = "business India"
                elif category == "tech": query = "technology India"
                
                fallback_params = {
                    "apiKey": API_KEY,
                    "sortBy": "publishedAt",
                    "language": "en",
                    "pageSize": 20,
                    "q": query
                }
                
                resp_fallback = requests.get(f"{BASE_URL}/everything", params=fallback_params)
                if resp_fallback.status_code == 200:
                    articles = resp_fallback.json().get("articles", [])

            # Filter out [Removed] articles
            final_articles = []
            for art in articles:
                if art.get("title") == "[Removed]":
                    continue
                    
                final_articles.append({
                    "title": art.get("title"),
                    "description": art.get("description"),
                    "source": art.get("source", {}).get("name"),
                    "url": art.get("url"),
                    "urlToImage": art.get("urlToImage"),
                    "publishedAt": art.get("publishedAt")
                })
            
            result = {"articles": final_articles}
            save_to_cache(cache_key, result)
            return result
        else:
            return {"error": data.get("message", "Unknown error from NewsAPI")}

    except Exception as e:
        return {"error": str(e)}

# Serve static files
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
