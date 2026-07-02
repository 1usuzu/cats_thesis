import asyncio
import os

import structlog
from shared_state import shared_state

logger = structlog.get_logger("policy_agent")

POLICY_PATH = "/safety/policies/routing.rego" if os.path.exists("/safety/policies/routing.rego") else "safety/policies/routing.rego"

async def policy_agent_loop():
    """
    Simulates a Policy Agent that occasionally proposes Rego policy updates.
    In a full LLM implementation, this would prompt the Strategic Agent model.
    Here we simulate proposing a stricter QUEUE_OVERLOAD threshold (50 -> 40).
    """
    while True:
        await asyncio.sleep(120)  # Wake up every 2 minutes

        # Only propose if there is no pending proposal
        prop_state = shared_state.get_policy_proposal()
        if not prop_state["has_proposal"]:
            try:
                # Read current policy
                with open(POLICY_PATH, "r") as f:
                    current_rego = f.read()

                # Propose a stricter queue limit: change 'input.gateway_inflight > 50' to '40'
                if "input.gateway_inflight > 50" in current_rego:
                    logger.info("Policy Agent: Proposing a stricter gateway_inflight threshold (50 -> 40).")
                    proposed_rego = current_rego.replace("input.gateway_inflight > 50", "input.gateway_inflight > 40")
                    shared_state.set_policy_proposal(proposed_rego)

            except Exception as e:
                logger.error(f"Policy Agent failed to read/propose policy: {e}")

def trigger_policy_proposal_manually(target_inflight=None):
    """For manual testing via API, or predictive alerts."""
    try:
        with open(POLICY_PATH, "r") as f:
            current_rego = f.read()

        # If a target is specified by predictive alert, use it. Otherwise toggle between 50 and 40.
        if target_inflight is not None:
            import re
            proposed_rego = re.sub(r"input\.gateway_inflight > \d+", f"input.gateway_inflight > {target_inflight}", current_rego)
        else:
            if "input.gateway_inflight > 50" in current_rego:
                proposed_rego = current_rego.replace("input.gateway_inflight > 50", "input.gateway_inflight > 40")
            elif "input.gateway_inflight > 40" in current_rego:
                proposed_rego = current_rego.replace("input.gateway_inflight > 40", "input.gateway_inflight > 50")
            else:
                proposed_rego = current_rego

        shared_state.set_policy_proposal(proposed_rego)
        return True
    except Exception:
        logger.error("Failed to generate valid JSON proposal.")
        return {"error": "JSON parse failed"}


async def handle_anomaly(payload: dict):
    """
    Event handler for anomalies published on the Event Bus.
    """
    logger.info("Policy Agent received anomaly. Analyzing and proposing reactive policy update...")

    # 1. Generate Proposal (Reactive: lower limit to 40)
    res = trigger_policy_proposal_manually(target_inflight=40)
    if isinstance(res, dict) and "error" in res:
        logger.error(f"Auto-proposal failed: {res['error']}")
        return

    proposed_rego = shared_state.get_policy_proposal().get("proposed_policy")
    if not proposed_rego:
        return

    # 3. Call Critic Agent automatically
    from critic_agent import validate_policy_proposal
    val_res = await validate_policy_proposal(proposed_rego)
    shared_state.set_policy_validation(val_res)

    logger.info("Policy Agent completed reactive auto-proposal. Waiting for Human Approval.")


async def handle_predictive_alert(payload: dict):
    """
    Phase 6: Event handler for predictive alerts published on the Event Bus.
    Proactively proposes tighter constraints before anomalies happen.
    """
    logger.info("Policy Agent received PREDICTIVE alert. Generating preemptive policy update...", payload=payload)

    # 1. Generate Proposal (Preemptive: lower limit tighter, e.g. 35 to prevent queue buildup)
    res = trigger_policy_proposal_manually(target_inflight=35)
    if isinstance(res, dict) and "error" in res:
        logger.error(f"Auto-proposal failed: {res['error']}")
        return

    proposed_rego = shared_state.get_policy_proposal().get("proposed_policy")
    if not proposed_rego:
        return

    # 3. Call Critic Agent automatically
    from critic_agent import validate_policy_proposal
    val_res = await validate_policy_proposal(proposed_rego)
    shared_state.set_policy_validation(val_res)

    logger.info("Policy Agent completed preemptive auto-proposal. Waiting for Human Approval on Dashboard.")
