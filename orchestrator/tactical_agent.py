import requests
from metrics_cache import metrics_cache

# Trọng số chuẩn từ Master Plan v5.0
W_LATENCY = 0.30
W_QUEUE = 0.30
W_COMPUTE = 0.25
W_QUALITY_DEFAULT = 0.15

MAX_QUEUE = 50.0
QUALITY_SCORE = {"cloud": 1.0, "edge": 0.6}
SLA_TARGET_MS = 500
OPA_URL = "http://localhost:8181/v1/data/routing"

def compute_cats_score(site: str, request_tag: str = "default"):
    data = metrics_cache.get_all()
    
    latency_ms = data.get(f"{site}_latency_ms", 0)
    queue_depth = data.get(f"{site}_queue_depth", 0)
    
    if site == "cloud":
        compute_util = data.get("cloud_gpu_util", 0)
    else:
        compute_util = data.get("edge_cpu_util", 0)
        
    w_quality = W_QUALITY_DEFAULT
    if request_tag == "fast_ok":
        w_quality = 0.05
    elif request_tag == "high_quality":
        w_quality = 0.30
        
    score_lat = 1.0 / (1.0 + (latency_ms / 100.0))
    score_q = max(0.0, 1.0 - (queue_depth / MAX_QUEUE))
    score_comp = max(0.0, 1.0 - (compute_util / 100.0))
    
    total_score = (W_LATENCY * score_lat) + \
                  (W_QUEUE * score_q) + \
                  (W_COMPUTE * score_comp) + \
                  (w_quality * QUALITY_SCORE[site])
                  
    return round(total_score, 4)

def check_opa_safety(site: str, request_tag: str, site_state: str = "NORMAL"):
    """
    Gửi dữ liệu kiểm tra an toàn cho OPA dựa trên schema v5.0
    """
    data = metrics_cache.get_all()
    queue_depth = data.get(f"{site}_queue_depth", 0)
    latency_ms = data.get(f"{site}_latency_ms", 0)
    
    if site == "cloud":
        compute_util = data.get("cloud_gpu_util", 0)
    else:
        compute_util = data.get("edge_cpu_util", 0)

    # Đóng gói JSON theo đúng Schema OPA
    opa_input = {
        "input": {
            "site": site,
            "queue_depth": queue_depth,
            "compute_util": compute_util,
            "predicted_latency_ms": latency_ms,
            "request_tag": request_tag,
            "site_state": site_state,
            "sla_target_ms": SLA_TARGET_MS
        }
    }
    
    try:
        response = requests.post(OPA_URL, json=opa_input, timeout=1)
        result = response.json().get("result", {})
        return result.get("allow", False), result.get("violations", [])
    except requests.exceptions.RequestException:
        print(f"Cảnh báo: Lỗi kết nối OPA. Bỏ qua kiểm duyệt an toàn cho {site}.")
        # Nếu OPA sập (unreachable), hệ thống vẫn tiếp tục chạy theo Rule v5.0
        return True, []
