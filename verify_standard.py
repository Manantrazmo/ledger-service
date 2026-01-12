import requests
import json

def verify():
    base_url = "http://localhost:8000"
    
    # 1. Login
    print("--- Login ---")
    auth_resp = requests.post(
        f"{base_url}/v1/auth/token",
        data={"username": "admin@tigerbeetle.com", "password": "tigerbeetle"}
    )
    if auth_resp.status_code != 200:
        print("Login failed:", auth_resp.text)
        return
        
    token = auth_resp.json()["access_token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 2. Trigger Error (Create Existing Account)
    print("\n--- Triggering Error (Create Existing Account) ---")
    payload = [{
        "id": "1",  # Assuming '1' exists from previous steps
        "ledger": 1,
        "code": 718,
        "flags": 8,
        "debits_pending": "0",
        "debits_posted": "0",
        "credits_pending": "0",
        "credits_posted": "0",
        "timestamp": "0"
    }]
    
    resp = requests.post(f"{base_url}/v1/accounts", headers=headers, json=payload)
    print(f"Status Code: {resp.status_code}")
    print("Response Body:")
    print(json.dumps(resp.json(), indent=2))

if __name__ == "__main__":
    verify()
