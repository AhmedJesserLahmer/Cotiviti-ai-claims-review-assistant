"""Re-export of the shared circuit breaker (implemented in claims_common)."""

from claims_common.resilience.circuit_breaker import CircuitBreaker, CircuitState

__all__ = ["CircuitBreaker", "CircuitState"]
