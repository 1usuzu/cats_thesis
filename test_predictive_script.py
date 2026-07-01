import asyncio

from event_bus import event_bus
from metrics_cache import metrics_cache
from monitoring_agent import holt_linear_trend
from policy_agent import handle_predictive_alert


async def main():
    print("Testing predictive alert loop...")
    event_bus.start()
    event_bus.subscribe("predictive_alert", handle_predictive_alert)

    # Simulate metrics history
    # 3 periods: 60, 70, 80, 85
    metrics_cache.update("edge_cpu_util", 60)
    metrics_cache.update("edge_cpu_util", 70)
    metrics_cache.update("edge_cpu_util", 80)
    metrics_cache.update("edge_cpu_util", 85)

    cpu_history = metrics_cache.get_history("edge_cpu_util")
    pred = holt_linear_trend(cpu_history, steps_ahead=6)
    print(f"Predicted CPU: {pred}")

    if pred > 90:
        print("Publishing predictive alert...")
        await event_bus.publish("predictive_alert", {
            "signal": "edge_cpu_util",
            "current_value": 85,
            "forecast_value": round(pred, 2)
        })

    await asyncio.sleep(1) # wait for event
    event_bus.stop()

asyncio.run(main())
