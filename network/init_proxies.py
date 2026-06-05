"""Initialize Toxiproxy proxies and apply default GOOD profile on startup."""

import json
import os
import time
import sys
from pathlib import Path

import requests

TOXIPROXY_API = os.environ.get("TOXIPROXY_API", "http://toxiproxy:8474")
INIT_FILE = Path(__file__).with_name("toxiproxy_init.json")
MAX_RETRIES = 30
RETRY_DELAY_S = 2

GOOD_PROFILE = {
    "cloud-proxy": {"latency": 15, "jitter": 3, "rate": 12500000},
    "edge-proxy": {"latency": 5, "jitter": 1, "rate": 12500000},
}


def wait_for_toxiproxy():
    for i in range(MAX_RETRIES):
        try:
            resp = requests.get(f"{TOXIPROXY_API}/version", timeout=2)
            if resp.status_code == 200:
                print(f"Toxiproxy ready (v{resp.text.strip()})")
                return True
        except requests.ConnectionError:
            pass
        print(f"Waiting for Toxiproxy... ({i + 1}/{MAX_RETRIES})")
        time.sleep(RETRY_DELAY_S)
    return False


def create_proxies():
    with open(INIT_FILE) as f:
        proxies = json.load(f)

    for proxy in proxies:
        name = proxy["name"]
        try:
            resp = requests.get(f"{TOXIPROXY_API}/proxies/{name}", timeout=2)
            if resp.status_code == 200:
                print(f"Proxy '{name}' already exists, skipping.")
                continue
        except requests.ConnectionError:
            pass

        resp = requests.post(f"{TOXIPROXY_API}/proxies", json=proxy, timeout=5)
        resp.raise_for_status()
        print(f"Created proxy: {name} ({proxy['listen']} -> {proxy['upstream']})")


def apply_good_profile():
    for proxy_name, config in GOOD_PROFILE.items():
        toxics_url = f"{TOXIPROXY_API}/proxies/{proxy_name}/toxics"

        # Clear existing toxics
        try:
            existing = requests.get(toxics_url, timeout=2).json()
            for toxic in existing:
                requests.delete(f"{toxics_url}/{toxic['name']}", timeout=2)
        except Exception:
            pass

        # Apply latency toxic
        requests.post(toxics_url, json={
            "name": "latency_downstream",
            "type": "latency",
            "stream": "downstream",
            "attributes": {"latency": config["latency"], "jitter": config["jitter"]},
        }, timeout=5)

        # Apply bandwidth toxic
        requests.post(toxics_url, json={
            "name": "bandwidth_downstream",
            "type": "bandwidth",
            "stream": "downstream",
            "attributes": {"rate": config["rate"]},
        }, timeout=5)

        print(f"Applied GOOD profile to {proxy_name}")


if __name__ == "__main__":
    if not wait_for_toxiproxy():
        print("ERROR: Toxiproxy not reachable after retries.")
        sys.exit(1)

    create_proxies()
    apply_good_profile()
    print("Toxiproxy initialization complete.")
