import threading

class MetricsCache:
    def __init__(self):
        # Sử dụng RLock để tránh đụng độ dữ liệu khi nhiều luồng cùng đọc/ghi
        self.lock = threading.RLock()
        self.data = {
            "cloud_latency_ms": 0,
            "cloud_jitter_ms": 0,
            "cloud_bandwidth_kbps": 100000,
            "cloud_queue_depth": 0,
            "cloud_gpu_util": 0,
            "cloud_ttft_ms_avg": 0,
            
            "edge_latency_ms": 0,
            "edge_jitter_ms": 0,
            "edge_bandwidth_kbps": 100000,
            "edge_queue_depth": 0,
            "edge_cpu_util": 0,
            "edge_ttft_ms_avg": 0,
            
            "current_rps": 0.0,
            "previous_rps": 0.0
        }

    def update(self, key, value):
        with self.lock:
            if key in self.data:
                self.data[key] = value

    def get_all(self):
        with self.lock:
            return self.data.copy()

# Khởi tạo đối tượng toàn cục để các module khác cùng import
metrics_cache = MetricsCache()
