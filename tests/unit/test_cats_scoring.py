import pytest
from tactical_agent import compute_cats_score
from metrics_cache import metrics_cache

# Weights from config.py: w_latency=0.30, w_queue=0.30, w_compute=0.25, w_quality=0.15/0.05/0.30
# Quality scores: cloud=1.0, edge=0.6
# score_lat = 1/(1 + latency/100)   →  lat=0 → 1.0,  lat=100 → 0.5
# score_q   = max(0, 1 - queue/50)  →  q=0 → 1.0,    q=25 → 0.5
# score_comp= max(0, 1 - comp/100)  →  c=0 → 1.0,    c=50 → 0.5

# We need >= 25 test cases. We'll use pytest.mark.parametrize
test_cases = [
    # (site, request_tag, latency, queue, compute, expected_score_approx)
    
    # 1-5: Cloud Default (w_quality=0.15, quality=1.0)
    ("cloud", "default", 0, 0, 0, 0.30 * 1.0 + 0.30 * 1.0 + 0.25 * 1.0 + 0.15 * 1.0),
    ("cloud", "default", 100, 0, 0, 0.30 * 0.5 + 0.30 * 1.0 + 0.25 * 1.0 + 0.15 * 1.0),
    ("cloud", "default", 0, 25, 0, 0.30 * 1.0 + 0.30 * 0.5 + 0.25 * 1.0 + 0.15 * 1.0),
    ("cloud", "default", 0, 0, 50, 0.30 * 1.0 + 0.30 * 1.0 + 0.25 * 0.5 + 0.15 * 1.0),
    ("cloud", "default", 100, 25, 50, 0.30 * 0.5 + 0.30 * 0.5 + 0.25 * 0.5 + 0.15 * 1.0),
    
    # 6-10: Edge Default (w_quality=0.15, quality=0.6)
    ("edge", "default", 0, 0, 0, 0.30 * 1.0 + 0.30 * 1.0 + 0.25 * 1.0 + 0.15 * 0.6),
    ("edge", "default", 100, 0, 0, 0.30 * 0.5 + 0.30 * 1.0 + 0.25 * 1.0 + 0.15 * 0.6),
    ("edge", "default", 0, 25, 0, 0.30 * 1.0 + 0.30 * 0.5 + 0.25 * 1.0 + 0.15 * 0.6),
    ("edge", "default", 0, 0, 50, 0.30 * 1.0 + 0.30 * 1.0 + 0.25 * 0.5 + 0.15 * 0.6),
    ("edge", "default", 100, 25, 50, 0.30 * 0.5 + 0.30 * 0.5 + 0.25 * 0.5 + 0.15 * 0.6),

    # 11-15: Cloud Fast_OK (w_quality=0.05, quality=1.0)
    ("cloud", "fast_ok", 0, 0, 0, 0.30 * 1.0 + 0.30 * 1.0 + 0.25 * 1.0 + 0.05 * 1.0),
    ("cloud", "fast_ok", 100, 0, 0, 0.30 * 0.5 + 0.30 * 1.0 + 0.25 * 1.0 + 0.05 * 1.0),
    ("cloud", "fast_ok", 0, 25, 0, 0.30 * 1.0 + 0.30 * 0.5 + 0.25 * 1.0 + 0.05 * 1.0),
    ("cloud", "fast_ok", 0, 0, 50, 0.30 * 1.0 + 0.30 * 1.0 + 0.25 * 0.5 + 0.05 * 1.0),
    ("cloud", "fast_ok", 100, 25, 50, 0.30 * 0.5 + 0.30 * 0.5 + 0.25 * 0.5 + 0.05 * 1.0),

    # 16-20: Edge Fast_OK (w_quality=0.05, quality=0.6)
    ("edge", "fast_ok", 0, 0, 0, 0.30 * 1.0 + 0.30 * 1.0 + 0.25 * 1.0 + 0.05 * 0.6),
    ("edge", "fast_ok", 100, 0, 0, 0.30 * 0.5 + 0.30 * 1.0 + 0.25 * 1.0 + 0.05 * 0.6),
    ("edge", "fast_ok", 0, 25, 0, 0.30 * 1.0 + 0.30 * 0.5 + 0.25 * 1.0 + 0.05 * 0.6),
    ("edge", "fast_ok", 0, 0, 50, 0.30 * 1.0 + 0.30 * 1.0 + 0.25 * 0.5 + 0.05 * 0.6),
    ("edge", "fast_ok", 100, 25, 50, 0.30 * 0.5 + 0.30 * 0.5 + 0.25 * 0.5 + 0.05 * 0.6),

    # 21-25: Cloud High_Quality (w_quality=0.30, quality=1.0)
    ("cloud", "high_quality", 0, 0, 0, 0.30 * 1.0 + 0.30 * 1.0 + 0.25 * 1.0 + 0.30 * 1.0),
    ("cloud", "high_quality", 100, 0, 0, 0.30 * 0.5 + 0.30 * 1.0 + 0.25 * 1.0 + 0.30 * 1.0),
    ("cloud", "high_quality", 0, 25, 0, 0.30 * 1.0 + 0.30 * 0.5 + 0.25 * 1.0 + 0.30 * 1.0),
    ("cloud", "high_quality", 0, 0, 50, 0.30 * 1.0 + 0.30 * 1.0 + 0.25 * 0.5 + 0.30 * 1.0),
    ("cloud", "high_quality", 100, 25, 50, 0.30 * 0.5 + 0.30 * 0.5 + 0.25 * 0.5 + 0.30 * 1.0),
    
    # 26-30: Edge High_Quality (w_quality=0.30, quality=0.6)
    ("edge", "high_quality", 0, 0, 0, 0.30 * 1.0 + 0.30 * 1.0 + 0.25 * 1.0 + 0.30 * 0.6),
    ("edge", "high_quality", 100, 0, 0, 0.30 * 0.5 + 0.30 * 1.0 + 0.25 * 1.0 + 0.30 * 0.6),
    ("edge", "high_quality", 0, 25, 0, 0.30 * 1.0 + 0.30 * 0.5 + 0.25 * 1.0 + 0.30 * 0.6),
    ("edge", "high_quality", 0, 0, 50, 0.30 * 1.0 + 0.30 * 1.0 + 0.25 * 0.5 + 0.30 * 0.6),
    ("edge", "high_quality", 100, 25, 50, 0.30 * 0.5 + 0.30 * 0.5 + 0.25 * 0.5 + 0.30 * 0.6),
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
