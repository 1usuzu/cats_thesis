import pytest
from metrics_cache import metrics_cache

def test_metrics_cache_default_values():
    assert metrics_cache.get("cloud_gateway_inflight") == 0
    assert metrics_cache.get("current_rps") == 0.0
    assert metrics_cache.get("previous_rps") == 1.0

def test_metrics_cache_update():
    metrics_cache.update("cloud_latency_ms", 123.4)
    assert metrics_cache.get("cloud_latency_ms") == 123.4
    
    data = metrics_cache.get_all()
    assert data["cloud_latency_ms"] == 123.4

def test_metrics_cache_rps_burst_tracking():
    metrics_cache.update("current_rps", 5.0)
    # Wait a tiny bit to simulate time passing
    import time
    time.sleep(0.01)
    metrics_cache.update("current_rps", 20.0)
    
    # The previous_rps should have been updated to 5.0 when current_rps changed
    assert metrics_cache.get("previous_rps") == 5.0
    assert metrics_cache.get("current_rps") == 20.0

def test_get_site_metrics():
    metrics_cache.update("cloud_latency_ms", 50)
    metrics_cache.update("edge_latency_ms", 10)
    
    cloud_metrics = metrics_cache.get_site_metrics("cloud")
    assert "cloud_latency_ms" in cloud_metrics
    assert "edge_latency_ms" not in cloud_metrics
    assert cloud_metrics["cloud_latency_ms"] == 50

def test_prometheus_format():
    metrics_cache.update("cloud_gateway_inflight", 5)
    metrics_cache.update("current_rps", 12.5)
    
    prom_data = metrics_cache.to_prometheus_format()
    assert 'cats_gateway_inflight{site="cloud"} 5' in prom_data
    assert 'cats_gateway_rps 12.5' in prom_data
