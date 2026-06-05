import asyncio
import itertools
import time
from collections import deque
from contextlib import asynccontextmanager

import httpx
import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config import settings
from middleware import RequestIDMiddleware, TimingMiddleware
from rate_limiter import rate_limit_middleware
from auth import api_key_auth_middleware
from circuit_breaker import circuit_breakers, CircuitState
from models import APIResponse, ChatRequest, ChatResponse, ErrorResponse, HealthResponse, ReadinessResponse, RouteInfo
from pydantic import BaseModel
from quality_sample import router as quality_router
from shared_client import shared_http_client

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger("gateway")

# Round-robin counter for BASELINE-1
rr_counter = itertools.cycle(["cloud", "edge"])

# Thread-safe in-flight tracking
in_flight_lock = asyncio.Lock()
in_flight = {"cloud": 0, "edge": 0}
request_timestamps: deque = deque(maxlen=1000)


@asynccontextmanager
async def lifespan(app: FastAPI):
    shared_http_client.client = httpx.AsyncClient(timeout=settings.inference_timeout_s)
    logger.info("Gateway started", strategy=settings.benchmark_strategy)
    yield
    if shared_http_client.client:
        await shared_http_client.client.aclose()
    logger.info("Gateway shut down")


app = FastAPI(
    title="CATS Ingress Gateway",
    version="1.0.0",
    description="Context-Aware Traffic Steering gateway for LLM inference routing",
    lifespan=lifespan,
)

# Add Middleware (Order matters: outermost first)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TimingMiddleware)
app.add_middleware(RequestIDMiddleware)
# Custom middlewares via BaseHTTPMiddleware
app.add_middleware(BaseHTTPMiddleware, dispatch=rate_limit_middleware)
app.add_middleware(BaseHTTPMiddleware, dispatch=api_key_auth_middleware)

# Include routers
app.include_router(quality_router, prefix="/v1")


def _build_inference_url(site: str) -> str:
    base = settings.cloud_inference_url if site == "cloud" else settings.edge_inference_url
    return f"{base}/api/generate" if not base.endswith("/api/generate") else base


def _get_model(site: str) -> str:
    return settings.cloud_model if site == "cloud" else settings.edge_inference_model


async def _push_metrics(cloud_total_inference: float = 0.0, edge_total_inference: float = 0.0):
    now = time.time()
    recent = [ts for ts in request_timestamps if now - ts <= 5.0]
    current_rps = len(recent) / 5.0 if recent else 0.0

    async with in_flight_lock:
        cloud_q = in_flight["cloud"]
        edge_q = in_flight["edge"]

    payload = {
        "cloud_inflight": cloud_q,
        "edge_inflight": edge_q,
        "current_rps": current_rps,
        "cloud_total_inference_ms": cloud_total_inference,
        "edge_total_inference_ms": edge_total_inference,
    }
    try:
        if shared_http_client.client:
            await shared_http_client.client.post(
                settings.orchestrator_metrics_url,
                json=payload,
                timeout=settings.metrics_push_timeout_s
            )
    except Exception as e:
        logger.warning("Failed to push metrics to orchestrator", error=str(e))


@app.get("/health", response_model=HealthResponse)
async def health():
    """Liveness probe."""
    return HealthResponse(status="ok")


@app.get("/health/ready", response_model=ReadinessResponse)
async def health_ready():
    """Readiness probe checking dependencies."""
    checks = {}
    try:
        resp = await shared_http_client.client.get(f"{settings.cloud_metrics_url}/api/tags", timeout=2.0)
        checks["cloud_node"] = resp.status_code == 200
    except Exception:
        checks["cloud_node"] = False

    try:
        resp = await shared_http_client.client.get(f"{settings.edge_metrics_url}/api/tags", timeout=2.0)
        checks["edge_node"] = resp.status_code == 200
    except Exception:
        checks["edge_node"] = False

    all_ready = all(checks.values())
    status = "ready" if all_ready else "not_ready"
    return ReadinessResponse(status=status, checks=checks)


@app.get("/health/sites")
async def health_sites():
    """Check circuit breaker states for sites."""
    return {"states": circuit_breakers.get_states()}


class StrategyUpdate(BaseModel):
    strategy: str

@app.post("/admin/strategy")
async def update_strategy(req: StrategyUpdate):
    """Dynamically update routing strategy in memory."""
    settings.benchmark_strategy = req.strategy
    logger.info("Benchmark strategy updated via admin endpoint", new_strategy=req.strategy)
    return {"status": "ok", "strategy": settings.benchmark_strategy}


@app.post("/v1/chat", response_model=APIResponse[ChatResponse])
async def chat(req: ChatRequest):
    """Main routing endpoint for chat requests."""
    request_timestamps.append(time.time())
    decision = "cloud"

    if settings.benchmark_strategy == "PROPOSED":
        try:
            res = await shared_http_client.client.post(
                settings.orchestrator_url,
                json={"prompt": req.prompt, "request_tag": req.request_tag},
                timeout=settings.orchestrator_timeout_s,
            )
            res.raise_for_status()
            decision = res.json().get("decision", "cloud")
        except Exception as e:
            logger.error("Orchestrator unavailable, falling back to cloud", error=str(e))
            decision = "cloud"
    elif settings.benchmark_strategy == "BASELINE-1":
        decision = next(rr_counter)
    elif settings.benchmark_strategy == "BASELINE-2":
        decision = "cloud"
    elif settings.benchmark_strategy == "BASELINE-3":
        decision = "edge"

    # Circuit Breaker check
    cb = circuit_breakers.get(decision)
    if not cb.can_execute():
        logger.warning(f"Circuit for {decision} is OPEN. Failing over.")
        decision = "edge" if decision == "cloud" else "cloud"
        cb = circuit_breakers.get(decision)
        if not cb.can_execute():
            return JSONResponse(
                status_code=503,
                content=APIResponse(error="Both inference sites are currently unavailable").model_dump()
            )

    target_url = _build_inference_url(decision)
    model_name = _get_model(decision)
    payload = {"model": model_name, "prompt": req.prompt, "stream": False}

    async with in_flight_lock:
        in_flight[decision] += 1

    asyncio.create_task(_push_metrics())

    start_time = time.time()
    try:
        response = await shared_http_client.client.post(target_url, json=payload)
        response.raise_for_status()
        
        # Record success for circuit breaker
        cb.record_success()
        
        total_inference_ms = round((time.time() - start_time) * 1000)

        c_tot = total_inference_ms if decision == "cloud" else 0.0
        e_tot = total_inference_ms if decision == "edge" else 0.0
        asyncio.create_task(_push_metrics(c_tot, e_tot))

        chat_resp = ChatResponse(
            response=response.json().get("response"),
            route=RouteInfo(
                site=decision,
                model=model_name,
                strategy=settings.benchmark_strategy,
                total_inference_ms=total_inference_ms
            )
        )
        
        logger.info("Request routed successfully", site=decision, total_inference_ms=total_inference_ms)
        
        return APIResponse[ChatResponse](
            data=chat_resp,
            meta={"strategy": settings.benchmark_strategy}
        )
        
    except Exception as e:
        # Record failure for circuit breaker
        cb.record_failure()
        logger.error("Inference failed", site=decision, error=str(e))
        return JSONResponse(
            status_code=500,
            content=APIResponse(
                error="Inference failed",
                meta={"detail": str(e), "routed_to": decision}
            ).model_dump()
        )
    finally:
        async with in_flight_lock:
            in_flight[decision] -= 1
        asyncio.create_task(_push_metrics())


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)