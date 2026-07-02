import asyncio
import json
import random

import httpx
import structlog
from config import settings
from metrics_cache import metrics_cache
from shared_state import shared_state

logger = structlog.get_logger("tuning_agent")

# Base boundaries
MIN_WEIGHT = 0.10
MAX_WEIGHT = 0.60

async def call_strategic_agent_for_tuning(current_state: str, metrics: dict, current_weights: dict):
    """Consult the LLM (Tier-1) for a second opinion on parameter tuning."""
    api_url = f"{settings.strategic_agent_url}/api/generate"
    prompt = f"""You are an AI supervisor for network routing.
Current State: {current_state}
Current Weights: {json.dumps(current_weights)}
Metrics: {json.dumps({k: v for k, v in metrics.items() if 'latency' in k or 'inflight' in k})}

Based on these metrics, suggest a new set of weights for w_latency, w_queue, and w_compute.
The sum doesn't need to be 1.0, but each must be between 0.1 and 0.6.
If latency is high, increase w_latency. If queues are high, increase w_queue.
Return ONLY a JSON object: {{"w_latency": float, "w_queue": float, "w_compute": float}}.
No markdown, no explanation.
"""
    payload = {"model": settings.strategic_agent_model, "prompt": prompt, "stream": False, "format": "json"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(api_url, json=payload)
            res.raise_for_status()
            response_text = res.json().get("response", "").strip()

            proposed = json.loads(response_text)

            # Bounds checking
            w_lat = max(MIN_WEIGHT, min(MAX_WEIGHT, float(proposed.get("w_latency", current_weights["w_latency"]))))
            w_queue = max(MIN_WEIGHT, min(MAX_WEIGHT, float(proposed.get("w_queue", current_weights["w_queue"]))))
            w_comp = max(MIN_WEIGHT, min(MAX_WEIGHT, float(proposed.get("w_compute", current_weights["w_compute"]))))

            return {"w_latency": w_lat, "w_queue": w_queue, "w_compute": w_comp}
    except Exception as e:
        logger.warning("LLM Tuning failed, falling back to heuristics", error=str(e))
        return None

def apply_heuristics(state: str, current_weights: dict) -> dict:
    """Fast, safe rule-based parameter tuning."""
    w_lat = current_weights.get("w_latency", settings.w_latency)
    w_queue = current_weights.get("w_queue", settings.w_queue)
    w_comp = current_weights.get("w_compute", settings.w_compute)

    step = 0.05

    if state == "STATE_EDGE_LOADED":
        w_queue = min(MAX_WEIGHT, w_queue + step)
        w_comp = max(MIN_WEIGHT, w_comp - step)
    elif state == "STATE_DEGRADED":
        w_lat = min(MAX_WEIGHT, w_lat + step)
    elif state == "STATE_BURST":
        w_queue = min(MAX_WEIGHT, w_queue + step)
        w_lat = max(MIN_WEIGHT, w_lat - step)
    elif state == "STATE_NORMAL":
        # Slowly decay back to defaults
        w_lat += (settings.w_latency - w_lat) * 0.1
        w_queue += (settings.w_queue - w_queue) * 0.1
        w_comp += (settings.w_compute - w_comp) * 0.1

    return {
        "w_latency": round(w_lat, 3),
        "w_queue": round(w_queue, 3),
        "w_compute": round(w_comp, 3)
    }

async def run_tuning_loop():
    logger.info("Starting Tuning Agent (Rule-based + LLM)")

    while True:
        await asyncio.sleep(30.0) # Tune every 30 seconds

        current_state, _ = shared_state.get()
        metrics = metrics_cache.get_all()
        current_weights = shared_state.get_dynamic_weights()

        # 1. Generate new weights via Heuristics
        new_weights = apply_heuristics(current_state, current_weights)

        # 2. Every 4th cycle (2 minutes), ask LLM for strategic tuning
        if random.random() < 0.25:
            llm_weights = await call_strategic_agent_for_tuning(current_state, metrics, current_weights)
            if llm_weights:
                new_weights = llm_weights
                logger.info("Applied LLM-assisted tuning weights", weights=new_weights)

        # 3. Apply to Sandbox
        shared_state.set_sandbox_weights(
            w_lat=new_weights["w_latency"],
            w_queue=new_weights["w_queue"],
            w_comp=new_weights["w_compute"]
        )

        # 4. Activate Canary (10% traffic will use sandbox_weights)
        shared_state.set_canary_active(True)

        # 5. For now, stop auto-promotion and log that manual review is required.
        logger.info("Canary tuning active. Manual promotion required pending validation.", sandbox=new_weights)

        await asyncio.sleep(15.0)

        # Do not automatically promote weights without validation
        # shared_state.update_dynamic_weights(...)
        shared_state.set_canary_active(False)
        logger.info("Sandbox canary evaluation ended. Awaiting validation pipeline for promotion.", active_weights=new_weights)


def start_tuning_agent():
    return asyncio.create_task(run_tuning_loop())
