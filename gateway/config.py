"""Type-safe configuration for the CATS Gateway via environment variables."""

import os
from pydantic_settings import BaseSettings


class GatewaySettings(BaseSettings):
    # Routing strategy
    benchmark_strategy: str = "PROPOSED"

    # Service URLs
    orchestrator_url: str = "http://orchestrator:8080/route"
    orchestrator_metrics_url: str = "http://orchestrator:8080/metrics/update"
    cloud_inference_url: str = "http://toxiproxy:8001"
    edge_inference_url: str = "http://toxiproxy:8002"
    cloud_metrics_url: str = "http://cloud-node:11434"
    edge_metrics_url: str = "http://edge-node:11434"

    # Model names (must match entrypoint.sh)
    cloud_model: str = "qwen2.5:7b"
    edge_inference_model: str = "qwen2.5:1.5b"

    # SLA
    sla_target_ms: int = 500

    # Rate limiting
    rate_limit_per_second: int = 100
    rate_limit_burst: int = 20

    # Timeouts
    inference_timeout_s: float = 120.0
    orchestrator_timeout_s: float = 5.0
    metrics_push_timeout_s: float = 1.0

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = GatewaySettings()
