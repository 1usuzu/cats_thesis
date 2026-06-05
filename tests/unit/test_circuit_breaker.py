import pytest
from circuit_breaker import CircuitBreaker, CircuitState

def test_circuit_breaker_initial_state():
    cb = CircuitBreaker()
    assert cb.get_state() == CircuitState.CLOSED.value
    assert cb.can_execute() is True

def test_circuit_breaker_trips_on_failures():
    cb = CircuitBreaker(failure_threshold=3)
    
    # 2 failures -> should still be CLOSED
    cb.record_failure()
    cb.record_failure()
    assert cb.get_state() == CircuitState.CLOSED.value
    assert cb.can_execute() is True
    
    # 3rd failure -> should trip to OPEN
    cb.record_failure()
    assert cb.get_state() == CircuitState.OPEN.value
    assert cb.can_execute() is False

def test_circuit_breaker_recovers_after_timeout():
    # Use a very short timeout for testing
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
    
    cb.record_failure()
    assert cb.get_state() == CircuitState.OPEN.value
    
    # Immediately after, still OPEN
    assert cb.can_execute() is False
    
    # Wait for timeout
    import time
    time.sleep(0.15)
    
    # Now should be HALF_OPEN and allow one execution
    assert cb.can_execute() is True
    assert cb.get_state() == CircuitState.HALF_OPEN.value
    
    # If successful, should reset to CLOSED
    cb.record_success()
    assert cb.get_state() == CircuitState.CLOSED.value
    assert cb.can_execute() is True

def test_circuit_breaker_fails_again_in_half_open():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
    cb.record_failure()
    
    import time
    time.sleep(0.15)
    assert cb.can_execute() is True # Transitions to HALF_OPEN
    
    # Fails again -> goes back to OPEN
    cb.record_failure()
    assert cb.get_state() == CircuitState.OPEN.value
    assert cb.can_execute() is False

def test_circuit_breaker_success_resets_failure_count():
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure()
    cb.record_failure()
    
    # Success resets count
    cb.record_success()
    
    # Now 2 failures shouldn't trip it
    cb.record_failure()
    cb.record_failure()
    assert cb.get_state() == CircuitState.CLOSED.value
    assert cb.can_execute() is True
