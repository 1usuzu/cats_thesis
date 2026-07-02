import json
import os
import random
from pathlib import Path

from dotenv import load_dotenv
from locust import HttpUser, between, events, task

load_dotenv(Path(__file__).parent.parent / ".env")

# Ensure prompts exist, do not silently fallback
DATA_PATH = Path(__file__).parent / "data" / "prompts.json"
if not DATA_PATH.exists():
    raise FileNotFoundError(f"CRITICAL ERROR: Dataset not found at {DATA_PATH}. Benchmark must use a real dataset.")

with open(DATA_PATH, "r") as f:
    PROMPTS = json.load(f)


class CATSUser(HttpUser):
    wait_time = between(0.5, 1.5)

    def on_start(self):
        self.client.headers.update({"X-API-Key": os.getenv("CATS_API_KEY", "")})

    @task
    def send_chat(self):
        req_data = random.choice(PROMPTS)

        with self.client.post("/v1/chat", json=req_data, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "data" in data and "route" in data["data"]:
                    route = data["data"]["route"]["site"]
                    # Record custom metric for routing decision
                    events.request.fire(
                        request_type="ROUTE",
                        name=f"Routed to {route}",
                        response_time=data["data"]["route"]["total_inference_ms"],
                        response_length=len(response.text),
                        exception=None,
                        context={},
                    )

                    # Record fallback metrics explicitly
                    if data.get("meta", {}).get("routing_analysis", {}).get("forced_fallback"):
                        events.request.fire(
                            request_type="ROUTE_FALLBACK",
                            name=f"Forced Fallback to {route}",
                            response_time=data["data"]["route"]["total_inference_ms"],
                            response_length=len(response.text),
                            exception=None,
                            context={},
                        )
                response.success()
            else:
                response.failure(f"Failed with status code {response.status_code}")
