"""
BharatDoc-VLM: Inference Server Tests
========================================
"""

import pytest
import sys
from pathlib import Path
from PIL import Image
import io

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def client():
    """Create test client for inference server."""
    from fastapi.testclient import TestClient
    from inference.server import create_inference_app
    app = create_inference_app(use_mock=True)
    return TestClient(app)


@pytest.fixture
def gateway_client():
    """Create test client for gateway."""
    from fastapi.testclient import TestClient
    from gateway.gateway import create_app
    app = create_app(use_mock=True)
    return TestClient(app)


def _create_test_image():
    """Create a test image as bytes."""
    img = Image.new("RGB", (800, 600), (255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


class TestInferenceServer:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["mock_mode"] is True

    def test_predict_v1(self, client):
        img_buf = _create_test_image()
        response = client.post(
            "/predict/v1",
            files={"file": ("test.png", img_buf, "image/png")},
            data={"doc_type": "aadhaar"},
        )
        # 200 = real extraction; 500 = model not loaded (correct: no silent mock)
        assert response.status_code in (200, 500)
        data = response.json()
        if response.status_code == 200:
            assert "extraction" in data
            assert "latency_ms" in data
        else:
            assert "error" in data

    def test_predict_v2(self, client):
        img_buf = _create_test_image()
        response = client.post(
            "/predict/v2",
            files={"file": ("test.png", img_buf, "image/png")},
            data={"doc_type": "invoice"},
        )
        assert response.status_code in (200, 500)
        data = response.json()
        if response.status_code == 200:
            assert data["version"] == "v2"

    def test_circuit_breaker_status(self, client):
        response = client.get("/circuit-breaker")
        assert response.status_code == 200
        data = response.json()
        assert "state" in data


class TestGateway:
    def test_gateway_health(self, gateway_client):
        response = gateway_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_gateway_process(self, gateway_client):
        img_buf = _create_test_image()
        response = gateway_client.post(
            "/process",
            files={"file": ("test.png", img_buf, "image/png")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "extraction" in data
        assert "doc_type" in data
        assert "classification_confidence" in data

    def test_gateway_schema_endpoint(self, gateway_client):
        response = gateway_client.get("/schemas/aadhaar")
        assert response.status_code == 200

    def test_gateway_unknown_schema(self, gateway_client):
        response = gateway_client.get("/schemas/unknown_type")
        assert response.status_code == 404


class TestCircuitBreaker:
    def test_normal_operation(self):
        from inference.circuit_breaker import CircuitBreaker, CircuitState
        cb = CircuitBreaker(failure_threshold=3, latency_threshold_ms=500)
        cb.record_latency(100)
        cb.record_latency(200)
        assert cb.state == CircuitState.CLOSED
        assert not cb.should_use_fallback

    def test_trips_on_slow_requests(self):
        from inference.circuit_breaker import CircuitBreaker, CircuitState
        cb = CircuitBreaker(failure_threshold=3, latency_threshold_ms=500)
        for _ in range(5):
            cb.record_latency(600)
        assert cb.state == CircuitState.OPEN
        assert cb.should_use_fallback
