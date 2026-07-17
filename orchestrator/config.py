"""Type-safe configuration for the CATS Orchestrator via environment variables."""

from pydantic_settings import BaseSettings


class OrchestratorSettings(BaseSettings):
    # Control Plane URLs (bypass Toxiproxy)
    cloud_metrics_url: str = "http://cloud-node:11434"
    edge_metrics_url: str = "http://edge-node:11434"
    strategic_agent_url: str = "http://edge-node:11434"
    toxiproxy_api: str = "http://toxiproxy:8474"
    opa_url: str = "http://opa:8181/v1/data/routing"

    # Models
    strategic_agent_model: str = "qwen2.5:1.5b-instruct"

    # CATS Scoring weights
    w_latency: float = 0.30
    w_queue: float = 0.30
    w_compute: float = 0.25
    w_quality: float = 0.15
    w_quality_fast: float = 0.05
    w_quality_hq: float = 0.30

    # Model quality scores
    quality_cloud: float = 1.0
    quality_edge: float = 0.6

    # Thresholds
    max_gateway_inflight: int = 50
    max_gpu_util_pct: int = 90
    max_cpu_util_pct: int = 92
    sla_target_ms: int = 10000
    sla_target_ms_fast: float = 5000.0
    sla_target_ms_hq: float = 40000.0

    # Estimated ms penalty per in-flight request (for predicted_e2e_ms)
    queue_penalty_per_request_ms: int = 50

    # Tier-1 thresholds
    state_edge_loaded_inflight: int = 35
    state_edge_loaded_cpu: int = 85
    state_degraded_latency_ms: int = 150
    state_degraded_bandwidth_kbps: int = 1000
    state_burst_ratio: float = 1.5

    # Phase 0: Routing Decision Hardening
    fail_open_on_opa_unreachable: bool = False
    emergency_override_enabled: bool = False
    emergency_fallback_site: str = "cloud"
    min_score_delta: float = 0.05

    # Feature Flags (Phase 3-6)
    enable_tuning_agent: bool = False
    enable_policy_agent: bool = False
    enable_critic_agent: bool = False
    enable_monitoring_agent: bool = False
    enable_predictive_alerts: bool = False

    # Phase 0: Route Decision Stability
    hysteresis_epochs: int = 2          # State must persist N epochs before transition
    cooldown_requests: int = 5          # Min requests before route can change
    cooldown_seconds: float = 10.0      # Min seconds before route can change
    ema_alpha: float = 0.3              # EMA smoothing factor (lower = smoother)

    # Phase 2: Cost Model Configuration (Tuned for Gemini Flash)
    cost_inference_cloud: float = 0.00015    # Base cost (per 1K tokens)
    cost_inference_edge: float = 0.00002     # Base cost (electricity/hardware depreciation)
    cost_network_cloud: float = 0.00005      # Transfer overhead cost to cloud
    cost_network_edge: float = 0.00000       # Transfer cost to edge (local)
    cost_sla_penalty: float = 0.001          # Penalty cost when SLA is missed

    # Timing
    strategic_epoch_s: int = 30
    strategic_timeout_s: int = 5

    # Collection intervals
    toxiproxy_reader_interval_s: int = 5
    ollama_queue_interval_s: float = 0.5
    compute_metrics_interval_s: int = 2

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = OrchestratorSettings()
