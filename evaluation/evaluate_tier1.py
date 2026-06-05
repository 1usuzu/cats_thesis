import asyncio
import httpx
import json

TEST_CASES = [
    {
        "name": "Normal State",
        "telemetry": {
            "latency_ms": {"cloud": 10, "edge": 5},
            "bandwidth_kbps": {"cloud": 100000, "edge": 100000},
            "gateway_inflight": {"cloud": 5, "edge": 0},
            "compute_util": {"cloud_gpu": 20, "edge_cpu": 10},
            "rps": {"current": 5, "previous": 5}
        },
        "expected": "STATE_NORMAL"
    },
    {
        "name": "Edge Loaded",
        "telemetry": {
            "latency_ms": {"cloud": 10, "edge": 5},
            "bandwidth_kbps": {"cloud": 100000, "edge": 100000},
            "gateway_inflight": {"cloud": 5, "edge": 25},
            "compute_util": {"cloud_gpu": 20, "edge_cpu": 85},
            "rps": {"current": 5, "previous": 5}
        },
        "expected": "STATE_EDGE_LOADED"
    },
    {
        "name": "Degraded Network",
        "telemetry": {
            "latency_ms": {"cloud": 200, "edge": 5},
            "bandwidth_kbps": {"cloud": 1000, "edge": 100000},
            "gateway_inflight": {"cloud": 5, "edge": 0},
            "compute_util": {"cloud_gpu": 20, "edge_cpu": 10},
            "rps": {"current": 5, "previous": 5}
        },
        "expected": "STATE_DEGRADED"
    },
    {
        "name": "Traffic Burst",
        "telemetry": {
            "latency_ms": {"cloud": 10, "edge": 5},
            "bandwidth_kbps": {"cloud": 100000, "edge": 100000},
            "gateway_inflight": {"cloud": 5, "edge": 0},
            "compute_util": {"cloud_gpu": 20, "edge_cpu": 10},
            "rps": {"current": 50, "previous": 10}
        },
        "expected": "STATE_BURST"
    },
    {
        "name": "Critical (Burst + Degraded)",
        "telemetry": {
            "latency_ms": {"cloud": 200, "edge": 5},
            "bandwidth_kbps": {"cloud": 100000, "edge": 100000},
            "gateway_inflight": {"cloud": 5, "edge": 0},
            "compute_util": {"cloud_gpu": 20, "edge_cpu": 10},
            "rps": {"current": 50, "previous": 10}
        },
        "expected": "STATE_CRITICAL"
    }
]

async def evaluate():
    correct = 0
    total = len(TEST_CASES)
    
    # Needs Edge Node running Ollama for the strategic agent model
    url = "http://localhost:11435/api/generate"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, case in enumerate(TEST_CASES):
            prompt = f"""You are a system state classifier for an LLM inference orchestrator.
Read the telemetry summary and output EXACTLY ONE state label.

Valid outputs (one word only):
STATE_NORMAL | STATE_EDGE_LOADED | STATE_DEGRADED | STATE_BURST | STATE_CRITICAL

Rules:
- STATE_EDGE_LOADED: edge gateway_inflight > 20 OR edge cpu_util > 80
- STATE_DEGRADED: any latency_ms > 100 OR any bandwidth_kbps < 50000
- STATE_BURST: current_rps > 3 * previous_rps
- STATE_CRITICAL: two or more of the above conditions apply
- STATE_NORMAL: none of the above

Telemetry:
{json.dumps(case['telemetry'], indent=2)}

Output the state label only."""

            try:
                res = await client.post(url, json={
                    "model": "qwen2.5:1.5b-instruct",
                    "prompt": prompt,
                    "stream": False
                })
                res.raise_for_status()
                output = res.json().get("response", "").strip().upper()
                
                # Check accuracy
                match = case['expected'] in output
                if match:
                    correct += 1
                
                print(f"[{'PASS' if match else 'FAIL'}] {case['name']} | Expected: {case['expected']} | Got: {output}")
            except Exception as e:
                print(f"[ERROR] {case['name']} failed: {e}")
                
    accuracy = (correct / total) * 100
    print(f"\nOverall Tier-1 Accuracy: {accuracy}% ({correct}/{total})")

if __name__ == "__main__":
    asyncio.run(evaluate())
