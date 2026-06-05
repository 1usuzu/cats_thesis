import httpx

class SharedClient:
    client: httpx.AsyncClient | None = None

shared_http_client = SharedClient()
