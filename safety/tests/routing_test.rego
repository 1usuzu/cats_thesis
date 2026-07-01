package routing_test

import rego.v1
import data.routing

# Test 1: Normal input should be allowed
test_normal_pass if {
    result := routing.allow with input as {
        "site": "cloud",
        "gateway_inflight": 10,
        "compute_util": 50,
        "predicted_latency_ms": 100,
        "sla_target_ms": 500,
        "request_tag": "default",
        "site_state": "STATE_NORMAL"
    }
    result == true
}

# Test 2: Queue overload (Rule 1)
test_queue_overload if {
    violations := routing.violations with input as {
        "site": "cloud",
        "gateway_inflight": 60,
        "compute_util": 50,
        "predicted_latency_ms": 100,
        "sla_target_ms": 500,
        "request_tag": "default",
        "site_state": "STATE_NORMAL"
    }
    "QUEUE_OVERLOAD" in violations
}

# Test 3: GPU overload on cloud (Rule 2a)
test_gpu_overload if {
    violations := routing.violations with input as {
        "site": "cloud",
        "gateway_inflight": 10,
        "compute_util": 95,
        "predicted_latency_ms": 100,
        "sla_target_ms": 500,
        "request_tag": "default",
        "site_state": "STATE_NORMAL"
    }
    "GPU_OVERLOAD" in violations
}

# Test 4: CPU overload on edge (Rule 2b)
test_cpu_overload if {
    violations := routing.violations with input as {
        "site": "edge",
        "gateway_inflight": 10,
        "compute_util": 95,
        "predicted_latency_ms": 100,
        "sla_target_ms": 500,
        "request_tag": "default",
        "site_state": "STATE_NORMAL"
    }
    "CPU_OVERLOAD" in violations
}

# Test 5: SLA violation (Rule 3)
test_sla_violation if {
    violations := routing.violations with input as {
        "site": "cloud",
        "gateway_inflight": 10,
        "compute_util": 50,
        "predicted_latency_ms": 600,
        "sla_target_ms": 500,
        "request_tag": "default",
        "site_state": "STATE_NORMAL"
    }
    "SLA_VIOLATION" in violations
}

# Test 6: Edge degraded HQ rejection (Rule 5)
test_edge_degraded_hq if {
    violations := routing.violations with input as {
        "site": "edge",
        "gateway_inflight": 10,
        "compute_util": 50,
        "predicted_latency_ms": 100,
        "sla_target_ms": 500,
        "request_tag": "high_quality",
        "site_state": "STATE_DEGRADED"
    }
    "EDGE_DEGRADED_HQ" in violations
}
