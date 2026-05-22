import time
import json
import requests
import threading
from metrics_cache import metrics_cache
from shared_state import shared_state
from routing_templates import ROUTING_TEMPLATES

# Control Plane bypass Toxiproxy, trỏ thẳng vào mô hình Instruct trên Edge Node
STRATEGIC_AGENT_URL = "http://localhost:11435/api/generate"
MODEL_NAME = "qwen2.5:1.5b-instruct"
EPOCH_S = 30  # Chu kỳ 30 giây

def get_telemetry_summary():
    """Gom dữ liệu 30s thành JSON để cho LLM đọc"""
    data = metrics_cache.get_all()
    summary = {
        "latency_ms": {"cloud": data.get("cloud_latency_ms"), "edge": data.get("edge_latency_ms")},
        "bandwidth_kbps": {"cloud": data.get("cloud_bandwidth_kbps"), "edge": data.get("edge_bandwidth_kbps")},
        "queue_depth": {"cloud": data.get("cloud_queue_depth"), "edge": data.get("edge_queue_depth")},
        "compute_util": {"cloud_gpu": data.get("cloud_gpu_util"), "edge_cpu": data.get("edge_cpu_util")},
        "rps": {"current": data.get("current_rps"), "previous": data.get("previous_rps", 1.0)}
    }
    return json.dumps(summary, indent=2)

def rule_based_fallback(data):
    """Rule-based Fallback nếu AI trả lời sai hoặc Timeout"""
    edge_q = data.get("edge_queue_depth", 0)
    edge_cpu = data.get("edge_cpu_util", 0)
    c_lat, e_lat = data.get("cloud_latency_ms", 0), data.get("edge_latency_ms", 0)
    c_bw, e_bw = data.get("cloud_bandwidth_kbps", 100000), data.get("edge_bandwidth_kbps", 100000)
    curr_rps, prev_rps = data.get("current_rps", 0), max(1, data.get("previous_rps", 1))

    cond_edge = edge_q > 35 or edge_cpu > 85
    cond_deg = c_lat > 150 or e_lat > 150 or c_bw < 1000 or e_bw < 1000
    cond_burst = curr_rps > 1.5 * prev_rps
    
    conditions_met = sum([cond_edge, cond_deg, cond_burst])

    if conditions_met >= 2: return "STATE_CRITICAL"
    if cond_edge: return "STATE_EDGE_LOADED"
    if cond_deg: return "STATE_DEGRADED"
    if cond_burst: return "STATE_BURST"
    return "STATE_NORMAL"

def run_strategic_loop():
    print("Strategic Agent (Tier-1) đã khởi động. Chu kỳ: 30s.")
    while True:
        # Chờ gom đủ data cho 1 Epoch
        time.sleep(EPOCH_S)
        
        telemetry_json = get_telemetry_summary()
        prompt = f"""You are a system state classifier for an LLM inference orchestrator.
Read the telemetry summary and output EXACTLY ONE state label.

Valid outputs (one word only):
STATE_NORMAL | STATE_EDGE_LOADED | STATE_DEGRADED | STATE_BURST | STATE_CRITICAL

Rules:
- STATE_EDGE_LOADED: edge queue_depth > 35 OR edge cpu_util > 85
- STATE_DEGRADED: any latency_ms > 150 OR any bandwidth_kbps < 1000
- STATE_BURST: current_rps > 1.5 * previous_rps
- STATE_CRITICAL: two or more of the above conditions apply
- STATE_NORMAL: none of the above

Telemetry:
{telemetry_json}

Output the state label only."""

        payload = {"model": MODEL_NAME, "prompt": prompt, "stream": False}

        try:
            start_time = time.time()
            # Gọi LLM với Timeout 5s (Tránh treo hệ thống)
            res = requests.post(STRATEGIC_AGENT_URL, json=payload, timeout=15.0)
            res.raise_for_status()
            output = res.json().get("response", "").strip().upper()
            
            valid_states = list(ROUTING_TEMPLATES.keys())
            if output in valid_states:
                final_state = output
                print(f"[Tier-1] Qwen2.5-1.5B phân tích xong ({(time.time()-start_time):.2f}s): {final_state}")
            else:
                final_state = rule_based_fallback(metrics_cache.get_all())
                print(f"[Tier-1] LLM xuất ảo giác ('{output}'). Fallback -> {final_state}")

        except Exception as e:
            final_state = rule_based_fallback(metrics_cache.get_all())
            print(f"[Tier-1] Lỗi gọi LLM ({e}). Kích hoạt Fallback -> {final_state}")

        # Dán kết quả lên bảng chung cho Tier-2 dùng
        shared_state.update(final_state)

def start_strategic_agent():
    threading.Thread(target=run_strategic_loop, daemon=True).start()

# Hàm để chạy test độc lập
if __name__ == "__main__":
    # Để test nhanh, ta giảm Epoch xuống 5s thay vì 30s
    EPOCH_S = 5 
    # Bật dummy data reader để có số cho LLM đọc
    from toxiproxy_reader import start_toxiproxy_reader
    start_toxiproxy_reader()
    
    start_strategic_agent()
    while True: time.sleep(1)
