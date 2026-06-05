"""Async strategic agent loop for LLM classification."""

import asyncio
import json
import time

import httpx
import structlog
from metrics_cache import metrics_cache
from shared_state import shared_state
from routing_templates import ROUTING_TEMPLATES
from config import settings

logger = structlog.get_logger("strategic_agent")


def get_telemetry_summary() -> str:
    data = metrics_cache.get_all()
    summary = {
        "latency_ms": {
            "cloud": data.get("cloud_latency_ms"),
            "edge": data.get("edge_latency_ms"),
        },
        "bandwidth_kbps": {
            "cloud": data.get("cloud_bandwidth_kbps"),
            "edge": data.get("edge_bandwidth_kbps"),
        },
        "gateway_inflight": {
            "cloud": data.get("cloud_gateway_inflight"),
            "edge": data.get("edge_gateway_inflight"),
        },
        "compute_util": {
            "cloud_gpu": data.get("cloud_gpu_util"),
            "edge_cpu": data.get("edge_cpu_util"),
        },
        "rps": {
            "current": data.get("current_rps"),
            "previous": data.get("previous_rps", 1.0),
        },
    }
    return json.dumps(summary, indent=2)


def rule_based_fallback(data: dict) -> str:
    edge_inflight = data.get("edge_gateway_inflight", 0)
    edge_cpu = data.get("edge_cpu_util", 0)
    c_lat = data.get("cloud_latency_ms", 0)
    e_lat = data.get("edge_latency_ms", 0)
    c_bw = data.get("cloud_bandwidth_kbps", 100000)
    e_bw = data.get("edge_bandwidth_kbps", 100000)
    curr_rps = data.get("current_rps", 0)
    prev_rps = max(1, data.get("previous_rps", 1))

    cond_edge = edge_inflight > settings.state_edge_loaded_inflight or edge_cpu > settings.state_edge_loaded_cpu
    cond_deg = (
        c_lat > settings.state_degraded_latency_ms
        or e_lat > settings.state_degraded_latency_ms
        or c_bw < settings.state_degraded_bandwidth_kbps
        or e_bw < settings.state_degraded_bandwidth_kbps
    )
    cond_burst = curr_rps > settings.state_burst_ratio * prev_rps

    conditions_met = sum([cond_edge, cond_deg, cond_burst])

    if conditions_met >= 2:
        return "STATE_CRITICAL"
    if cond_edge:
        return "STATE_EDGE_LOADED"
    if cond_deg:
        return "STATE_DEGRADED"
    if cond_burst:
        return "STATE_BURST"
    return "STATE_NORMAL"


async def run_strategic_loop():
    api_url = f"{settings.strategic_agent_url}/api/generate"
    logger.info("Strategic Agent started", epoch_s=settings.strategic_epoch_s, model=settings.strategic_agent_model)

    async with httpx.AsyncClient(timeout=settings.strategic_timeout_s) as client:
        while True:
            await asyncio.sleep(settings.strategic_epoch_s)

            telemetry_json = get_telemetry_summary()
            prompt = f"""You are a system state classifier for an LLM inference orchestrator.
Read the telemetry summary and output EXACTLY ONE state label.

Valid outputs (one word only):
STATE_NORMAL | STATE_EDGE_LOADED | STATE_DEGRADED | STATE_BURST | STATE_CRITICAL

Rules:
- STATE_EDGE_LOADED: edge gateway_inflight > {settings.state_edge_loaded_inflight} OR edge cpu_util > {settings.state_edge_loaded_cpu}
- STATE_DEGRADED: any latency_ms > {settings.state_degraded_latency_ms} OR any bandwidth_kbps < {settings.state_degraded_bandwidth_kbps}
- STATE_BURST: current_rps > {settings.state_burst_ratio} * previous_rps
- STATE_CRITICAL: two or more of the above conditions apply
- STATE_NORMAL: none of the above

Telemetry:
{telemetry_json}

Output the state label only."""

            payload = {"model": settings.strategic_agent_model, "prompt": prompt, "stream": False}

            start_time = time.time()
            try:
                res = await client.post(api_url, json=payload)
                res.raise_for_status()
                output = res.json().get("response", "").strip().upper()
                elapsed = round(time.time() - start_time, 2)

                valid_states = list(ROUTING_TEMPLATES.keys())
                if output in valid_states:
                    final_state = output
                    logger.info("LLM classification successful", state=final_state, elapsed_s=elapsed)
                else:
                    final_state = rule_based_fallback(metrics_cache.get_all())
                    logger.warning("LLM hallucination", output=output, fallback=final_state)

            except asyncio.CancelledError:
                break
            except Exception as e:
                final_state = rule_based_fallback(metrics_cache.get_all())
                logger.error("LLM request failed", error=str(e), fallback=final_state)

            shared_state.update(final_state)


def start_strategic_agent():
    return asyncio.create_task(run_strategic_loop())
