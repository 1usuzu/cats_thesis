import time as _time

import httpx
import structlog
from metrics_cache import metrics_cache
from config import settings

logger = structlog.get_logger("tactical_agent")

# Shared OPA client — initialized in orchestrator lifespan, avoids per-call TCP overhead
_opa_client: httpx.AsyncClient | None = None


def init_opa_client(timeout: float = 0.5) -> None:
    """Create the shared async HTTP client for OPA queries."""
    global _opa_client
    _opa_client = httpx.AsyncClient(timeout=timeout)


async def close_opa_client() -> None:
    """Gracefully close the shared OPA client."""
    global _opa_client
    if _opa_client:
        await _opa_client.aclose()
        _opa_client = None


def compute_cats_score(site: str, request_tag: str = "default") -> float:
    data = metrics_cache.get_all()

    latency_ms = data.get(f"{site}_latency_ms", 0)
    gateway_inflight = data.get(f"{site}_gateway_inflight", 0)

    if site == "cloud":
        compute_util = data.get("cloud_gpu_util", 0)
    else:
        compute_util = data.get("edge_cpu_util", 0)

    w_quality = settings.w_quality
    if request_tag == "fast_ok":
        w_quality = settings.w_quality_fast
    elif request_tag == "high_quality":
        w_quality = settings.w_quality_hq

    score_lat = 1.0 / (1.0 + (latency_ms / 100.0))
    score_q = max(0.0, 1.0 - (gateway_inflight / settings.max_gateway_inflight))
    score_comp = max(0.0, 1.0 - (compute_util / 100.0))

    site_quality = settings.quality_cloud if site == "cloud" else settings.quality_edge
    
    total_score = (
        settings.w_latency * score_lat
        + settings.w_queue * score_q
        + settings.w_compute * score_comp
        + w_quality * site_quality
    )
    return round(total_score, 4)


async def check_opa_safety(
    site: str, request_tag: str, site_state: str = "STATE_NORMAL"
) -> tuple[bool, list, str]:
    """Query OPA safety gate. Returns (allow, violations, opa_status).

    opa_status is "enforced" when OPA responded, "bypassed" on failure (fail-open).
    """
    t0 = _time.perf_counter()

    data = metrics_cache.get_all()
    gateway_inflight = data.get(f"{site}_gateway_inflight", 0)
    network_latency_ms = data.get(f"{site}_latency_ms", 0)
    total_inference_ms_avg = data.get(f"{site}_total_inference_ms_avg", 0)

    if site == "cloud":
        compute_util = data.get("cloud_gpu_util", 0)
    else:
        compute_util = data.get("edge_cpu_util", 0)

    # Composite end-to-end estimate: network + inference + queue pressure
    queue_penalty_ms = gateway_inflight * settings.queue_penalty_per_request_ms
    predicted_e2e_ms = network_latency_ms + total_inference_ms_avg + queue_penalty_ms

    opa_input = {
        "input": {
            "site": site,
            "gateway_inflight": gateway_inflight,
            "compute_util": compute_util,
            "predicted_latency_ms": predicted_e2e_ms,
            "request_tag": request_tag,
            "site_state": site_state,
            "sla_target_ms": settings.sla_target_ms,
        }
    }

    try:
        if not _opa_client:
            raise RuntimeError("OPA client not initialized")
        client = _opa_client
        response = await client.post(settings.opa_url, json=opa_input)
        response.raise_for_status()
        result = response.json().get("result", {})

        opa_latency_ms = round((_time.perf_counter() - t0) * 1000, 2)
        metrics_cache.update("opa_latency_ms", opa_latency_ms)

        return result.get("allow", False), result.get("violations", []), "enforced"
    except Exception as e:
        opa_latency_ms = round((_time.perf_counter() - t0) * 1000, 2)
        metrics_cache.update("opa_latency_ms", opa_latency_ms)
        logger.error(
            "OPA connection error, BYPASSING safety gate",
            error=str(e),
            site=site,
            opa_latency_ms=opa_latency_ms,
        )
        return True, [], "bypassed"
