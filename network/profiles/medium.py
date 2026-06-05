"""Apply MEDIUM network profile via Toxiproxy REST API (Plan v5.0)."""

import os
import requests

PROFILES = {
    "cloud-proxy": {"latency": 120, "jitter": 25, "rate": 1250000},
    "edge-proxy": {"latency": 30, "jitter": 5, "rate": 6250000},
}


def apply_profile(api_url: str = None):
    api_url = api_url or os.environ.get("TOXIPROXY_API", "http://localhost:8474")
    base_url = f"{api_url}/proxies"
    for proxy_name, config in PROFILES.items():
        proxy_url = f"{base_url}/{proxy_name}/toxics"

        # Clear existing toxics
        try:
            active_toxics = requests.get(proxy_url, timeout=2).json()
            for toxic in active_toxics:
                requests.delete(f"{proxy_url}/{toxic['name']}", timeout=2)
        except Exception:
            pass

        # Apply latency
        requests.post(proxy_url, json={
            "name": "latency_downstream",
            "type": "latency",
            "stream": "downstream",
            "attributes": {"latency": config["latency"], "jitter": config["jitter"]},
        }, timeout=5)

        # Apply bandwidth
        requests.post(proxy_url, json={
            "name": "bandwidth_downstream",
            "type": "bandwidth",
            "stream": "downstream",
            "attributes": {"rate": config["rate"]},
        }, timeout=5)

        print(f"Applied MEDIUM profile to: {proxy_name}")


if __name__ == "__main__":
    apply_profile()
