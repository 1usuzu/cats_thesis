package routing

import rego.v1

# Input Validation
valid_input if {
    is_number(input.gateway_inflight)
    is_number(input.compute_util)
    is_number(input.predicted_latency_ms)
    is_number(input.sla_target_ms)
    is_string(input.site)
    is_string(input.request_tag)
    is_string(input.site_state)
    input.site in {"cloud", "edge"}
}

# Mặc định là chặn, chỉ cho phép nếu không có lỗi nào và input hợp lệ
default allow := false

allow if {
    valid_input
    count(violations) == 0
}

# Collect violations
violations contains "INVALID_INPUT" if not valid_input

# RULE 1: Gateway in-flight overload
violations contains "QUEUE_OVERLOAD" if {
    valid_input
    input.gateway_inflight > 50
}

# RULE 2: Compute quá tải (GPU cho Cloud, CPU cho Edge)
violations contains "GPU_OVERLOAD" if {
    valid_input
    input.site == "cloud"
    input.compute_util > 90
}

violations contains "CPU_OVERLOAD" if {
    valid_input
    input.site == "edge"
    input.compute_util > 92
}

# RULE 3: Vi phạm SLA (Độ trễ dự kiến cao hơn cho phép)
violations contains "SLA_VIOLATION" if {
    valid_input
    input.predicted_latency_ms > input.sla_target_ms
}

# RULE 5: Chặn Edge nếu yêu cầu HQ mà mạng lại đang xuống cấp
violations contains "EDGE_DEGRADED_HQ" if {
    valid_input
    input.request_tag == "high_quality"
    input.site_state == "STATE_DEGRADED"
    input.site == "edge"
}
