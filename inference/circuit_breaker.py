"""
BharatDoc-VLM: Circuit Breaker
=================================

Monitors request latencies and trips to a fallback model if the primary
model is too slow (> 2s threshold). Auto-recovers after cool-down.

Pattern: Circuit Breaker from distributed systems, applied to ML serving.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"      # Normal operation, using primary model
    OPEN = "open"          # Tripped, using fallback model
    HALF_OPEN = "half_open"  # Testing if primary has recovered


class CircuitBreaker:
    """
    Circuit breaker for ML inference latency protection.
    
    If last N requests exceeded latency_threshold, switches to fallback.
    After cooldown_seconds, tries primary again (half-open state).
    """

    def __init__(self, failure_threshold: int = 5, latency_threshold_ms: float = 2000,
                 cooldown_seconds: float = 30.0, window_size: int = 10):
        self.failure_threshold = failure_threshold
        self.latency_threshold = latency_threshold_ms
        self.cooldown_seconds = cooldown_seconds
        self.window_size = window_size
        self.state = CircuitState.CLOSED
        self.latencies = deque(maxlen=window_size)
        self.last_trip_time = 0.0
        self.trip_count = 0

    def record_latency(self, latency_ms: float):
        """Record a request latency and update circuit state."""
        self.latencies.append(latency_ms)

        if self.state == CircuitState.OPEN:
            if time.time() - self.last_trip_time > self.cooldown_seconds:
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker: HALF_OPEN (testing primary)")
            return

        if self.state == CircuitState.HALF_OPEN:
            if latency_ms <= self.latency_threshold:
                self.state = CircuitState.CLOSED
                logger.info("Circuit breaker: CLOSED (primary recovered)")
            else:
                self._trip()
            return

        # Check if we should trip
        recent = list(self.latencies)[-self.failure_threshold:]
        slow_count = sum(1 for l in recent if l > self.latency_threshold)
        if slow_count >= self.failure_threshold:
            self._trip()

    def _trip(self):
        """Trip the circuit breaker to OPEN state."""
        self.state = CircuitState.OPEN
        self.last_trip_time = time.time()
        self.trip_count += 1
        logger.warning(f"Circuit breaker TRIPPED (trip #{self.trip_count})")

    @property
    def should_use_fallback(self) -> bool:
        return self.state in (CircuitState.OPEN, CircuitState.HALF_OPEN)

    def get_status(self) -> dict:
        avg_latency = sum(self.latencies) / len(self.latencies) if self.latencies else 0
        return {
            "state": self.state.value,
            "trip_count": self.trip_count,
            "avg_latency_ms": round(avg_latency, 2),
            "recent_latencies": list(self.latencies),
            "using_fallback": self.should_use_fallback,
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cb = CircuitBreaker(failure_threshold=3, latency_threshold_ms=500)

    # Simulate normal, then slow, then recovery
    for lat in [100, 120, 110, 600, 700, 800, 650, 700]:
        cb.record_latency(lat)
        print(f"  Latency: {lat}ms → State: {cb.state.value}")
