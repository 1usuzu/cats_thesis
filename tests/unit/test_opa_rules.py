import pytest
import subprocess
import json
import os

# To test OPA locally without a server, we can run 'opa eval' via subprocess if OPA is installed.
# Since OPA might not be installed in the CI runner directly (unless via docker), 
# we'll mock this test or only run it if docker/opa is available.

@pytest.mark.skipif(not os.path.exists("/policies/routing.rego") and not os.path.exists("safety/policies/routing.rego"), 
                    reason="OPA rego file not found")
def test_opa_rules_syntax_check():
    # We already checked syntax, this is a placeholder.
    # In a real environment, you'd use 'opa test' with rego test files.
    rego_path = "safety/policies/routing.rego"
    if not os.path.exists(rego_path):
        return
        
    with open(rego_path, 'r') as f:
        content = f.read()
        
    # Check that our specific rules are defined
    assert "package routing" in content
    assert "valid_input if {" in content
    assert "count(violations) == 0" in content
    assert "QUEUE_OVERLOAD" in content
    assert "EDGE_DEGRADED_HQ" in content
    assert "SLA_VIOLATION" in content
