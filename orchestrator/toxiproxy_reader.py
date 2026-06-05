"""Async reader for Toxiproxy metrics."""

import asyncio
import httpx
import structlog

from metrics_cache import metrics_cache
from config import settings

logger = structlog.get_logger("toxiproxy_reader")

async def fetch_toxiproxy_metrics():
    proxies_url = f"{settings.toxiproxy_api}/proxies"
    
    async with httpx.AsyncClient(timeout=2.0) as client:
        while True:
            try:
                for site in ["cloud", "edge"]:
                    proxy_name = f"{site}-proxy"
                    try:
                        response = await client.get(f"{proxies_url}/{proxy_name}/toxics")
                        response.raise_for_status()
                        toxics = response.json()
                        
                        latency_ms = 0
                        jitter_ms = 0
                        bandwidth_kbps = 100000

                        for toxic in toxics:
                            if toxic["type"] == "latency":
                                latency_ms = toxic["attributes"].get("latency", 0)
                                jitter_ms = toxic["attributes"].get("jitter", 0)
                            elif toxic["type"] == "bandwidth":
                                rate = toxic["attributes"].get("rate", 12500000)
                                bandwidth_kbps = rate * 8 / 1000

                        metrics_cache.update(f"{site}_latency_ms", latency_ms)
                        metrics_cache.update(f"{site}_jitter_ms", jitter_ms)
                        metrics_cache.update(f"{site}_bandwidth_kbps", bandwidth_kbps)
                    except Exception as e:
                        logger.warning("Failed to fetch proxy metrics", site=site, error=str(e))
            except asyncio.CancelledError:
                logger.info("Toxiproxy reader stopped")
                break
            except Exception as e:
                logger.error("Toxiproxy reader error", error=str(e))

            await asyncio.sleep(settings.toxiproxy_reader_interval_s)

def start_toxiproxy_reader():
    """Start the reader as an asyncio task."""
    return asyncio.create_task(fetch_toxiproxy_metrics())

if __name__ == "__main__":
    # Standalone execution
    async def main():
        task = start_toxiproxy_reader()
        try:
            while True:
                data = metrics_cache.get_all()
                print(f"Cloud: {data.get('cloud_latency_ms')}ms | {data.get('cloud_bandwidth_kbps')} Kbps")
                print(f"Edge:  {data.get('edge_latency_ms')}ms | {data.get('edge_bandwidth_kbps')} Kbps")
                print("-" * 50)
                await asyncio.sleep(5)
        except KeyboardInterrupt:
            task.cancel()

    asyncio.run(main())
