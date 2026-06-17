import asyncio
import json
import random
import time
import httpx
import structlog
from metrics_cache import metrics_cache
from shared_state import shared_state
from config import settings

logger = structlog.get_logger("tuning_agent")

ACTIONS = {
    "BALANCED": {"w_latency": 0.30, "w_queue": 0.30, "w_compute": 0.25},
    "LATENCY_FOCUS": {"w_latency": 0.50, "w_queue": 0.15, "w_compute": 0.20},
    "THROUGHPUT_FOCUS": {"w_latency": 0.15, "w_queue": 0.45, "w_compute": 0.25}
}

STATES = [
    "STATE_NORMAL", 
    "STATE_EDGE_LOADED", 
    "STATE_DEGRADED", 
    "STATE_BURST", 
    "STATE_CRITICAL"
]

# Initialize Q-Table
Q_TABLE = {s: {a: 0.0 for a in ACTIONS} for s in STATES}

# Q-Learning Hyperparameters
ALPHA = 0.1
GAMMA = 0.9
EPSILON = 0.15

async def llm_warm_start():
    """Calls the LLM to populate initial Q-Values for a warm start."""
    api_url = f"{settings.strategic_agent_url}/api/generate"
    prompt = """You are an AI supervisor initializing a Reinforcement Learning agent for network routing.
For each of the following 5 network states, select the BEST routing action profile.
States: STATE_NORMAL, STATE_EDGE_LOADED, STATE_DEGRADED, STATE_BURST, STATE_CRITICAL
Actions: BALANCED, LATENCY_FOCUS, THROUGHPUT_FOCUS

Rules:
- STATE_EDGE_LOADED means edge queue is full -> prioritize THROUGHPUT_FOCUS (queue).
- STATE_DEGRADED means latency is high -> prioritize LATENCY_FOCUS.
- Return ONLY a valid JSON object mapping State to Action. No markdown, no explanations.
Example: {"STATE_NORMAL": "BALANCED", ...}
"""
    payload = {"model": settings.strategic_agent_model, "prompt": prompt, "stream": False, "format": "json"}
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(api_url, json=payload)
            res.raise_for_status()
            response_text = res.json().get("response", "").strip()
            
            mapping = json.loads(response_text)
            for state, action in mapping.items():
                if state in Q_TABLE and action in ACTIONS:
                    Q_TABLE[state][action] = 10.0 # Warm start boost
            
            logger.info("LLM Warm-Start completed", mapping=mapping)
    except Exception as e:
        logger.warning("LLM Warm-Start failed, falling back to empty Q-Table", error=str(e))
        # Fallback manual warm start
        Q_TABLE["STATE_NORMAL"]["BALANCED"] = 10.0
        Q_TABLE["STATE_DEGRADED"]["LATENCY_FOCUS"] = 10.0
        Q_TABLE["STATE_EDGE_LOADED"]["THROUGHPUT_FOCUS"] = 10.0


async def run_tuning_loop():
    logger.info("Starting Tuning Agent (Q-Learning + LLM Warm-Start)")
    await llm_warm_start()
    
    last_state, _ = shared_state.get()
    last_action = "BALANCED"
    
    while True:
        await asyncio.sleep(5.0) # Tuning interval
        
        current_state, _ = shared_state.get()
        
        # Calculate Reward based on metrics
        data = metrics_cache.get_all()
        c_lat = data.get("cloud_latency_ms", 0.0)
        e_lat = data.get("edge_latency_ms", 0.0)
        c_inf = data.get("cloud_gateway_inflight", 0)
        e_inf = data.get("edge_gateway_inflight", 0)
        
        avg_lat = (c_lat + e_lat) / 2.0
        avg_inf = (c_inf + e_inf) / 2.0
        
        if avg_lat <= 0: avg_lat = 1.0
        
        # Reward formula: penalize high latency and high queues
        reward = 1000.0 / (avg_lat + avg_inf * 10)
        
        # Bellman Update
        max_q_next = max(Q_TABLE[current_state].values())
        current_q = Q_TABLE[last_state][last_action]
        Q_TABLE[last_state][last_action] += ALPHA * (reward + GAMMA * max_q_next - current_q)
        
        # Epsilon-Greedy Action Selection
        if random.random() < EPSILON:
            next_action = random.choice(list(ACTIONS.keys()))
            is_exploration = True
        else:
            next_action = max(Q_TABLE[current_state], key=Q_TABLE[current_state].get)
            is_exploration = False
            
        # Apply Action
        weights = ACTIONS[next_action]
        shared_state.update_dynamic_weights(
            w_lat=weights["w_latency"], 
            w_queue=weights["w_queue"], 
            w_comp=weights["w_compute"]
        )
        
        logger.debug(
            "Tuning step completed", 
            state=current_state, 
            action=next_action, 
            reward=round(reward, 2), 
            explored=is_exploration,
            q_values={k: round(v, 2) for k, v in Q_TABLE[current_state].items()}
        )
        
        last_state = current_state
        last_action = next_action

def start_tuning_agent():
    return asyncio.create_task(run_tuning_loop())
