import time
import requests
import subprocess
import threading
from metrics_cache import metrics_cache

# Control Plane URLs (Bypass Toxiproxy)
CLOUD_METRICS_URL = "http://localhost:11434"
EDGE_METRICS_URL = "http://localhost:11435"

def get_cpu_utilization():
    """Tính toán % CPU sử dụng dựa trên /proc/stat của Linux"""
    def read_cpu_stats():
        with open('/proc/stat', 'r') as f:
            lines = f.readlines()
        for line in lines:
            if line.startswith('cpu '):
                parts = [int(i) for i in line.split()[1:]]
                idle = parts[3] + parts[4] # idle + iowait
                total = sum(parts)
                return idle, total
        return 0, 0

    idle1, total1 = read_cpu_stats()
    time.sleep(0.1) # Lấy mẫu chênh lệch 100ms
    idle2, total2 = read_cpu_stats()
    
    total_delta = total2 - total1
    idle_delta = idle2 - idle1
    if total_delta == 0: return 0.0
    return 100.0 * (1.0 - idle_delta / total_delta)

def fetch_compute_util():
    """Luồng 1: Đọc GPU (Cloud) và CPU (Edge) mỗi 2 giây"""
    while True:
        try:
            # 1. Đọc GPU cho Cloud-node (Bỏ qua lỗi in ra màn hình nếu GPU đang ngủ)
            try:
                gpu_out = subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"], 
                    encoding="utf-8",
                    stderr=subprocess.DEVNULL # Chặn các log lỗi đỏ quạch từ hệ điều hành
                )
                gpu_util = float(gpu_out.strip())
                metrics_cache.update("cloud_gpu_util", gpu_util)
            except subprocess.CalledProcessError:
                # GPU Laptop đang ngủ (Mã lỗi 18) -> Tải mặc định là 0%
                metrics_cache.update("cloud_gpu_util", 0.0)

            # 2. Đọc CPU cho Edge-node
            cpu_util = get_cpu_utilization()
            metrics_cache.update("edge_cpu_util", round(cpu_util, 2))

        except Exception as e:
            print(f"Lỗi đọc Compute: {e}")
            
        time.sleep(2)

def fetch_queue_depth():
    """Luồng 2: Đọc trạng thái Ollama mỗi 0.5 giây"""
    while True:
        try:
            # Lưu ý: Ollama API tiêu chuẩn không trả về độ dài queue trực tiếp trong /api/ps.
            # Trong giai đoạn benchmark, gateway sẽ tự đo concurrent requests. 
            # Ở đây ta check API /api/ps để đảm bảo Control Plane connection đang sống (< 1ms).
            requests.get(f"{CLOUD_METRICS_URL}/api/ps", timeout=1)
            requests.get(f"{EDGE_METRICS_URL}/api/ps", timeout=1)
            
            # (Queue depth thực tế sẽ được Gateway Middleware bơm vào bộ nhớ cache sau khi nhận request)
            
        except Exception as e:
            print(f"Lỗi đọc Queue: {e}")
            
        time.sleep(0.5)

def start_compute_reader():
    threading.Thread(target=fetch_compute_util, daemon=True).start()
    threading.Thread(target=fetch_queue_depth, daemon=True).start()

# Cấu hình test độc lập
if __name__ == "__main__":
    print("Đang khởi động Compute Reader...")
    start_compute_reader()
    while True:
        data = metrics_cache.get_all()
        print(f"Tải Cloud (GPU): {data['cloud_gpu_util']}%")
        print(f"Tải Edge  (CPU): {data['edge_cpu_util']}%")
        print("-" * 30)
        time.sleep(2)
