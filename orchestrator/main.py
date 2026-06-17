import time
import asyncio
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from metrics_cache import metrics_cache
from toxiproxy_reader import start_toxiproxy_reader
from compute_reader import start_compute_reader
from strategic_agent import start_strategic_agent
from tactical_agent import compute_cats_score, check_opa_safety, init_opa_client, close_opa_client
from shared_state import shared_state
from cost_agent import run_cost_loop
from tuning_agent import start_tuning_agent
from config import settings
from classifier import classify_prompt_complexity

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger("orchestrator")

background_tasks = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize shared OPA client
    init_opa_client()

    # Start readers
    task_tox = start_toxiproxy_reader()
    tasks_comp = start_compute_reader()
    task_strat = start_strategic_agent()
    task_cost = asyncio.create_task(run_cost_loop())
    task_tune = start_tuning_agent()
    
    background_tasks.append(task_tox)
    background_tasks.extend(tasks_comp)
    background_tasks.append(task_strat)
    background_tasks.append(task_cost)
    background_tasks.append(task_tune)
    
    logger.info("Orchestrator background readers started")
    yield
    
    logger.info("Orchestrator shutting down, cancelling tasks")
    for t in background_tasks:
        t.cancel()
    await close_opa_client()


app = FastAPI(
    title="CATS Orchestrator Service",
    version="1.0.0",
    description="Two-tier agentic orchestrator: Tier-1 Strategic + Tier-2 Tactical + OPA Safety Gate",
    lifespan=lifespan,
)


class RouteRequest(BaseModel):
    prompt: str
    request_tag: str = "default"
    cb_states: dict[str, str] = {"cloud": "CLOSED", "edge": "CLOSED"}


class GatewayMetrics(BaseModel):
    cloud_inflight: int
    edge_inflight: int
    current_rps: float
    cloud_total_inference_ms: float
    edge_total_inference_ms: float

class GatewayResult(BaseModel):
    site: str
    success: bool

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready():
    data = metrics_cache.get_all()
    state, _ = shared_state.get()
    return {
        "status": "ready",
        "tier1_state": state,
        "metrics_populated": data.get("cloud_bandwidth_kbps", 0) > 0,
    }


@app.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """Prometheus metrics endpoint."""
    return metrics_cache.to_prometheus_format()


@app.get("/telemetry")
async def telemetry_json():
    """Returns telemetry data as JSON for the UI dashboard."""
    data = metrics_cache.get_all()
    state, _ = shared_state.get()
    
    return {
        "metrics": data,
        "tier1_state": state
    }



@app.post("/metrics/update")
async def update_gateway_metrics(metrics: GatewayMetrics):
    metrics_cache.update("cloud_gateway_inflight", metrics.cloud_inflight)
    metrics_cache.update("edge_gateway_inflight", metrics.edge_inflight)
    metrics_cache.update("current_rps", metrics.current_rps)
    if metrics.cloud_total_inference_ms > 0:
        metrics_cache.update("cloud_total_inference_ms_avg", metrics.cloud_total_inference_ms)
    if metrics.edge_total_inference_ms > 0:
        metrics_cache.update("edge_total_inference_ms_avg", metrics.edge_total_inference_ms)
    return {"status": "ok"}

@app.post("/metrics/update_result")
async def update_gateway_result(res: GatewayResult):
    data = metrics_cache.get_all()
    if res.site == "cloud":
        if res.success:
            metrics_cache.update("cloud_success_count", data.get("cloud_success_count", 0) + 1)
        else:
            metrics_cache.update("cloud_failure_count", data.get("cloud_failure_count", 0) + 1)
    else:
        if res.success:
            metrics_cache.update("edge_success_count", data.get("edge_success_count", 0) + 1)
        else:
            metrics_cache.update("edge_failure_count", data.get("edge_failure_count", 0) + 1)
    return {"status": "ok"}


@app.post("/route")
async def get_routing_decision(req: RouteRequest):
    start_time = time.perf_counter()

    current_state, current_template = shared_state.get()

    computed_tag = req.request_tag
    if computed_tag == "default" or not computed_tag:
        computed_tag = classify_prompt_complexity(req.prompt)

    cloud_cats, cloud_cost_mod = compute_cats_score("cloud", computed_tag)
    edge_cats, edge_cost_mod = compute_cats_score("edge", computed_tag)

    cloud_final = cloud_cats * current_template.get("cloud", 0.5)
    edge_final = edge_cats * current_template.get("edge", 0.5)

    cloud_open = req.cb_states.get("cloud") == "OPEN"
    edge_open = req.cb_states.get("edge") == "OPEN"

    if cloud_open and edge_open:
        decision_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "decision": "none",
            "cats_scores": {"cloud": cloud_cats, "edge": edge_cats},
            "final_scores": {"cloud": cloud_final, "edge": edge_final},
            "tier1_state": current_state,
            "opa_status": "bypassed",
            "opa_violations": ["CIRCUIT_BREAKER_OPEN"],
            "explanation": {"summary": "Both circuit breakers are OPEN. No routes available.", "primary_reason": "Hard constraint failure"},
            "decision_time_ms": decision_time_ms,
            "computed_tag": computed_tag,
            "forced_fallback": False,
        }

    if cloud_open:
        preferred_site = "edge"
        backup_site = "none"
    elif edge_open:
        preferred_site = "cloud"
        backup_site = "none"
    else:
        if abs(cloud_final - edge_final) > settings.min_score_delta:
            preferred_site = "cloud" if cloud_final > edge_final else "edge"
        else:
            preferred_site = "cloud" if cloud_final >= edge_final else "edge"
        backup_site = "edge" if preferred_site == "cloud" else "cloud"

    allow, violations, opa_status = await check_opa_safety(
        preferred_site, computed_tag, current_state
    )
    decision = preferred_site
    all_violations = violations
    forced_fallback = False

    if not allow:
        if backup_site != "none":
            backup_allow, backup_violations, backup_opa_status = await check_opa_safety(
                backup_site, computed_tag, current_state
            )
            if backup_opa_status == "bypassed":
                opa_status = "bypassed"
            if backup_allow:
                decision = backup_site
                all_violations = backup_violations
            else:
                all_violations = violations + backup_violations
                decision = preferred_site
                forced_fallback = True
                all_violations.append("FORCED_FALLBACK")
                logger.warning("Both sites rejected by OPA, applying Best-Effort Fallback", site=decision)
        else:
            all_violations = violations
            decision = preferred_site
            forced_fallback = True
            all_violations.append("FORCED_FALLBACK")
            logger.warning("Available site rejected by OPA and backup is OPEN. Applying Best-Effort Fallback", site=decision)

    decision_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
    
    data = metrics_cache.get_all()
    
    explanation = {
        "summary": f"Routed to {decision.upper()}." + (" (FORCED FALLBACK)" if "FORCED_FALLBACK" in all_violations else ""),
        "primary_reason": "Score preference" if allow else ("Fallback passed OPA" if "FORCED_FALLBACK" not in all_violations else "Best-Effort Fallback"),
        "factors": [
            {"signal": f"{preferred_site}_final_score", "value": round(cloud_final if preferred_site=="cloud" else edge_final, 4)},
            {"signal": "opa_status", "value": opa_status},
        ],
        "score_breakdown": {
            "cloud_cats": cloud_cats,
            "edge_cats": edge_cats,
            "cloud_cost_modifier": cloud_cost_mod,
            "edge_cost_modifier": edge_cost_mod,
            "cloud_final": round(cloud_final, 4),
            "edge_final": round(edge_final, 4)
        },
        "telemetry_snapshot": {
            "cloud_latency_ms": data.get("cloud_latency_ms"),
            "edge_latency_ms": data.get("edge_latency_ms"),
            "cloud_inflight": data.get("cloud_gateway_inflight"),
            "edge_inflight": data.get("edge_gateway_inflight"),
            "cloud_gpu_util": data.get("cloud_gpu_util"),
            "edge_cpu_util": data.get("edge_cpu_util")
        },
        "alternatives_considered": [
            {"site": backup_site, "score": round(edge_final if backup_site=="edge" else cloud_final, 4), "rejection_reason": "N/A" if allow else "OPA_REJECTED"}
        ]
    }

    logger.info("Routing decision made", 
                decision=decision, 
                tier1_state=current_state, 
                opa_status=opa_status,
                latency_ms=decision_time_ms)

    return {
        "decision": decision,
        "cats_scores": {"cloud": cloud_cats, "edge": edge_cats},
        "final_scores": {"cloud": cloud_final, "edge": edge_final},
        "tier1_state": current_state,
        "opa_status": opa_status,
        "opa_violations": all_violations,
        "explanation": explanation,
        "decision_time_ms": decision_time_ms,
        "computed_tag": computed_tag,
        "forced_fallback": forced_fallback,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)