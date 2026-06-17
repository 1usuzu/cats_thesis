package routing_test

import rego.v1
import data.routing

# Test: Allow normal request
test_allow_normal if {
    routing.allow with input as {
        "site": "cloud",
        "gateway_inflight": 10,
        "compute_util": 50,
        "predicted_latency_ms": 200,
        "request_tag": "default",
        "site_state": "STATE_NORMAL",
        "sla_target_ms": 500
    }
}

# Test: Rule 1 - Queue Overload
test_queue_overload if {
    not routing.allow with input as {
        "site": "cloud",
        "gateway_inflight": 51,
        "compute_util": 50,
        "predicted_latency_ms": 200,
        "request_tag": "default",
        "site_state": "STATE_NORMAL",
        "sla_target_ms": 500
    }
    "QUEUE_OVERLOAD" in routing.violations with input as {
        "site": "cloud",
        "gateway_inflight": 51,
        "compute_util": 50,
        "predicted_latency_ms": 200,
        "request_tag": "default",
        "site_state": "STATE_NORMAL",
        "sla_target_ms": 500
    }
}

# Test: Rule 2 - GPU Overload (Cloud)
test_gpu_overload if {
    not routing.allow with input as {
        "site": "cloud",
        "gateway_inflight": 10,
        "compute_util": 95,
        "predicted_latency_ms": 200,
        "request_tag": "default",
        "site_state": "STATE_NORMAL",
        "sla_target_ms": 500
    }
    "GPU_OVERLOAD" in routing.violations with input as {
        "site": "cloud",
        "gateway_inflight": 10,
        "compute_util": 95,
        "predicted_latency_ms": 200,
        "request_tag": "default",
        "site_state": "STATE_NORMAL",
        "sla_target_ms": 500
    }
}

# Test: Rule 2 - CPU Overload (Edge)
test_cpu_overload if {
    not routing.allow with input as {
        "site": "edge",
        "gateway_inflight": 10,
        "compute_util": 95,
        "predicted_latency_ms": 200,
        "request_tag": "default",
        "site_state": "STATE_NORMAL",
        "sla_target_ms": 500
    }
    "CPU_OVERLOAD" in routing.violations with input as {
        "site": "edge",
        "gateway_inflight": 10,
        "compute_util": 95,
        "predicted_latency_ms": 200,
        "request_tag": "default",
        "site_state": "STATE_NORMAL",
        "sla_target_ms": 500
    }
}

# Test: Rule 3 - SLA Violation
test_sla_violation if {
    not routing.allow with input as {
        "site": "cloud",
        "gateway_inflight": 10,
        "compute_util": 50,
        "predicted_latency_ms": 600,
        "request_tag": "default",
        "site_state": "STATE_NORMAL",
        "sla_target_ms": 500
    }
    "SLA_VIOLATION" in routing.violations with input as {
        "site": "cloud",
        "gateway_inflight": 10,
        "compute_util": 50,
        "predicted_latency_ms": 600,
        "request_tag": "default",
        "site_state": "STATE_NORMAL",
        "sla_target_ms": 500
    }
}

# Test: Rule 5 - Edge Degraded HQ
test_edge_degraded_hq if {
    not routing.allow with input as {
        "site": "edge",
        "gateway_inflight": 10,
        "compute_util": 50,
        "predicted_latency_ms": 200,
        "request_tag": "high_quality",
        "site_state": "STATE_DEGRADED",
        "sla_target_ms": 500
    }
    "EDGE_DEGRADED_HQ" in routing.violations with input as {
        "site": "edge",
        "gateway_inflight": 10,
        "compute_util": 50,
        "predicted_latency_ms": 200,
        "request_tag": "high_quality",
        "site_state": "STATE_DEGRADED",
        "sla_target_ms": 500
    }
}

# Test: Invalid Input
test_invalid_input if {
    not routing.allow with input as {
        "site": "invalid_site",
        "gateway_inflight": 10,
        "compute_util": 50,
        "predicted_latency_ms": 200,
        "request_tag": "default",
        "site_state": "STATE_NORMAL",
        "sla_target_ms": 500
    }
    "INVALID_INPUT" in routing.violations with input as {
        "site": "invalid_site",
        "gateway_inflight": 10,
        "compute_util": 50,
        "predicted_latency_ms": 200,
        "request_tag": "default",
        "site_state": "STATE_NORMAL",
        "sla_target_ms": 500
    }
}
