import pytest
from strategic_agent import rule_based_fallback

def test_rule_based_fallback_normal():
    data = {
        "edge_gateway_inflight": 0,
        "edge_cpu_util": 50,
        "cloud_latency_ms": 20,
        "edge_latency_ms": 10,
        "cloud_bandwidth_kbps": 100000,
        "edge_bandwidth_kbps": 100000,
        "current_rps": 5,
        "previous_rps": 5
    }
    assert rule_based_fallback(data) == "STATE_NORMAL"

def test_rule_based_fallback_edge_loaded():
    data = {
        "edge_gateway_inflight": 40, # Above settings.state_edge_loaded_inflight (35)
        "edge_cpu_util": 50,
        "cloud_latency_ms": 20,
        "edge_latency_ms": 10,
        "cloud_bandwidth_kbps": 100000,
        "edge_bandwidth_kbps": 100000,
        "current_rps": 5,
        "previous_rps": 5
    }
    # Mock settings temporarily if needed, but assuming default settings apply
    assert rule_based_fallback(data) == "STATE_EDGE_LOADED"

def test_rule_based_fallback_degraded():
    data = {
        "edge_gateway_inflight": 0,
        "edge_cpu_util": 50,
        "cloud_latency_ms": 200, # Degraded latency
        "edge_latency_ms": 10,
        "cloud_bandwidth_kbps": 100000,
        "edge_bandwidth_kbps": 100000,
        "current_rps": 5,
        "previous_rps": 5
    }
    assert rule_based_fallback(data) == "STATE_DEGRADED"

def test_rule_based_fallback_burst():
    data = {
        "edge_gateway_inflight": 0,
        "edge_cpu_util": 50,
        "cloud_latency_ms": 20,
        "edge_latency_ms": 10,
        "cloud_bandwidth_kbps": 100000,
        "edge_bandwidth_kbps": 100000,
        "current_rps": 50, # Burst (50 > 3 * 5)
        "previous_rps": 5
    }
    assert rule_based_fallback(data) == "STATE_BURST"

def test_rule_based_fallback_critical():
    data = {
        "edge_gateway_inflight": 40, # Condition 1: Edge loaded
        "edge_cpu_util": 50,
        "cloud_latency_ms": 200, # Condition 2: Degraded
        "edge_latency_ms": 10,
        "cloud_bandwidth_kbps": 100000,
        "edge_bandwidth_kbps": 100000,
        "current_rps": 5,
        "previous_rps": 5
    }
    # Two conditions met = CRITICAL
    assert rule_based_fallback(data) == "STATE_CRITICAL"
