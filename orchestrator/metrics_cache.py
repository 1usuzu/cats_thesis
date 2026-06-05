import threading
import time


class MetricsCache:
    def __init__(self):
        self._cache = {}
        self._lock = threading.RLock()
        
        # Initialize default values
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
            "previous_rps": 0.0,
            "cloud_total_inference_ms_avg": 0.0,
            "edge_total_inference_ms_avg": 0.0,
        }
        for k, v in defaults.items():
            self.update(k, v)

    def update(self, key: str, value):
        with self._lock:
            # Special handling for RPS tracking burst
            if key == "current_rps":
                prev = self._cache.get("current_rps", {}).get("value", 0.0)
                if prev > 0:
                    self._cache["previous_rps"] = {"value": prev, "timestamp": time.time()}
                    
            self._cache[key] = {"value": value, "timestamp": time.time()}

    def get(self, key: str, default=None):
        with self._lock:
            entry = self._cache.get(key)
            if not entry:
                return default
            return entry["value"]

    def get_all(self):
        with self._lock:
            return {k: v["value"] for k, v in self._cache.items()}

    def get_site_metrics(self, site: str):
        with self._lock:
            return {
                k: v["value"] 
                for k, v in self._cache.items() 
                if k.startswith(f"{site}_")
            }

    def to_prometheus_format(self) -> str:
        with self._lock:
            lines = []
            
            # Network Latency
            lines.append("# HELP cats_network_latency_ms Declared network latency in ms")
            lines.append("# TYPE cats_network_latency_ms gauge")
            lines.append(f"cats_network_latency_ms{{site=\"cloud\"}} {self.get('cloud_latency_ms', 0)}")
            lines.append(f"cats_network_latency_ms{{site=\"edge\"}} {self.get('edge_latency_ms', 0)}")
            
            # Network Bandwidth
            lines.append("# HELP cats_network_bandwidth_kbps Declared network bandwidth in kbps")
            lines.append("# TYPE cats_network_bandwidth_kbps gauge")
            lines.append(f"cats_network_bandwidth_kbps{{site=\"cloud\"}} {self.get('cloud_bandwidth_kbps', 0)}")
            lines.append(f"cats_network_bandwidth_kbps{{site=\"edge\"}} {self.get('edge_bandwidth_kbps', 0)}")
            
            # Gateway In-Flight
            lines.append("# HELP cats_gateway_inflight In-flight requests at the gateway")
            lines.append("# TYPE cats_gateway_inflight gauge")
            lines.append(f"cats_gateway_inflight{{site=\"cloud\"}} {self.get('cloud_gateway_inflight', 0)}")
            lines.append(f"cats_gateway_inflight{{site=\"edge\"}} {self.get('edge_gateway_inflight', 0)}")
            
            # Compute Utilization
            lines.append("# HELP cats_compute_gpu_util_pct Cloud GPU Utilization percentage")
            lines.append("# TYPE cats_compute_gpu_util_pct gauge")
            lines.append(f"cats_compute_gpu_util_pct {self.get('cloud_gpu_util', 0)}")
            
            lines.append("# HELP cats_compute_cpu_util_pct Edge CPU Utilization percentage")
            lines.append("# TYPE cats_compute_cpu_util_pct gauge")
            lines.append(f"cats_compute_cpu_util_pct {self.get('edge_cpu_util', 0)}")
            
            # Request Rate
            lines.append("# HELP cats_gateway_rps Requests per second at the gateway")
            lines.append("# TYPE cats_gateway_rps gauge")
            lines.append(f"cats_gateway_rps {self.get('current_rps', 0)}")
            
            # Total Inference Time (moving average from gateway)
            lines.append("# HELP cats_compute_total_inference_ms Total inference time in ms")
            lines.append("# TYPE cats_compute_total_inference_ms gauge")
            lines.append(f"cats_compute_total_inference_ms{{site=\"cloud\"}} {self.get('cloud_total_inference_ms_avg', 0)}")
            lines.append(f"cats_compute_total_inference_ms{{site=\"edge\"}} {self.get('edge_total_inference_ms_avg', 0)}")
            
            return "\n".join(lines) + "\n"


metrics_cache = MetricsCache()
