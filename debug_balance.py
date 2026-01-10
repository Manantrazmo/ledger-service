import requests
import json
import time

def debug_balance():
    base_url = "http://localhost:8000"
    
    # 1. Login
    auth_resp = requests.post(
        f"{base_url}/v1/auth/token",
        data={"username": "admin@tigerbeetle.com", "password": "tigerbeetle"}
    )
    token = auth_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    print("--- 1. Debugging Account 11 via LOOKUP (Current State) ---")
    # This is the definitive source of truth for "Current Balance"
    resp = requests.post(f"{base_url}/v1/accounts/lookup", headers=headers, json=["11"])
    print(json.dumps(resp.json(), indent=2))

    print("\n--- 2. Debugging Account 11 via BALANCES Endpoint ---")
    # Testing default filter (which has 0s)
    resp = requests.post(f"{base_url}/v1/accounts/balances", headers=headers, json={"account_id": "11"})
    print("Default Filter Response:")
    print(json.dumps(resp.json(), indent=2))

    print("\n--- 3. Debugging Account 11 via BALANCES (With Time Range) ---")
    # Trying with a wide timestamp range
    # TigerBeetle timestamps are nanoseconds since epoch
    current_ts = int(time.time_ns())
    payload = {
        "account_id": "11",
        "timestamp_min": 0,
        "timestamp_max": current_ts, 
        "limit": 10
    }
    resp = requests.post(f"{base_url}/v1/accounts/balances", headers=headers, json=payload)
    print("Time Range Filter Response:")
    print(json.dumps(resp.json(), indent=2))

if __name__ == "__main__":
    debug_balance()
