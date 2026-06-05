import pytest
from httpx import AsyncClient, ASGITransport
import asyncio
from main import app as orchestrator_app

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=orchestrator_app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_metrics_update_and_export():
    async with AsyncClient(transport=ASGITransport(app=orchestrator_app), base_url="http://test") as ac:
        # Update metrics
        payload = {
            "cloud_inflight": 15,
            "edge_inflight": 5,
            "current_rps": 10.5,
            "cloud_total_inference_ms": 120.0,
            "edge_total_inference_ms": 60.0
        }
        res_post = await ac.post("/metrics/update", json=payload)
        assert res_post.status_code == 200
        
        # Get metrics
        res_get = await ac.get("/metrics")
        assert res_get.status_code == 200
        assert "cats_gateway_rps 10.5" in res_get.text
        assert 'cats_gateway_inflight{site="cloud"} 15' in res_get.text
