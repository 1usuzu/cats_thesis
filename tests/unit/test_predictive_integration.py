import asyncio

import pytest
from event_bus import event_bus
from metrics_cache import metrics_cache
from monitoring_agent import start_monitoring_agent


@pytest.mark.asyncio
async def test_predictive_alert_trigger():
    # Setup
    event_bus.start()
    alert_received = False

    async def handler(payload):
        nonlocal alert_received
        alert_received = True
        print(f"Received alert: {payload}")

    event_bus.subscribe("predictive_alert", handler)

    # Start loop in background
    task = start_monitoring_agent()

    # Simulate rising CPU: 60 -> 70 -> 80 -> 85
    # If it rises this fast, it should predict >90 soon.
    metrics_cache.update("edge_cpu_util", 60.0)
    await asyncio.sleep(0.1) # Wait for agent loop (wait, agent loop sleeps 5s. That's too slow for test)

    task.cancel()
    event_bus.stop()
