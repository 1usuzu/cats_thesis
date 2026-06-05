import os
import sys
import asyncio
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# Import isolation logic
from isolation import prepare_experiment_state

PROFILES = ["good", "medium", "bad"]
LOADS = ["low", "high"]
STRATEGIES = ["PROPOSED", "BASELINE-1", "BASELINE-2", "BASELINE-3"]

# Ensure results directory exists
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# Locust config per load
LOAD_CONFIGS = {
    "low": {"users": 5, "spawn_rate": 1, "duration": "30s"},
    "high": {"users": 50, "spawn_rate": 10, "duration": "1m"},
}

async def run_benchmark():
    total_runs = len(PROFILES) * len(LOADS) * len(STRATEGIES)
    current_run = 0
    
    print("======================================================")
    print(f"Starting CATS 24-Run Benchmark Matrix")
    print(f"Total scenarios: {total_runs}")
    print("======================================================")
    
    for profile in PROFILES:
        for load in LOADS:
            for strategy in STRATEGIES:
                current_run += 1
                print(f"\n--- Running scenario {current_run}/{total_runs} ---")
                print(f"Profile: {profile.upper()} | Load: {load.upper()} | Strategy: {strategy}")
                
                # 1. Isolate and prepare the state
                try:
                    await prepare_experiment_state(network_profile=profile, strategy=strategy)
                except Exception as e:
                    print(f"[ERROR] Failed to prepare experiment state: {e}")
                    print("[WARNING] Skipping to next scenario...")
                    continue
                
                # 2. Run Locust
                config = LOAD_CONFIGS[load]
                csv_prefix = RESULTS_DIR / f"benchmark_{profile}_{load}_{strategy}"
                locust_cmd = [
                    sys.executable, "-m", "locust",
                    "-f", "locustfile.py",
                    "--headless",
                    "--host", "http://localhost:8000",
                    "-u", str(config["users"]),
                    "-r", str(config["spawn_rate"]),
                    "-t", config["duration"],
                    "--csv", str(csv_prefix)
                ]
                
                print(f"[INFO] Running Locust load test ({config['duration']})...")
                start_time = time.time()
                try:
                    # Run locust and capture output to prevent terminal spam
                    # We give a generous timeout of (duration + 60s) for teardown
                    timeout_s = 90 if load == "low" else 150
                    result = subprocess.run(
                        locust_cmd,
                        cwd=Path(__file__).parent,
                        capture_output=True,
                        text=True,
                        timeout=timeout_s
                    )
                    
                    if result.returncode in [0,1]:
                        elapsed = round(time.time() - start_time, 2)
                        print(f"[SUCCESS] Load test completed successfully in {elapsed}s")
                    else:
                        print(f"[ERROR] Locust failed with return code {result.returncode}")
                        print(f"Stderr tail: {result.stderr[-500:]}")
                except subprocess.TimeoutExpired:
                    print(f"[ERROR] Locust process timed out after {timeout_s}s")
                except Exception as e:
                    print(f"[ERROR] Unexpected error running Locust: {e}")
                
                # Brief sleep between runs to let OS sockets close
                print("[INFO] Waiting 5 seconds before next scenario...")
                time.sleep(5)

    print("\n======================================================")
    print("Benchmark Matrix Complete!")
    print(f"Results saved in: {RESULTS_DIR}")
    print("======================================================")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
