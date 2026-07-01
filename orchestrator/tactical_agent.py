import json
import time as _time
from pathlib import Path

import httpx
import structlog
from config import settings
from metrics_cache import metrics_cache

try:
    import jsonschema
    _schema_path = Path(__file__).parent.parent / "safety" / "schemas" / "opa_input_schema.json"
    if _schema_path.exists():
        with open(_schema_path) as f:
            _OPA_INPUT_SCHEMA = json.load(f)
    else:
        _OPA_INPUT_SCHEMA = None
except ImportError:
    _OPA_INPUT_SCHEMA = None

logger = structlog.get_logger("tactical_agent")

# EMA state for score smoothing (Phase 0: Route Decision Stability)
_ema_state: dict[str, float] = {}


def _apply_ema(key: str, raw_value: float, alpha: float) -> float:
    """Apply Exponential Moving Average to dampen metric noise."""
    if key not in _ema_state:
        _ema_state[key] = raw_value
        return raw_value
    smoothed = alpha * raw_value + (1 - alpha) * _ema_state[key]
    _ema_state[key] = smoothed
    return smoothed

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


def compute_cats_score(site: str, request_tag: str = "default", is_canary: bool = False) -> float:
    data = metrics_cache.get_all()

    raw_latency = data.get(f"{site}_latency_ms", 0)
    raw_inflight = data.get(f"{site}_gateway_inflight", 0)

    if site == "cloud":
        raw_compute = data.get("cloud_gpu_util", 0)
    else:
        raw_compute = data.get("edge_cpu_util", 0)

    # Apply EMA smoothing to dampen noise
    latency_ms = _apply_ema(f"{site}_latency", raw_latency, settings.ema_alpha)
    gateway_inflight = _apply_ema(f"{site}_inflight", raw_inflight, settings.ema_alpha)
    compute_util = _apply_ema(f"{site}_compute", raw_compute, settings.ema_alpha)

    w_quality = settings.w_quality
    if request_tag == "fast_ok":
        w_quality = settings.w_quality_fast
    elif request_tag == "high_quality":
        w_quality = settings.w_quality_hq

    score_lat = 1.0 / (1.0 + (latency_ms / 100.0))
    score_q = max(0.0, 1.0 - (gateway_inflight / settings.max_gateway_inflight))
    score_comp = max(0.0, 1.0 - (compute_util / 100.0))

    site_quality = settings.quality_cloud if site == "cloud" else settings.quality_edge

    # Cost modifier integration
    from shared_state import shared_state
    cost_modifiers = shared_state.get_cost_modifiers()
    site_cost_mod = cost_modifiers.get(site, 1.0)

    if is_canary:
        weights = shared_state.get_sandbox_weights()
    else:
        weights = shared_state.get_dynamic_weights()

    w_latency = weights.get("w_latency", settings.w_latency)
    w_queue = weights.get("w_queue", settings.w_queue)
    w_compute = weights.get("w_compute", settings.w_compute)

    # Rescale weights (W_COST = 0.20, others scale down slightly)
    w_lat_adj = w_latency * 0.8
    w_queue_adj = w_queue * 0.8
    w_comp_adj = w_compute * 0.8
    w_qual_adj = w_quality * 0.8

    # Dynamic Cost Weight: Don't care much about cost if the task is complex
    w_cost = 0.05 if request_tag == "high_quality" else 0.20

    total_score = (
        w_lat_adj * score_lat
        + w_queue_adj * score_q
        + w_comp_adj * score_comp
        + w_qual_adj * site_quality
        + w_cost * site_cost_mod
    )
    return round(total_score, 4), site_cost_mod


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

    dynamic_sla_ms = settings.sla_target_ms
    if request_tag == "high_quality":
        dynamic_sla_ms = getattr(settings, "sla_target_ms_hq", 40000.0)
    elif request_tag == "fast_ok":
        dynamic_sla_ms = getattr(settings, "sla_target_ms_fast", 5000.0)

    opa_input = {
        "input": {
            "site": site,
            "gateway_inflight": gateway_inflight,
            "compute_util": compute_util,
            "predicted_latency_ms": predicted_e2e_ms,
            "request_tag": request_tag,
            "site_state": site_state,
            "sla_target_ms": dynamic_sla_ms,
        }
    }

    try:
        # Validate OPA input schema if available
        if _OPA_INPUT_SCHEMA is not None:
            try:
                jsonschema.validate(instance=opa_input["input"], schema=_OPA_INPUT_SCHEMA)
            except jsonschema.ValidationError as ve:
                logger.error("OPA input schema validation failed",
                             error=str(ve.message),
                             path=list(ve.absolute_path))
                return False, ["SCHEMA_VALIDATION_FAILED"], "error"

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
        if settings.fail_open_on_opa_unreachable:
            logger.error(
                "OPA connection error, BYPASSING safety gate",
                error=str(e),
                site=site,
                opa_latency_ms=opa_latency_ms,
            )
            return True, ["OPA_UNREACHABLE_BYPASS"], "bypassed"
        else:
            logger.error(
                "OPA connection error, BLOCKING request (fail-open disabled)",
                error=str(e),
                site=site,
                opa_latency_ms=opa_latency_ms,
            )
            return False, ["OPA_UNREACHABLE"], "unreachable"
