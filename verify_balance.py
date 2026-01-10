import requests
import json

def verify_simplification():
    base_url = "http://localhost:8000"
    
    # 1. Login
    print("--- Login ---")
    auth_resp = requests.post(f"{base_url}/v1/auth/token", data={"username": "admin@tigerbeetle.com", "password": "tigerbeetle"})
    token = auth_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 2. Check Balance (Simplified Payload)
    print("\n--- Check Balance (Simple ID only) ---")
    simple_payload = {"account_id": "1"}
    
    resp = requests.post(f"{base_url}/v1/accounts/balances", headers=headers, json=simple_payload)
    print(f"Status: {resp.status_code}")
    print(json.dumps(resp.json(), indent=2))

    # 3. Check Balance (With Optional Flags)
    print("\n--- Check Balance (With Advanced Flags) ---")
    advanced_payload = {
        "account_id": "1",
        "flags": 0,
        "limit": 5
    }
    
    resp_adv = requests.post(f"{base_url}/v1/accounts/balances", headers=headers, json=advanced_payload)
    print(f"Status (Advanced): {resp_adv.status_code}")
    # Just confirm it works
    if resp_adv.status_code == 200:
        print("Success: Advanced query handled correctly associated with simplified model.")

if __name__ == "__main__":
    verify_simplification()
