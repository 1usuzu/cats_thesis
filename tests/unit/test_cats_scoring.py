import pytest
from metrics_cache import metrics_cache
import tactical_agent
from tactical_agent import compute_cats_score

@pytest.fixture(autouse=True)
def reset_ema_state():
    tactical_agent._ema_state.clear()

# Weights from config.py: w_latency=0.30, w_queue=0.30, w_compute=0.25, w_quality=0.15/0.05/0.30
# Quality scores: cloud=1.0, edge=0.6
# score_lat = 1/(1 + latency/100)   →  lat=0 → 1.0,  lat=100 → 0.5
# score_q   = max(0, 1 - queue/50)  →  q=0 → 1.0,    q=25 → 0.5
# score_comp= max(0, 1 - comp/100)  →  c=0 → 1.0,    c=50 → 0.5

# We need >= 25 test cases. We'll use pytest.mark.parametrize
test_cases = [
    # (site, request_tag, latency, queue, compute, expected_score_approx)
    # The actual formula in tactical_agent.py is:
    # w_lat_adj = 0.30 * 0.8 = 0.24
    # w_queue_adj = 0.30 * 0.8 = 0.24
    # w_comp_adj = 0.25 * 0.8 = 0.20
    # w_qual_adj = w_quality * 0.8
    # w_cost = 0.05 if tag=="high_quality" else 0.20
    # cost_mod = 1.0
    # total = 0.24 * score_lat + 0.24 * score_q + 0.20 * score_comp + (w_quality * 0.8) * quality + w_cost * 1.0

    # 1-5: Cloud Default (w_quality=0.15, quality=1.0) -> w_qual_adj=0.12, w_cost=0.20
    ("cloud", "default", 0, 0, 0, 0.24 * 1.0 + 0.24 * 1.0 + 0.20 * 1.0 + 0.12 * 1.0 + 0.20),
    ("cloud", "default", 100, 0, 0, 0.24 * 0.5 + 0.24 * 1.0 + 0.20 * 1.0 + 0.12 * 1.0 + 0.20),
    ("cloud", "default", 0, 25, 0, 0.24 * 1.0 + 0.24 * 0.5 + 0.20 * 1.0 + 0.12 * 1.0 + 0.20),
    ("cloud", "default", 0, 0, 50, 0.24 * 1.0 + 0.24 * 1.0 + 0.20 * 0.5 + 0.12 * 1.0 + 0.20),
    ("cloud", "default", 100, 25, 50, 0.24 * 0.5 + 0.24 * 0.5 + 0.20 * 0.5 + 0.12 * 1.0 + 0.20),

    # 6-10: Edge Default (w_quality=0.15, quality=0.6) -> w_qual_adj=0.12, w_cost=0.20
    ("edge", "default", 0, 0, 0, 0.24 * 1.0 + 0.24 * 1.0 + 0.20 * 1.0 + 0.12 * 0.6 + 0.20),
    ("edge", "default", 100, 0, 0, 0.24 * 0.5 + 0.24 * 1.0 + 0.20 * 1.0 + 0.12 * 0.6 + 0.20),
    ("edge", "default", 0, 25, 0, 0.24 * 1.0 + 0.24 * 0.5 + 0.20 * 1.0 + 0.12 * 0.6 + 0.20),
    ("edge", "default", 0, 0, 50, 0.24 * 1.0 + 0.24 * 1.0 + 0.20 * 0.5 + 0.12 * 0.6 + 0.20),
    ("edge", "default", 100, 25, 50, 0.24 * 0.5 + 0.24 * 0.5 + 0.20 * 0.5 + 0.12 * 0.6 + 0.20),

    # 11-15: Cloud Fast_OK (w_quality=0.05, quality=1.0) -> w_qual_adj=0.04, w_cost=0.20
    ("cloud", "fast_ok", 0, 0, 0, 0.24 * 1.0 + 0.24 * 1.0 + 0.20 * 1.0 + 0.04 * 1.0 + 0.20),
    ("cloud", "fast_ok", 100, 0, 0, 0.24 * 0.5 + 0.24 * 1.0 + 0.20 * 1.0 + 0.04 * 1.0 + 0.20),
    ("cloud", "fast_ok", 0, 25, 0, 0.24 * 1.0 + 0.24 * 0.5 + 0.20 * 1.0 + 0.04 * 1.0 + 0.20),
    ("cloud", "fast_ok", 0, 0, 50, 0.24 * 1.0 + 0.24 * 1.0 + 0.20 * 0.5 + 0.04 * 1.0 + 0.20),
    ("cloud", "fast_ok", 100, 25, 50, 0.24 * 0.5 + 0.24 * 0.5 + 0.20 * 0.5 + 0.04 * 1.0 + 0.20),

    # 16-20: Edge Fast_OK (w_quality=0.05, quality=0.6) -> w_qual_adj=0.04, w_cost=0.20
    ("edge", "fast_ok", 0, 0, 0, 0.24 * 1.0 + 0.24 * 1.0 + 0.20 * 1.0 + 0.04 * 0.6 + 0.20),
    ("edge", "fast_ok", 100, 0, 0, 0.24 * 0.5 + 0.24 * 1.0 + 0.20 * 1.0 + 0.04 * 0.6 + 0.20),
    ("edge", "fast_ok", 0, 25, 0, 0.24 * 1.0 + 0.24 * 0.5 + 0.20 * 1.0 + 0.04 * 0.6 + 0.20),
    ("edge", "fast_ok", 0, 0, 50, 0.24 * 1.0 + 0.24 * 1.0 + 0.20 * 0.5 + 0.04 * 0.6 + 0.20),
    ("edge", "fast_ok", 100, 25, 50, 0.24 * 0.5 + 0.24 * 0.5 + 0.20 * 0.5 + 0.04 * 0.6 + 0.20),

    # 21-25: Cloud High_Quality (w_quality=0.30, quality=1.0) -> w_qual_adj=0.24, w_cost=0.05
    ("cloud", "high_quality", 0, 0, 0, 0.24 * 1.0 + 0.24 * 1.0 + 0.20 * 1.0 + 0.24 * 1.0 + 0.05),
    ("cloud", "high_quality", 100, 0, 0, 0.24 * 0.5 + 0.24 * 1.0 + 0.20 * 1.0 + 0.24 * 1.0 + 0.05),
    ("cloud", "high_quality", 0, 25, 0, 0.24 * 1.0 + 0.24 * 0.5 + 0.20 * 1.0 + 0.24 * 1.0 + 0.05),
    ("cloud", "high_quality", 0, 0, 50, 0.24 * 1.0 + 0.24 * 1.0 + 0.20 * 0.5 + 0.24 * 1.0 + 0.05),
    ("cloud", "high_quality", 100, 25, 50, 0.24 * 0.5 + 0.24 * 0.5 + 0.20 * 0.5 + 0.24 * 1.0 + 0.05),

    # 26-30: Edge High_Quality (w_quality=0.30, quality=0.6) -> w_qual_adj=0.24, w_cost=0.05
    ("edge", "high_quality", 0, 0, 0, 0.24 * 1.0 + 0.24 * 1.0 + 0.20 * 1.0 + 0.24 * 0.6 + 0.05),
    ("edge", "high_quality", 100, 0, 0, 0.24 * 0.5 + 0.24 * 1.0 + 0.20 * 1.0 + 0.24 * 0.6 + 0.05),
    ("edge", "high_quality", 0, 25, 0, 0.24 * 1.0 + 0.24 * 0.5 + 0.20 * 1.0 + 0.24 * 0.6 + 0.05),
    ("edge", "high_quality", 0, 0, 50, 0.24 * 1.0 + 0.24 * 1.0 + 0.20 * 0.5 + 0.24 * 0.6 + 0.05),
    ("edge", "high_quality", 100, 25, 50, 0.24 * 0.5 + 0.24 * 0.5 + 0.20 * 0.5 + 0.24 * 0.6 + 0.05),
]

@pytest.mark.parametrize("site, tag, latency, queue, compute, expected", test_cases)
def test_compute_cats_score_cases(site, tag, latency, queue, compute, expected):
    # Setup cache
    metrics_cache.update(f"{site}_latency_ms", latency)
    metrics_cache.update(f"{site}_gateway_inflight", queue)

    if site == "cloud":
        metrics_cache.update("cloud_gpu_util", compute)
    else:
        metrics_cache.update("edge_cpu_util", compute)

    score = compute_cats_score(site, tag)
    assert abs(score - expected) < 0.001
