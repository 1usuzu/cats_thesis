import pytest
from main import RouteRequest, get_routing_decision
from metrics_cache import metrics_cache
from shared_state import shared_state


# We need to patch check_opa_safety so we don't actually hit the OPA server
@pytest.fixture(autouse=True)
def mock_opa(monkeypatch):
    async def mock_check_opa_safety(site, request_tag, site_state="NORMAL"):
        # For tests, we'll pretend OPA always allows cloud, but edge might fail if it's explicitly set to fail
        if site == "edge" and request_tag in ("fail_edge", "fail_both"):
            return False, ["EDGE_SIMULATED_FAIL"], "enforced"
        if site == "cloud" and request_tag in ("fail_cloud", "fail_both"):
            return False, ["CLOUD_SIMULATED_FAIL"], "enforced"
        return True, [], "enforced"

    monkeypatch.setattr("main.check_opa_safety", mock_check_opa_safety)

@pytest.mark.asyncio
async def test_routing_decision_normal():
    shared_state.update("STATE_NORMAL")
    metrics_cache.update("cloud_latency_ms", 10)
    metrics_cache.update("edge_latency_ms", 50)

    req = RouteRequest(prompt="test", request_tag="default")
    res = await get_routing_decision(req)

    assert res["decision"] in ["cloud", "edge"]
    assert "cats_scores" in res
    assert "decision_time_ms" in res
    assert res["tier1_state"] == "STATE_NORMAL"
    assert res["opa_violations"] == []

@pytest.mark.asyncio
async def test_routing_decision_opa_fallback():
    import main
    main._last_decision = None
    main._last_decision_change_time = 0.0
    shared_state.update("STATE_NORMAL")
    # Make edge the preferred site (e.g. cloud latency huge)
    metrics_cache.update("cloud_latency_ms", 1000)
    metrics_cache.update("edge_latency_ms", 10)

    # We use tag 'fail_edge' to trigger OPA rejection on edge
    req = RouteRequest(prompt="test", request_tag="fail_edge")
    res = await get_routing_decision(req)

    # Even though edge was preferred, OPA rejected it, so it should fallback to cloud
    assert res["decision"] == "cloud"

@pytest.mark.asyncio
async def test_routing_decision_rule4_force_none():
    import main
    main.settings.emergency_override_enabled = False
    shared_state.update("STATE_NORMAL")
    metrics_cache.update("cloud_latency_ms", 100)
    metrics_cache.update("edge_latency_ms", 100)

    req = RouteRequest(prompt="test", request_tag="fail_both")
    res = await get_routing_decision(req)

    # Both rejected, no emergency -> none
    assert res["decision"] == "none"
    assert "BOTH_SITES_REJECTED" in res["opa_violations"]
    assert res["opa_status"] == "rejected"

@pytest.mark.asyncio
async def test_routing_decision_rule4_emergency_fallback():
    import main
    main.settings.emergency_override_enabled = True
    main.settings.emergency_fallback_site = "cloud"
    shared_state.update("STATE_NORMAL")
    metrics_cache.update("cloud_latency_ms", 100)
    metrics_cache.update("edge_latency_ms", 100)

    req = RouteRequest(prompt="test", request_tag="fail_both")
    res = await get_routing_decision(req)

    # Both rejected, emergency -> cloud
    assert res["decision"] == "cloud"
    assert "BOTH_SITES_REJECTED" in res["opa_violations"]
    assert res["opa_status"] == "emergency_override"
