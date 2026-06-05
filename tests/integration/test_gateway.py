import pytest
from httpx import AsyncClient, ASGITransport
from main import app as gateway_app

@pytest.mark.asyncio
async def test_gateway_health():
    async with AsyncClient(transport=ASGITransport(app=gateway_app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_api_key_auth_missing():
    async with AsyncClient(transport=ASGITransport(app=gateway_app), base_url="http://test") as ac:
        # Chat requires API Key
        response = await ac.post("/v1/chat", json={"prompt": "hello"})
    assert response.status_code == 401
    assert "Missing X-API-Key header" in response.text

@pytest.mark.asyncio
async def test_api_key_auth_invalid():
    async with AsyncClient(transport=ASGITransport(app=gateway_app), base_url="http://test") as ac:
        response = await ac.post("/v1/chat", json={"prompt": "hello"}, headers={"X-API-Key": "invalid"})
    assert response.status_code == 401
    assert "Invalid API Key" in response.text

@pytest.mark.asyncio
async def test_circuit_breaker_endpoint():
    async with AsyncClient(transport=ASGITransport(app=gateway_app), base_url="http://test") as ac:
        response = await ac.get("/health/sites")
    assert response.status_code == 200
    data = response.json()
    assert "states" in data
    assert data["states"]["cloud"] == "CLOSED"
    assert data["states"]["edge"] == "CLOSED"
