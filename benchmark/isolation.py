import asyncio
import httpx
import os
import time
import re
import sys
from pathlib import Path

# Add network directory to path so we can import profiles
network_dir = Path(__file__).parent.parent / "network"
sys.path.append(str(network_dir))

from profiles import good, medium, bad

async def prepare_experiment_state(network_profile: str, strategy: str):
    """
    1. Update the Benchmark Strategy dynamically.
    2. Reset Toxiproxy and apply the target network profile.
    3. Wait for the Gateway inflight queues to drain (0 requests).
    4. Send a dummy warmup prompt to ensure models are loaded in memory.
    """
    print(f"--- Preparing Experiment State: {network_profile.upper()} profile / {strategy} strategy ---")
    
    # 1. Update Strategy
    gateway_url = os.environ.get("GATEWAY_URL", "http://localhost:8000")
    api_key = os.environ.get("CATS_API_KEY", "")
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{gateway_url}/admin/strategy", 
            json={"strategy": strategy},
            headers={"X-API-Key": api_key}
        )
        res.raise_for_status()
        print(f"✅ Updated Gateway Strategy to {strategy}")
    
    # 2. Apply Network Profile
    toxiproxy_api = os.environ.get("TOXIPROXY_API", "http://localhost:8474")
    if network_profile == "good":
        good.apply_profile(toxiproxy_api)
    elif network_profile == "medium":
        medium.apply_profile(toxiproxy_api)
    elif network_profile == "bad":
        bad.apply_profile(toxiproxy_api)
    else:
        raise ValueError(f"Unknown network profile: {network_profile}")
    print(f"✅ Applied network profile: {network_profile}")
    
    # 3. Wait for queues to drain (Gateway inflight = 0)
    orchestrator_url = os.environ.get("ORCHESTRATOR_URL", "http://localhost:8080")
    max_wait = 60
    start = time.time()
    
    print("⏳ Waiting for queues to drain...", end="", flush=True)
    async with httpx.AsyncClient() as client:
        while time.time() - start < max_wait:
            try:
                res = await client.get(f"{orchestrator_url}/metrics")
                res.raise_for_status()
                text = res.text
                
                # Parse prometheus output
                cloud_match = re.search(r'cats_gateway_inflight\{site="cloud"\} (\d+)', text)
                edge_match = re.search(r'cats_gateway_inflight\{site="edge"\} (\d+)', text)
                
                cloud_q = int(cloud_match.group(1)) if cloud_match else 0
                edge_q = int(edge_match.group(1)) if edge_match else 0
                
                if cloud_q == 0 and edge_q == 0:
                    print("\n✅ Inflight queues drained (Cloud: 0, Edge: 0).")
                    break
                
                print(".", end="", flush=True)
                await asyncio.sleep(2)
            except Exception as e:
                print(f"\n⚠️ Error polling metrics: {e}. Retrying...")
                await asyncio.sleep(2)
        else:
            raise TimeoutError("\n❌ Queues did not drain within max_wait time.")

    # 4. Dummy Warmup Prompts
    cloud_inference_url = os.environ.get("CLOUD_INFERENCE_URL", "http://localhost:11434")
    edge_inference_url = os.environ.get("EDGE_INFERENCE_URL", "http://localhost:11435")
    
    async def warmup(url, model):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                await client.post(f"{url}/api/generate", json={
                    "model": model,
                    "prompt": "hello, are you awake?",
                    "stream": False
                })
        except Exception as e:
            print(f"⚠️ Warmup failed for {url}: {e}")

    # Models must match compose/entrypoint
    cloud_model = os.environ.get("CLOUD_MODEL", "qwen2.5:7b-q4_K_M")
    edge_model = os.environ.get("EDGE_MODEL", "qwen2.5:1.8b-q4_K_M")
    
    print("⏳ Sending warmup prompts...")
    await asyncio.gather(
        warmup(cloud_inference_url, cloud_model),
        warmup(edge_inference_url, edge_model)
    )
    print("✅ Warmup complete. Experiment state ready.")

if __name__ == "__main__":
    # Example usage
    asyncio.run(prepare_experiment_state("good", "BASELINE-1"))
