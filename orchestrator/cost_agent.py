import asyncio

import structlog
from config import settings
from event_bus import event_bus
from metrics_cache import metrics_cache
from shared_state import shared_state

logger = structlog.get_logger("cost_agent")

# Phase 2 Cost Model
EPSILON = 1e-6

async def run_cost_loop():
    logger.info("Cost Agent starting...")
    while True:
        try:
            data = metrics_cache.get_all()

            # 1. Compute Empirical Probabilities (Retry & SLA Miss)
            c_succ = data.get("cloud_success_count", 0)
            c_fail = data.get("cloud_failure_count", 0)
            c_sla_miss = data.get("cloud_sla_miss_count", 0)

            e_succ = data.get("edge_success_count", 0)
            e_fail = data.get("edge_failure_count", 0)
            e_sla_miss = data.get("edge_sla_miss_count", 0)

            c_total = c_succ + c_fail
            e_total = e_succ + e_fail

            cloud_retry_prob = (c_fail / c_total) if c_total > 0 else 0.0
            edge_retry_prob = (e_fail / e_total) if e_total > 0 else 0.0

            cloud_sla_prob = (c_sla_miss / c_total) if c_total > 0 else 0.0
            edge_sla_prob = (e_sla_miss / e_total) if e_total > 0 else 0.0

            # 2. Compute Base Cost
            cloud_base_cost = settings.cost_inference_cloud + settings.cost_network_cloud
            edge_base_cost = settings.cost_inference_edge + settings.cost_network_edge

            # 3. Compute Expected Cost (Full Formula)
            # Expected Cost = (Base / (1 - RetryProb)) + FallbackCost + (SLA_Prob * SLA_Penalty)
            cloud_expected_cost = (
                (cloud_base_cost / max(1.0 - cloud_retry_prob, EPSILON)) +
                (cloud_retry_prob * edge_base_cost) +
                (cloud_sla_prob * settings.cost_sla_penalty)
            )

            edge_expected_cost = (
                (edge_base_cost / max(1.0 - edge_retry_prob, EPSILON)) +
                (edge_retry_prob * cloud_base_cost) +
                (edge_sla_prob * settings.cost_sla_penalty)
            )

            # 4. Convert Expected Cost to Normalized Modifiers
            min_possible_cost = min(cloud_base_cost, edge_base_cost)

            cloud_modifier = min_possible_cost / cloud_expected_cost
            edge_modifier = min_possible_cost / edge_expected_cost

            # Ensure boundaries [0.0, 1.0]
            cloud_modifier = max(0.0, min(1.0, cloud_modifier))
            edge_modifier = max(0.0, min(1.0, edge_modifier))

            # Record explicit cost metrics in cache for telemetry
            metrics_cache.update("cloud_expected_cost", round(cloud_expected_cost, 4))
            metrics_cache.update("edge_expected_cost", round(edge_expected_cost, 4))
            metrics_cache.update("cloud_cost_modifier", round(cloud_modifier, 4))
            metrics_cache.update("edge_cost_modifier", round(edge_modifier, 4))

            # 5. Push to shared state
            shared_state.update_cost_modifiers(round(cloud_modifier, 4), round(edge_modifier, 4))

            logger.debug("Cost model updated",
                         cloud_exp_cost=round(cloud_expected_cost, 4),
                         edge_exp_cost=round(edge_expected_cost, 4),
                         cloud_mod=round(cloud_modifier, 2),
                         edge_mod=round(edge_modifier, 2),
                         c_retry=round(cloud_retry_prob, 2),
                         e_retry=round(edge_retry_prob, 2),
                         c_sla=round(cloud_sla_prob, 2),
                         e_sla=round(edge_sla_prob, 2))

            # Phase 5: Publish cost_report periodically
            if not hasattr(run_cost_loop, "iteration"):
                run_cost_loop.iteration = 0
            run_cost_loop.iteration += 1
            if run_cost_loop.iteration >= 10:  # Every 5 mins (30s * 10)
                await event_bus.publish("cost_report", {
                    "cloud_expected_cost": round(cloud_expected_cost, 4),
                    "edge_expected_cost": round(edge_expected_cost, 4),
                    "cloud_modifier": round(cloud_modifier, 4),
                    "edge_modifier": round(edge_modifier, 4)
                })
                run_cost_loop.iteration = 0

        except Exception as e:
            logger.error("Cost Agent loop error", error=str(e))

        await asyncio.sleep(30)
