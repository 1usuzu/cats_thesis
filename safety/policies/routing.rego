package routing

import rego.v1

# Mặc định là chặn, chỉ cho phép nếu không có lỗi nào
default allow := false

allow := true if count(violations) == 0

# RULE 1: Hàng đợi quá tải
violations contains "QUEUE_OVERLOAD" if input.queue_depth > 50

# RULE 2: Compute quá tải (GPU cho Cloud, CPU cho Edge)
violations contains "GPU_OVERLOAD" if {
    input.site == "cloud"
    input.compute_util > 90
}

violations contains "CPU_OVERLOAD" if {
    input.site == "edge"
    input.compute_util > 92
}

# RULE 3: Vi phạm SLA (Độ trễ dự kiến cao hơn cho phép)
violations contains "SLA_VIOLATION" if input.predicted_latency_ms > input.sla_target_ms

# RULE 5: Chặn Edge nếu yêu cầu HQ mà mạng lại đang xuống cấp
violations contains "EDGE_DEGRADED_HQ" if {
    input.request_tag == "high_quality"
    input.site_state == "DEGRADED"
    input.site == "edge"
}
