import requests

TOXIPROXY_API = "http://localhost:8474/proxies"

# Cấu hình PROFILE GOOD (Theo Master Plan v5.0)
# Lưu ý: Toxiproxy tính rate bằng Bytes/sec. 100 Mbps = 12,500,000 bytes/s
PROFILES = {
    "cloud-proxy": {"latency": 15, "jitter": 3, "rate": 12500000},
    "edge-proxy": {"latency": 5, "jitter": 1, "rate": 12500000}
}

def apply_profile():
    for proxy_name, config in PROFILES.items():
        proxy_url = f"{TOXIPROXY_API}/{proxy_name}/toxics"
        
        # 1. Xóa các hiệu ứng cũ (nếu có) để không bị cộng dồn
        try:
            active_toxics = requests.get(proxy_url).json()
            for toxic in active_toxics:
                requests.delete(f"{proxy_url}/{toxic['name']}")
        except:
            pass
            
        # 2. Bơm hiệu ứng Độ trễ (Latency & Jitter)
        requests.post(proxy_url, json={
            "name": "latency_downstream",
            "type": "latency",
            "stream": "downstream",
            "attributes": {"latency": config["latency"], "jitter": config["jitter"]}
        })
        
        # 3. Bơm hiệu ứng Băng thông (Bandwidth)
        requests.post(proxy_url, json={
            "name": "bandwidth_downstream",
            "type": "bandwidth",
            "stream": "downstream",
            "attributes": {"rate": config["rate"]}
        })
        
        print(f"Đã áp dụng thành công PROFILE GOOD cho: {proxy_name}")

if __name__ == "__main__":
    apply_profile()
