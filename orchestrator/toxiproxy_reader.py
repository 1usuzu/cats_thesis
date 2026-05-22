import time
import requests
import threading
from metrics_cache import metrics_cache

TOXIPROXY_API = "http://localhost:8474/proxies"
INTERVAL_S = 5

def fetch_toxiproxy_metrics():
    while True:
        try:
            for site in ["cloud", "edge"]:
                proxy_name = f"{site}-proxy"
                response = requests.get(f"{TOXIPROXY_API}/{proxy_name}/toxics", timeout=2)
                toxics = response.json()
                
                # Cấu hình mặc định nếu mạng đang hoàn toàn bình thường (không có toxics)
                latency_ms = 0
                jitter_ms = 0
                bandwidth_kbps = 100000
                
                # Trích xuất dữ liệu từ các hiệu ứng mạng đang áp dụng
                for toxic in toxics:
                    if toxic["type"] == "latency":
                        latency_ms = toxic["attributes"].get("latency", 0)
                        jitter_ms = toxic["attributes"].get("jitter", 0)
                    elif toxic["type"] == "bandwidth":
                        rate = toxic["attributes"].get("rate", 12500000)
                        bandwidth_kbps = rate * 8 / 1000  # Chuyển đổi Bytes/s sang Kbps theo Plan
                        
                # Cập nhật vào kho lưu trữ trung tâm
                metrics_cache.update(f"{site}_latency_ms", latency_ms)
                metrics_cache.update(f"{site}_jitter_ms", jitter_ms)
                metrics_cache.update(f"{site}_bandwidth_kbps", bandwidth_kbps)
                
        except Exception as e:
            print(f"Lỗi khi đọc dữ liệu từ Toxiproxy: {e}")
            
        time.sleep(INTERVAL_S)

def start_toxiproxy_reader():
    thread = threading.Thread(target=fetch_toxiproxy_metrics, daemon=True)
    thread.start()
    
# Cấu hình để test thử file khi chạy độc lập
if __name__ == "__main__":
    print("Đang khởi động Toxiproxy Reader...")
    start_toxiproxy_reader()
    while True:
        data = metrics_cache.get_all()
        print(f"Mạng Cloud: Trễ {data['cloud_latency_ms']}ms | Băng thông {data['cloud_bandwidth_kbps']} Kbps")
        print(f"Mạng Edge : Trễ {data['edge_latency_ms']}ms | Băng thông {data['edge_bandwidth_kbps']} Kbps")
        print("-" * 50)
        time.sleep(5)
