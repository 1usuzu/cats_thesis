"""Async retry decorator with exponential backoff and jitter."""

import asyncio
import random
from functools import wraps
import structlog

logger = structlog.get_logger("retry")


def async_retry(max_retries: int = 3, base_delay: float = 0.5, max_delay: float = 5.0):
    """
    Retry an async function with exponential backoff and jitter.
    
    :param max_retries: Maximum number of retry attempts.
    :param base_delay: Initial delay in seconds.
    :param max_delay: Maximum delay in seconds.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Failed after {max_retries} retries", function=func.__name__, error=str(e))
                        raise
                        
                    # Exponential backoff: base_delay * 2^(retries-1)
                    delay = min(base_delay * (2 ** (retries - 1)), max_delay)
                    # Add jitter (±20%)
                    jitter = delay * 0.2
                    delay = delay + random.uniform(-jitter, jitter)
                    
                    logger.warning(
                        f"Attempt {retries} failed, retrying in {delay:.2f}s",
                        function=func.__name__,
                        error=str(e)
                    )
                    await asyncio.sleep(delay)
        return wrapper
    return decorator
