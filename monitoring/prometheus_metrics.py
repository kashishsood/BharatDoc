"""
BharatDoc-VLM: Prometheus Metrics
====================================

Instruments the inference server with production-grade metrics:
- request_latency_seconds (histogram)
- prediction_confidence (gauge)
- requests_total by doc_type (counter)
- validation_errors_total (counter)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Prometheus metrics collector for inference server.
    Falls back to in-memory counters if prometheus_client not installed.
    """

    def __init__(self):
        self._use_prometheus = False
        try:
            from prometheus_client import Histogram, Gauge, Counter, start_http_server, REGISTRY

            # Use REGISTRY to avoid duplicate metric registration (e.g. with multiple workers)
            def _get_or_create(metric_cls, name, *args, **kwargs):
                """Return existing metric if already registered, else create new."""
                if name in REGISTRY._names_to_collectors:
                    return REGISTRY._names_to_collectors[name]
                return metric_cls(name, *args, **kwargs)

            self.latency = _get_or_create(
                Histogram,
                "request_latency_seconds",
                "Request latency in seconds",
                ["doc_type", "version"],
                buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0],
            )
            self.confidence = _get_or_create(
                Gauge,
                "prediction_confidence",
                "Model prediction confidence score",
                ["doc_type"],
            )
            self.requests_total = _get_or_create(
                Counter,
                "requests_total",
                "Total requests by doc type",
                ["doc_type", "status"],
            )
            self.validation_errors = _get_or_create(
                Counter,
                "validation_errors_total",
                "Total schema validation errors",
                ["doc_type"],
            )
            # Start metrics HTTP server on port 9090
            try:
                start_http_server(9090)
                logger.info("Prometheus metrics server started on :9090")
            except OSError:
                logger.warning("Prometheus metrics port 9090 already in use")

            self._use_prometheus = True
            logger.info("Prometheus metrics initialized")

        except ImportError:
            logger.warning("prometheus_client not installed, using in-memory counters")
            self._counters = {"requests": {}, "errors": {}, "latencies": []}

    def record_request(self, doc_type: str, latency_ms: float,
                       confidence: float, version: str = "v1"):
        """Record a successful request."""
        if self._use_prometheus:
            self.latency.labels(doc_type=doc_type, version=version).observe(latency_ms / 1000)
            self.confidence.labels(doc_type=doc_type).set(confidence)
            self.requests_total.labels(doc_type=doc_type, status="success").inc()
        else:
            self._counters["latencies"].append(latency_ms)
            self._counters["requests"][doc_type] = self._counters["requests"].get(doc_type, 0) + 1

    def record_error(self, doc_type: str):
        """Record a failed request."""
        if self._use_prometheus:
            self.requests_total.labels(doc_type=doc_type, status="error").inc()
        else:
            self._counters["errors"][doc_type] = self._counters["errors"].get(doc_type, 0) + 1

    def record_validation_error(self, doc_type: str):
        """Record a schema validation error."""
        if self._use_prometheus:
            self.validation_errors.labels(doc_type=doc_type).inc()

    def get_summary(self) -> dict:
        """Get metrics summary (for health check endpoints)."""
        if self._use_prometheus:
            return {"backend": "prometheus", "endpoint": "http://localhost:9090/metrics"}
        return {"backend": "in-memory", "counters": self._counters}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    m = MetricsCollector()
    m.record_request("aadhaar", 150.0, 0.92)
    m.record_request("invoice", 200.0, 0.85)
    m.record_error("aadhaar")
    print(f"Metrics summary: {m.get_summary()}")
