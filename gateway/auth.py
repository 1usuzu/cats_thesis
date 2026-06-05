"""API Key Authentication Middleware."""

import os
from fastapi import Request
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger("auth")

# In production, keys should be loaded from secure storage or vault.
# For thesis demo, we read from env var or use a default.
VALID_API_KEYS = {k.strip() for k in os.getenv("CATS_API_KEYS", "").split(",") if k.strip()}

async def api_key_auth_middleware(request: Request, call_next):
    # Bypass paths
    if request.url.path.startswith("/health") or request.url.path.startswith("/docs") or request.url.path.startswith("/openapi"):
        return await call_next(request)

    api_key = request.headers.get("X-API-Key")
    
    if not api_key:
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized", "detail": "Missing X-API-Key header"}
        )
        
    if api_key not in VALID_API_KEYS:
        logger.warning("Invalid API Key attempt", path=request.url.path)
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized", "detail": "Invalid API Key"}
        )

    return await call_next(request)
