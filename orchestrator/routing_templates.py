# 5 Trạng thái hệ thống và tỷ lệ phân bổ tỷ trọng theo Master Plan v5.0
ROUTING_TEMPLATES = {
    "STATE_NORMAL":       {"cloud": 0.50, "edge": 0.50},
    "STATE_EDGE_LOADED":  {"cloud": 0.75, "edge": 0.25},
    "STATE_DEGRADED":     {"cloud": 0.40, "edge": 0.60},
    "STATE_BURST":        {"cloud": 0.65, "edge": 0.35},
    "STATE_CRITICAL":     {"cloud": 0.90, "edge": 0.10},
}
