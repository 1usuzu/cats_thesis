import asyncio
import time
from contextlib import asynccontextmanager

import httpx
import structlog
import uvicorn
from classifier import classify_prompt_complexity
from compute_reader import start_compute_reader
from config import settings
from cost_agent import run_cost_loop
from critic_agent import critic_agent_loop
from event_bus import event_bus
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from metrics_cache import metrics_cache
from monitoring_agent import start_monitoring_agent
from policy_agent import (
    handle_anomaly,
    handle_predictive_alert,
    policy_agent_loop,
    trigger_policy_proposal_manually,
)
from pydantic import BaseModel
from shared_state import shared_state
from strategic_agent import start_strategic_agent
from tactical_agent import check_opa_safety, close_opa_client, compute_cats_score, init_opa_client
from toxiproxy_reader import start_toxiproxy_reader
from tuning_agent import start_tuning_agent

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

# Cooldown state: prevents rapid route flipping between requests
_last_decision: str | None = None
_last_decision_change_time: float = 0.0
_requests_since_change: int = 0

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize shared OPA client
    init_opa_client()

    # Push initial policy to OPA via REST API
    try:
        opa_policy_url = settings.opa_url.replace("/v1/data/routing", "/v1/policies/routing")
        with open("/safety/policies/routing.rego", "r") as f:
            initial_policy = f.read()
        async with httpx.AsyncClient() as client:
            resp = await client.put(opa_policy_url, content=initial_policy, headers={"Content-Type": "text/plain"})
            if resp.status_code == 200:
                logger.info("Successfully pushed initial routing policy to OPA.")
            else:
                logger.error(f"Failed to push initial policy to OPA: {resp.text}")
    except Exception as e:
        logger.error(f"Error pushing initial policy to OPA: {e}")

    # Start Event Bus (Phase 5 & 6)
    event_bus.start()
    event_bus.subscribe("anomaly", handle_anomaly)
    event_bus.subscribe("predictive_alert", handle_predictive_alert)

    # Start readers and agents
    task_tox = start_toxiproxy_reader()
    tasks_comp = start_compute_reader()
    task_strat = start_strategic_agent()
    task_cost = asyncio.create_task(run_cost_loop())

    background_tasks.append(task_tox)
    background_tasks.extend(tasks_comp)
    background_tasks.append(task_strat)
    background_tasks.append(task_cost)

    if settings.enable_tuning_agent:
        task_tune = start_tuning_agent()
        background_tasks.append(task_tune)
    if settings.enable_policy_agent:
        task_policy = asyncio.create_task(policy_agent_loop())
        background_tasks.append(task_policy)
    if settings.enable_critic_agent:
        task_critic = asyncio.create_task(critic_agent_loop())
        background_tasks.append(task_critic)
    if settings.enable_monitoring_agent:
        task_monitoring = start_monitoring_agent()
        background_tasks.append(task_monitoring)

    logger.info("Orchestrator background readers and agents started")
    yield

    logger.info("Orchestrator shutting down, cancelling tasks")
    await event_bus.stop()
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
    sla_miss: bool = False

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
        "tier1_state": state,
        "tuning": {
            "dynamic_weights": shared_state.get_dynamic_weights(),
            "sandbox_weights": shared_state.get_sandbox_weights(),
            "canary_active": shared_state.is_canary_active()
        },
        "policy": shared_state.get_policy_proposal()
    }

# --- POLICY SANDBOX APIs ---
@app.get("/policy/status")
async def get_policy_status():
    """Returns current active policy, proposed policy, and validation status."""
    try:
        with open("/safety/policies/routing.rego", "r") as f:
            active_policy = f.read()
    except Exception:
        active_policy = ""

    return {
        "active_policy": active_policy,
        "proposal": shared_state.get_policy_proposal()
    }

@app.post("/policy/trigger")
async def trigger_policy():
    """Manually triggers the Policy Agent to propose a new policy."""
    success = trigger_policy_proposal_manually()
    if success:
        return {"status": "triggered"}
    return {"status": "failed"}

@app.post("/policy/approve")
async def approve_policy():
    """Approves and deploys the proposed policy via OPA REST API."""
    prop_state = shared_state.get_policy_proposal()
    if not prop_state["has_proposal"] or prop_state["validation_results"].get("status") != "PASSED":
        return {"status": "error", "message": "No valid proposal to approve"}

    proposed_rego = prop_state["proposed_policy"]

    try:
        # 1. Update the OPA server directly via REST API (Hot Reload)
        opa_url = settings.opa_url.replace("/v1/data/routing", "/v1/policies/routing")
        async with httpx.AsyncClient() as client:
            resp = await client.put(opa_url, content=proposed_rego, headers={"Content-Type": "text/plain"})
            if resp.status_code != 200:
                return {"status": "error", "message": f"OPA API rejected policy: {resp.text}"}

        # 2. Write to disk for persistence across restarts
        with open("/safety/policies/routing.rego", "w") as f:
            f.write(proposed_rego)

        shared_state.clear_policy_proposal()
        return {"status": "success", "message": "Policy approved and deployed."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/policy/reject")
async def reject_policy():
    """Rejects the proposed policy."""
    shared_state.clear_policy_proposal()
    return {"status": "success", "message": "Policy rejected."}

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

        if res.sla_miss:
            metrics_cache.update("cloud_sla_miss_count", data.get("cloud_sla_miss_count", 0) + 1)
    else:
        if res.success:
            metrics_cache.update("edge_success_count", data.get("edge_success_count", 0) + 1)
        else:
            metrics_cache.update("edge_failure_count", data.get("edge_failure_count", 0) + 1)

        if res.sla_miss:
            metrics_cache.update("edge_sla_miss_count", data.get("edge_sla_miss_count", 0) + 1)
    return {"status": "ok"}


@app.post("/route")
async def get_routing_decision(req: RouteRequest):
    start_time = time.perf_counter()
    import random

    current_state, current_template = shared_state.get()

    computed_tag = req.request_tag
    if computed_tag == "default" or not computed_tag:
        computed_tag = classify_prompt_complexity(req.prompt)

    # Canary logic: 10% traffic if active
    is_canary = False
    if shared_state.is_canary_active():
        if random.random() < 0.10:
            is_canary = True

    cloud_cats, cloud_cost_mod = compute_cats_score("cloud", computed_tag, is_canary)
    edge_cats, edge_cost_mod = compute_cats_score("edge", computed_tag, is_canary)

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
            "is_canary": is_canary,
        }

    primary_reason_str = "Score preference"

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

        # Cooldown: if we recently changed route, stick with the old one
        global _last_decision, _last_decision_change_time, _requests_since_change
        if _last_decision is not None and preferred_site != _last_decision:
            time_since_change = time.time() - _last_decision_change_time
            within_cooldown = (
                _requests_since_change < settings.cooldown_requests
                and time_since_change < settings.cooldown_seconds
            )
            if within_cooldown:
                # Hold the previous route (cooldown active)
                preferred_site = _last_decision
                backup_site = "edge" if preferred_site == "cloud" else "cloud"
                primary_reason_str = "Hysteresis (Route Locked)"
                logger.debug("Cooldown active, holding route",
                             held_site=preferred_site,
                             requests_since=_requests_since_change,
                             seconds_since=round(time_since_change, 1))

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
                if settings.emergency_override_enabled:
                    decision = settings.emergency_fallback_site
                    forced_fallback = True
                    all_violations.append("BOTH_SITES_REJECTED")
                    logger.warning("Both sites rejected by OPA, applying Emergency Fallback", site=decision)
                    opa_status = "emergency_override"
                else:
                    decision = "none"
                    forced_fallback = False
                    all_violations.append("BOTH_SITES_REJECTED")
                    logger.warning("Both sites rejected by OPA and emergency override disabled. Rejecting route.")
                    opa_status = "rejected"
        else:
            all_violations = violations
            if settings.emergency_override_enabled:
                decision = settings.emergency_fallback_site
                forced_fallback = True
                all_violations.append("BOTH_SITES_REJECTED")
                logger.warning("Available site rejected by OPA and backup is OPEN. Applying Emergency Fallback", site=decision)
                opa_status = "emergency_override"
            else:
                decision = "none"
                forced_fallback = False
                all_violations.append("BOTH_SITES_REJECTED")
                logger.warning("Available site rejected by OPA and backup is OPEN and emergency override disabled. Rejecting route.")
                opa_status = "rejected"

    decision_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # Update cooldown tracking
    if not cloud_open and not edge_open and decision != "none":
        if _last_decision is not None and decision != _last_decision:
            _last_decision_change_time = time.time()
            _requests_since_change = 0
            logger.info("Route changed", old=_last_decision, new=decision)
        else:
            _requests_since_change += 1
        _last_decision = decision

    data = metrics_cache.get_all()

    explanation = {
        "summary": f"Routed to {decision.upper()}." + (" (FORCED FALLBACK)" if "FORCED_FALLBACK" in all_violations else ""),
        "primary_reason": primary_reason_str if allow else ("Fallback passed OPA" if "FORCED_FALLBACK" not in all_violations else "Best-Effort Fallback"),
        "factors": [
            {"signal": f"{preferred_site}_final_score", "value": round(cloud_final if preferred_site=="cloud" else edge_final, 4)},
            {"signal": "opa_status", "value": opa_status},
        ],
        "score_breakdown": {
            "cloud_cats": cloud_cats,
            "edge_cats": edge_cats,
            "cloud_expected_cost": data.get("cloud_expected_cost", 0.0),
            "edge_expected_cost": data.get("edge_expected_cost", 0.0),
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
        "is_canary": is_canary,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
