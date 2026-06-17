import asyncio
import structlog
from metrics_cache import metrics_cache
from shared_state import shared_state
from config import settings

logger = structlog.get_logger("cost_agent")

# Static Cost configuration (could be moved to config.py later)
CLOUD_COST_PER_1K_TOKENS = 0.001
EDGE_COST_PER_1K_TOKENS = 0.0001
EPSILON = 1e-6

async def run_cost_loop():
    logger.info("Cost Agent starting...")
    while True:
        try:
            data = metrics_cache.get_all()
            
            # 1. Compute Retry Probability
            # using success/failure counts
            c_succ = data.get("cloud_success_count", 0)
            c_fail = data.get("cloud_failure_count", 0)
            e_succ = data.get("edge_success_count", 0)
            e_fail = data.get("edge_failure_count", 0)
            
            c_total = c_succ + c_fail
            e_total = e_succ + e_fail
            
            cloud_retry_prob = (c_fail / c_total) if c_total > 0 else 0.0
            edge_retry_prob = (e_fail / e_total) if e_total > 0 else 0.0
            
            # 2. Compute expected cost per success
            cloud_expected_cost = CLOUD_COST_PER_1K_TOKENS / max(1.0 - cloud_retry_prob, EPSILON)
            edge_expected_cost = EDGE_COST_PER_1K_TOKENS / max(1.0 - edge_retry_prob, EPSILON)
            
            # 3. Convert to modifiers (0.0 to 1.0, where 1.0 is cheapest)
            # Find max expected cost
            max_cost = max(cloud_expected_cost, edge_expected_cost, 0.0001)
            
            # Modifier = 1.0 - (cost / max_cost) -> Actually we want lower cost to be closer to 1.0
            # Let's use simple scaling: max_cost becomes 0.2, min_cost becomes 1.0
            # A simpler way: modifier = base_cheapest / current_expected
            min_possible_cost = min(CLOUD_COST_PER_1K_TOKENS, EDGE_COST_PER_1K_TOKENS)
            
            cloud_modifier = min_possible_cost / cloud_expected_cost
            edge_modifier = min_possible_cost / edge_expected_cost
            
            # Ensure boundaries
            cloud_modifier = max(0.0, min(1.0, cloud_modifier))
            edge_modifier = max(0.0, min(1.0, edge_modifier))
            
            # 4. Push to shared state
            shared_state.update_cost_modifiers(round(cloud_modifier, 4), round(edge_modifier, 4))
            
            logger.debug("Cost modifiers updated", 
                         cloud_prob=round(cloud_retry_prob, 2), 
                         edge_prob=round(edge_retry_prob, 2),
                         cloud_mod=round(cloud_modifier, 2),
                         edge_mod=round(edge_modifier, 2))
            
        except Exception as e:
            logger.error("Cost Agent loop error", error=str(e))
            
        await asyncio.sleep(30)
