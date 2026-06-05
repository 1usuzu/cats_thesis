"""Async reader for compute metrics (CPU, GPU, Queue)."""

import asyncio
import structlog
import httpx

from metrics_cache import metrics_cache
from config import settings

logger = structlog.get_logger("compute_reader")

async def get_cpu_utilization() -> float:
    def read_cpu_stats():
        try:
            with open("/proc/stat", "r") as f:
                for line in f:
                    if line.startswith("cpu "):
                        parts = [int(i) for i in line.split()[1:]]
                        idle = parts[3] + parts[4]
                        total = sum(parts)
                        return idle, total
        except FileNotFoundError:
            pass
        return 0, 0

    idle1, total1 = read_cpu_stats()
    await asyncio.sleep(0.1)
    idle2, total2 = read_cpu_stats()

    total_delta = total2 - total1
    if total_delta == 0:
        return 0.0
    idle_delta = idle2 - idle1
    return 100.0 * (1.0 - idle_delta / total_delta)

async def fetch_compute_util():
    while True:
        try:
            # GPU utilization for cloud-node via asyncio.create_subprocess_exec
            try:
                proc = await asyncio.create_subprocess_exec(
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu",
                    "--format=csv,noheader,nounits",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL
                )
                stdout, _ = await proc.communicate()
                
                if proc.returncode == 0 and stdout:
                    gpu_util = float(stdout.decode().strip())
                    metrics_cache.update("cloud_gpu_util", gpu_util)
                else:
                    metrics_cache.update("cloud_gpu_util", 0.0)
            except FileNotFoundError:
                metrics_cache.update("cloud_gpu_util", 0.0)

            # CPU utilization for edge-node
            cpu_util = await get_cpu_utilization()
            metrics_cache.update("edge_cpu_util", round(cpu_util, 2))

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Compute reader error", error=str(e))

        await asyncio.sleep(settings.compute_metrics_interval_s)

def start_compute_reader() -> list[asyncio.Task]:
    """Start compute utilization reader as asyncio task."""
    t1 = asyncio.create_task(fetch_compute_util())
    return [t1]

if __name__ == "__main__":
    async def main():
        tasks = start_compute_reader()
        try:
            while True:
                data = metrics_cache.get_all()
                print(f"Cloud GPU: {data.get('cloud_gpu_util')}%")
                print(f"Edge CPU:  {data.get('edge_cpu_util')}%")
                print("-" * 30)
                await asyncio.sleep(2)
        except KeyboardInterrupt:
            for t in tasks:
                t.cancel()

    asyncio.run(main())
