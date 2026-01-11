import requests

BASE_URL = "http://localhost:8081/api/merchants"

def test_create_merchant():
    # Login first (assuming login is required and we have a way to get a token, 
    # but for now let's try to hit the endpoint and see if we get 401 or something else)
    # The current backend implementation uses session-based auth (flask-login usually).
    # Since I don't have a session, I might get 401. 
    # However, I can check if the server is running and reachable.
    
    try:
        response = requests.get(BASE_URL)
        print(f"GET status: {response.status_code}")
        print(f"GET content: {response.text}")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    test_create_merchant()
