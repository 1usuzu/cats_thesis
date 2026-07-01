import asyncio
import time

import structlog
from event_bus import event_bus
from metrics_cache import metrics_cache

logger = structlog.get_logger()

def holt_linear_trend(series: list[float], alpha=0.3, beta=0.1, steps_ahead=6) -> float:
    """
    Holt's Linear Trend Method (Double Exponential Smoothing).
    Predicts the value `steps_ahead` into the future.
    """
    if len(series) < 2:
        return series[-1] if series else 0.0

    level = series[0]
    trend = series[1] - series[0]

    for y in series[1:]:
        last_level = level
        level = alpha * y + (1 - alpha) * (level + trend)
        trend = beta * (level - last_level) + (1 - beta) * trend

    return level + steps_ahead * trend

async def monitoring_agent_loop():
    """
    Monitoring Agent: Continuously monitors telemetry for anomalies and predictive risks.
    Runs every 5 seconds.
    """
    logger.info("Monitoring Agent started")

    # State tracking to avoid spamming
    last_anomaly_time = 0
    last_predictive_time = 0
    cooldown = 30  # Don't publish another alert for 30s

    edge_high_cpu_count = 0

    # Phase 6: History is now tracked natively in metrics_cache.py

    while True:
        try:
            data = metrics_cache.get_all()

            edge_cpu = data.get("edge_cpu_util", 0)
            edge_inflight = data.get("edge_gateway_inflight", 0)

            cpu_history = metrics_cache.get_history("edge_cpu_util")
            inflight_history = metrics_cache.get_history("edge_gateway_inflight")

            now = time.time()

            # 2. Phase 6: Predictive Analysis (Forecast next 30 seconds = 6 steps)
            if len(cpu_history) >= 4:
                predicted_cpu = holt_linear_trend(cpu_history, steps_ahead=6)
                predicted_inflight = holt_linear_trend(inflight_history, steps_ahead=6)

                if (predicted_cpu > 90.0 or predicted_inflight > 40.0) and (now - last_predictive_time) > cooldown:
                    await event_bus.publish("predictive_alert", {
                        "signal": "edge_cpu_util" if predicted_cpu > 90.0 else "edge_gateway_inflight",
                        "current_value": edge_cpu if predicted_cpu > 90.0 else edge_inflight,
                        "forecast_value": round(predicted_cpu if predicted_cpu > 90.0 else predicted_inflight, 2),
                        "time_horizon_sec": 30,
                        "risk": "high",
                        "message": f"Preemptive Alert: Forecasted {'CPU' if predicted_cpu > 90 else 'Inflight Queue'} to reach critical levels in 30s."
                    })
                    last_predictive_time = now

            # 3. Phase 5: Reactive Anomaly Detection
            if edge_cpu > 90:  # Restored to normal threshold
                edge_high_cpu_count += 1
            else:
                edge_high_cpu_count = 0

            if edge_high_cpu_count >= 2 and (now - last_anomaly_time) > cooldown:
                # Trigger anomaly
                await event_bus.publish("anomaly", {
                    "signal": "edge_cpu_util",
                    "value": edge_cpu,
                    "trend": "rising",
                    "risk": "high",
                    "message": f"Edge CPU utilization critically high ({edge_cpu}%) for consecutive periods."
                })
                last_anomaly_time = now
                edge_high_cpu_count = 0

        except Exception as e:
            logger.error("Error in Monitoring Agent loop", error=str(e))

        await asyncio.sleep(5)

def start_monitoring_agent():
    return asyncio.create_task(monitoring_agent_loop())
