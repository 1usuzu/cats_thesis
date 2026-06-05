"""Rate Limiting Middleware using Token Bucket algorithm."""

import time
import asyncio
from fastapi import Request
from fastapi.responses import JSONResponse
import structlog
from config import settings

logger = structlog.get_logger("rate_limiter")


class RateLimiter:
    def __init__(self, rate: float, burst: int):
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self) -> bool:
        async with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            
            # Replenish tokens
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            return False


# Global rate limiter instance
limiter = RateLimiter(rate=settings.rate_limit_per_second, burst=settings.rate_limit_burst)


async def rate_limit_middleware(request: Request, call_next):
    # Bypass health checks
    if request.url.path.startswith("/health") or request.url.path == "/":
        return await call_next(request)

    allowed = await limiter.acquire()
    if not allowed:
        logger.warning("Rate limit exceeded", path=request.url.path, client=request.client.host if request.client else None)
        return JSONResponse(
            status_code=429,
            content={"error": "Too Many Requests"},
            headers={"Retry-After": "1"}
        )
        
    return await call_next(request)
