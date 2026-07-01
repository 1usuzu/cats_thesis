import asyncio
import logging
import os
import subprocess

from shared_state import shared_state

logger = logging.getLogger(__name__)

POLICIES_DIR = "/safety/policies"
PROPOSED_PATH = os.path.join(POLICIES_DIR, "proposed_routing.rego")
TEST_PATH = os.path.join(POLICIES_DIR, "routing_test.rego")

async def critic_agent_loop():
    """
    Critic Agent Pipeline:
    Continuously monitors for new Policy Proposals and validates them.
    """
    while True:
        await asyncio.sleep(5)

        prop_state = shared_state.get_policy_proposal()
        if prop_state["has_proposal"] and prop_state["validation_results"].get("status") == "PENDING":
            logger.info("Critic Agent: Found pending policy proposal. Starting validation pipeline.")

            shared_state.update_policy_validation("VALIDATING", "Writing proposed policy to disk...")

            try:
                # 1. Write to temp file
                with open(PROPOSED_PATH, "w") as f:
                    f.write(prop_state["proposed_policy"])

                # 2. Syntax Check
                shared_state.update_policy_validation("VALIDATING", "Running opa check...")
                check_res = subprocess.run(["opa", "check", PROPOSED_PATH], capture_output=True, text=True)
                if check_res.returncode != 0:
                    shared_state.update_policy_validation("REJECTED", f"Syntax error:\n{check_res.stderr}")
                    continue

                # 3. Invariant Tests
                shared_state.update_policy_validation("VALIDATING", "Running opa test...")
                test_res = subprocess.run(["opa", "test", TEST_PATH, PROPOSED_PATH], capture_output=True, text=True)

                # OPA test returns 0 on success, >0 if tests fail
                if test_res.returncode == 0:
                    shared_state.update_policy_validation("PASSED", "All tests passed. Ready for Human Approval.")
                    logger.info("Critic Agent: Validation PASSED.")
                else:
                    shared_state.update_policy_validation("REJECTED", f"Invariant test failed:\n{test_res.stdout}\n{test_res.stderr}")
                    logger.warning("Critic Agent: Validation REJECTED due to test failures.")

            except Exception as e:
                logger.error(f"Critic Agent failed to run pipeline: {e}")
                shared_state.update_policy_validation("REJECTED", f"Internal validation error: {str(e)}")
            finally:
                # Keep the proposed file on disk so we can diff it later, or clean it up if rejected?
                # We'll leave it. The main API will read from shared_state anyway.
                pass
