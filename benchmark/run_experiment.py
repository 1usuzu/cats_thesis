import httpx
import time
import subprocess
import os

TOXIPROXY_URL = "http://localhost:8474"

def configure_network(scenario: str):
    print(f"Configuring network for scenario: {scenario}")
    
    # Reset all toxics
    with httpx.Client() as client:
        # Delete existing toxics
        for proxy in ["cloud-proxy", "edge-proxy"]:
            try:
                toxics = client.get(f"{TOXIPROXY_URL}/proxies/{proxy}/toxics").json()
                for t in toxics:
                    client.delete(f"{TOXIPROXY_URL}/proxies/{proxy}/toxics/{t['name']}")
            except Exception:
                pass

        if scenario == "NORMAL":
            pass # No toxics
            
        elif scenario == "EDGE_LOADED":
            # Just let Locust send burst to edge or simulate it via orchestrator config,
            # but Toxiproxy doesn't control CPU. We can simulate it by adding latency to edge
            pass 
            
        elif scenario == "DEGRADED":
            # Add 200ms latency to both
            for proxy in ["cloud-proxy", "edge-proxy"]:
                client.post(f"{TOXIPROXY_URL}/proxies/{proxy}/toxics", json={
                    "name": "latency",
                    "type": "latency",
                    "stream": "downstream",
                    "toxicity": 1.0,
                    "attributes": {"latency": 200, "jitter": 20}
                })
                
        elif scenario == "MULTI_FAIL":
            # Cloud drops 50% packets, Edge 500ms latency
            client.post(f"{TOXIPROXY_URL}/proxies/cloud-proxy/toxics", json={
                "name": "timeout",
                "type": "timeout",
                "stream": "downstream",
                "toxicity": 0.5,
                "attributes": {"timeout": 1000}
            })
            client.post(f"{TOXIPROXY_URL}/proxies/edge-proxy/toxics", json={
                "name": "latency",
                "type": "latency",
                "stream": "downstream",
                "toxicity": 1.0,
                "attributes": {"latency": 500, "jitter": 50}
            })

def run_locust(scenario: str, users: int, spawn_rate: int, duration: str):
    print(f"Running Locust: {users} users, {spawn_rate} spawn rate, {duration}")
    os.makedirs("results", exist_ok=True)
    cmd = [
        "locust",
        "-f", "benchmark/locustfile.py",
        "--headless",
        "-u", str(users),
        "-r", str(spawn_rate),
        "--run-time", duration,
        "--host", "http://localhost:8000",
        "--csv", f"results/locust_{scenario}"
    ]
    subprocess.run(cmd)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=str, default="NORMAL")
    parser.add_argument("--users", type=int, default=50)
    parser.add_argument("--rate", type=int, default=10)
    parser.add_argument("--duration", type=str, default="2m")
    args = parser.parse_args()

    configure_network(args.scenario)
    run_locust(args.scenario, args.users, args.rate, args.duration)
