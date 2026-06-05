import json
import os
import random
from pathlib import Path
from dotenv import load_dotenv
from locust import HttpUser, task, between, events

load_dotenv(Path(__file__).parent.parent / ".env")

# Load prompts
try:
    with open("data/prompts.json", "r") as f:
        PROMPTS = json.load(f)
except FileNotFoundError:
    PROMPTS = [{"prompt": "Hello", "request_tag": "default"}]

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
                response.success()
            else:
                response.failure(f"Failed with status code {response.status_code}")
