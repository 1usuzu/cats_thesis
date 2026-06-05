"""Circuit Breaker pattern for inference nodes."""

import time
from enum import Enum
import structlog

logger = structlog.get_logger("circuit_breaker")

class CircuitState(Enum):
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Failing, fast-fail requests
    HALF_OPEN = "HALF_OPEN" # Testing recovery


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = 0.0

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            now = time.time()
            if now - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker entering HALF_OPEN state")
                return True
            return False
            
        if self.state == CircuitState.HALF_OPEN:
            return True
            
        return True

    def record_success(self):
        if self.state == CircuitState.HALF_OPEN:
            logger.info("Circuit breaker recovered, entering CLOSED state")
            self.state = CircuitState.CLOSED
            self.failures = 0
        elif self.state == CircuitState.CLOSED:
            self.failures = 0

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.CLOSED and self.failures >= self.failure_threshold:
            logger.warning("Circuit breaker tripped, entering OPEN state")
            self.state = CircuitState.OPEN
            
        elif self.state == CircuitState.HALF_OPEN:
            logger.warning("Circuit breaker recovery failed, returning to OPEN state")
            self.state = CircuitState.OPEN

    def get_state(self) -> str:
        return self.state.value


class CircuitBreakerRegistry:
    def __init__(self):
        self.breakers = {
            "cloud": CircuitBreaker(),
            "edge": CircuitBreaker()
        }

    def get(self, site: str) -> CircuitBreaker:
        return self.breakers[site]
        
    def get_states(self) -> dict:
        return {site: cb.get_state() for site, cb in self.breakers.items()}


circuit_breakers = CircuitBreakerRegistry()
