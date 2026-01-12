# TigerBeetle REST API Request Samples

Use these JSON payloads to test the API via Swagger (`/docs`) or `curl`.

## 1. Batch Create Accounts
**Endpoint**: `POST /v1/accounts`

```json
[
  {
    "id": "1",
    "debits_pending": "0",
    "debits_posted": "0",
    "credits_pending": "0",
    "credits_posted": "0",
    "user_data_128": "0",
    "user_data_64": "0",
    "user_data_32": 0,
    "reserved": 0,
    "ledger": 1,
    "code": 718,
    "flags": 8,
    "timestamp": "0"
  }
]
```

## 2. Lookup Accounts
**Endpoint**: `POST /v1/accounts/lookup`

```json
["1", "2"]
```

## 3. Batch Create Transfers
**Endpoint**: `POST /v1/transfers`

```json
[
  {
    "id": "1001",
    "debit_account_id": "1",
    "credit_account_id": "2",
    "amount": "1000",
    "pending_id": "0",
    "user_data_128": "0",
    "user_data_64": "0",
    "user_data_32": 0,
    "timeout": 0,
    "ledger": 1,
    "code": 1,
    "flags": 0,
    "timestamp": "0"
  }
]
```

## 4. Lookup Transfers
**Endpoint**: `POST /v1/transfers/lookup`

```json
["1001"]
```

## 5. Get Account Balances
**Endpoint**: `POST /v1/accounts/balances`

```json
{
  "account_id": "1",
  "limit": 10,
  "timestamp_min": 0,
  "timestamp_max": 0,
  "code": 0,
  "flags": 0
}
```

## 6. Get Account Transfer History
**Endpoint**: `POST /v1/accounts/transfers`

```json
{
  "account_id": "1",
  "limit": 5
}
```

## 7. Advanced Query Accounts
**Endpoint**: `POST /v1/accounts/query`

```json
{
  "ledger": 1,
  "code": 718,
  "limit": 5,
  "user_data_32": 0
}
```

## 8. Advanced Query Transfers
**Endpoint**: `POST /v1/transfers/query`

```json
{
  "ledger": 1,
  "timestamp_min": 0,
  "limit": 100
}
```

> [!NOTE]
> All create operations accept a **List** of objects (batching). Lookup operations accept a **List** of strings/integers (IDs). All query operations accept a single filter object.
