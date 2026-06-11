import time
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from metrics_cache import metrics_cache
from toxiproxy_reader import start_toxiproxy_reader
from compute_reader import start_compute_reader
from strategic_agent import start_strategic_agent
from tactical_agent import compute_cats_score, check_opa_safety, init_opa_client, close_opa_client
from shared_state import shared_state

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
    
    background_tasks.append(task_tox)
    background_tasks.extend(tasks_comp)
    background_tasks.append(task_strat)
    
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


class GatewayMetrics(BaseModel):
    cloud_inflight: int
    edge_inflight: int
    current_rps: float
    cloud_total_inference_ms: float
    edge_total_inference_ms: float


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


@app.post("/route")
async def get_routing_decision(req: RouteRequest):
    start_time = time.perf_counter()

    current_state, current_template = shared_state.get()

    cloud_cats = compute_cats_score("cloud", req.request_tag)
    edge_cats = compute_cats_score("edge", req.request_tag)

    cloud_final = cloud_cats * current_template.get("cloud", 0.5)
    edge_final = edge_cats * current_template.get("edge", 0.5)

    preferred_site = "cloud" if cloud_final >= edge_final else "edge"
    backup_site = "edge" if preferred_site == "cloud" else "cloud"

    allow, violations, opa_status = await check_opa_safety(
        preferred_site, req.request_tag, current_state
    )
    decision = preferred_site
    all_violations = violations

    if not allow:
        backup_allow, backup_violations, backup_opa_status = await check_opa_safety(
            backup_site, req.request_tag, current_state
        )
        if backup_opa_status == "bypassed":
            opa_status = "bypassed"
        if backup_allow:
            decision = backup_site
            all_violations = backup_violations
        else:
            decision = "cloud"
            all_violations = violations + backup_violations + ["FORCE_CLOUD_FALLBACK"]

    decision_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
    
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
        "decision_time_ms": decision_time_ms,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)