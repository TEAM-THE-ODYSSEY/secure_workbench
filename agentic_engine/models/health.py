from __future__ import annotations

import logging
import time
import urllib.request
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger("agentic_engine.models.health")


class ModelHealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass
class HealthCheckResult:
    model_id: str
    status: ModelHealthStatus
    latency_ms: float
    error: Optional[str] = None


class ModelHealthMonitor:
    """Monitors model provider endpoint responsiveness and tracks circuit breaker status."""

    def __init__(self, failure_threshold: int = 3, recovery_timeout_s: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_s = recovery_timeout_s
        self._failure_counts: Dict[str, int] = {}
        self._last_failure_time: Dict[str, float] = {}

    def check_endpoint(self, endpoint: str = "http://localhost:11434", timeout_s: float = 2.0) -> HealthCheckResult:
        """Pings Ollama or model backend endpoint."""
        start = time.time()
        try:
            req = urllib.request.Request(f"{endpoint}/api/tags", headers={"User-Agent": "AgenticEngine-HealthCheck"})
            with urllib.request.urlopen(req, timeout=timeout_s) as response:
                if response.status == 200:
                    latency = (time.time() - start) * 1000
                    return HealthCheckResult(
                        model_id=endpoint,
                        status=ModelHealthStatus.HEALTHY,
                        latency_ms=round(latency, 2),
                    )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return HealthCheckResult(
                model_id=endpoint,
                status=ModelHealthStatus.UNAVAILABLE,
                latency_ms=round(latency, 2),
                error=str(e),
            )
        return HealthCheckResult(
            model_id=endpoint,
            status=ModelHealthStatus.DEGRADED,
            latency_ms=round((time.time() - start) * 1000, 2),
        )

    def record_failure(self, model_id: str) -> None:
        self._failure_counts[model_id] = self._failure_counts.get(model_id, 0) + 1
        self._last_failure_time[model_id] = time.time()
        logger.warning(f"Recorded failure for model {model_id}. Count: {self._failure_counts[model_id]}")

    def record_success(self, model_id: str) -> None:
        self._failure_counts[model_id] = 0

    def is_available(self, model_id: str) -> bool:
        failures = self._failure_counts.get(model_id, 0)
        if failures >= self.failure_threshold:
            last_fail = self._last_failure_time.get(model_id, 0)
            if (time.time() - last_fail) < self.recovery_timeout_s:
                return False  # Circuit breaker open
            # Half-open: allow probe
            self._failure_counts[model_id] = self.failure_threshold - 1
        return True
