import pytest
import os

# Set environment variables for testing before importing anything
os.environ["CLOUD_INFERENCE_URL"] = "http://mock-cloud:11434"
os.environ["EDGE_INFERENCE_URL"] = "http://mock-edge:11434"
os.environ["ORCHESTRATOR_URL"] = "http://mock-orch:8080/route"
os.environ["OPA_URL"] = "http://mock-opa:8181/v1/data/routing"
os.environ["CATS_API_KEYS"] = "test-key-123"

@pytest.fixture(autouse=True)
def reset_metrics_cache():
    """Reset the metrics cache before each test."""
    from metrics_cache import metrics_cache
    
    # Re-initialize cache with defaults
    defaults = {
        "cloud_latency_ms": 0.0,
        "cloud_jitter_ms": 0.0,
        "cloud_bandwidth_kbps": 100000.0,
        "edge_latency_ms": 0.0,
        "edge_jitter_ms": 0.0,
        "edge_bandwidth_kbps": 100000.0,
        "cloud_gpu_util": 0.0,
        "edge_cpu_util": 0.0,
        "cloud_gateway_inflight": 0,
        "edge_gateway_inflight": 0,
        "current_rps": 0.0,
        "previous_rps": 1.0,
    }
    for k, v in defaults.items():
        metrics_cache.update(k, v)
        
    yield
