# TigerBeetle REST API Bridge (Production Grade)

A high-performance, secure RESTful wrapper for the [TigerBeetle](https://tigerbeetle.com/) financial database built with FastAPI.

## Features
- **API Key Security**: Protected endpoints using `X-API-Key`.
- **Rate Limiting**: Built-in protection against request flooding.
- **Interactive Swagger**: Explore and test APIs at `/docs`.
- **Batch Operations**: Support for TigerBeetle's native batching for high throughput.
- **Observability**: Latency tracking for both HTTP and TigerBeetle core operations.

## Quick Start

1. **Start TigerBeetle**:
   ```bash
   docker-compose up -d
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Server**:
   ```bash
   python main.py
   ```

4. **Access Swagger UI**:
   Go to `http://localhost:8000/docs`

## Authentication
The API uses **OAuth2 Password Grant** (Bearer Tokens).

1.  **Get Token**:
    ```bash
    curl -X POST http://localhost:8000/v1/auth/token \
         -F "username=admin" \
         -F "password=tigerbeetle"
    ```
2.  **Use Token**:
    Include the token in the `Authorization` header:
    ```bash
    Authorization: Bearer <your_token>
    ```

## Testing with Swagger
1. Open `http://localhost:8000/docs`.
2. Click the **Authorize** button.
3. Enter `username` and `password` (default: `admin`/`tigerbeetle`).
4. Click **Login**. Swagger will handle the token automatically for all requests.

## Observability
- **Request ID**: Every request/response includes a `X-Request-ID` header.
- **Detailed Logs**: Server logs include Request ID, method, path, and duration.
