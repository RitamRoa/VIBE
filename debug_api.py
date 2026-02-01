import requests

API_KEY = "3ba57d42e1b3416296ee50d5412d4948"
BASE_URL = "https://newsapi.org/v2"

def test_api():
    # Test 1: Standard Top Headlines (World/Home)
    params = {
        "apiKey": API_KEY,
        "language": "en",
        "category": "general",
        "pageSize": 5
    }
    url = f"{BASE_URL}/top-headlines"
    print(f"Testing {url} with {params}")
    try:
        resp = requests.get(url, params=params)
        print(f"Status: {resp.status_code}")
        data = resp.json()
        if resp.status_code == 200:
            print(f"Articles found: {len(data.get('articles', []))}")
            if len(data.get('articles', [])) == 0:
                print("Response data:", data)
        else:
            print("Error:", data)
    except Exception as e:
        print(f"Exception: {e}")

    print("-" * 20)

    # Test 2: Bangalore (Everything endpoint)
    params_blr = {
        "apiKey": API_KEY,
        "q": "Bangalore",
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": 5
    }
    url_blr = f"{BASE_URL}/everything"
    print(f"Testing {url_blr} with {params_blr}")
    try:
        resp = requests.get(url_blr, params=params_blr)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"Articles found: {len(resp.json().get('articles', []))}")
        else:
            print("Error:", resp.json())
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_api()