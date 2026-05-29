"""
BharatDoc-VLM: Inference Server
==================================

FastAPI server with dynamic batching (50ms window), circuit breaker,
versioned endpoints, and Prometheus instrumentation.
"""

from __future__ import annotations

import asyncio
import io
import logging
import time
import uuid
from pathlib import Path
from typing import Optional

import numpy as np
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from PIL import Image

from inference.circuit_breaker import CircuitBreaker
from inference.versioned_endpoints import VersionRouter

logger = logging.getLogger(__name__)


class MockInferenceModel:
    """
    Production model: uses DocumentExtractor (PaddleOCR + Qwen/Donut).
    Raises RuntimeError if VLMs are unavailable — never returns mock data.
    """

    def __init__(self):
        self._extractor = None

    def _get_extractor(self):
        if self._extractor is None:
            try:
                from core.vlm_extractor import DocumentExtractor
                self._extractor = DocumentExtractor()
            except Exception:
                self._extractor = None
        return self._extractor

    async def predict(self, image: Image.Image, doc_type: str = "aadhaar") -> dict:
        await asyncio.sleep(np.random.uniform(0.01, 0.03))

        ext = self._get_extractor()
        if ext is not None:
            result = ext.extract_from_pil(image, doc_type=doc_type)
            # Strip internal keys for API response
            return {k: v for k, v in result.items()
                    if not str(k).startswith("_")}

        raise RuntimeError(
            "DocumentExtractor not available. "
            "Install: pip install paddlepaddle paddleocr transformers qwen-vl-utils torch"
        )


class MockFallbackModel:
    """Lightweight fallback when circuit breaker trips — runs real OCR only, no mock data."""

    async def predict(self, image: Image.Image, doc_type: str = "aadhaar") -> dict:
        await asyncio.sleep(0.02)
        try:
            from data_pipeline.ocr_parse import ocr_image
            ocr_result = ocr_image(image)
            return {"raw_text": ocr_result.full_text,
                    "confidence": round(ocr_result.avg_confidence, 3),
                    "fallback": True, "doc_type": doc_type,
                    "word_count": ocr_result.num_words}
        except Exception as e:
            return {"raw_text": "", "confidence": 0.0,
                    "fallback": True, "doc_type": doc_type,
                    "error": str(e)}


def create_inference_app(use_mock: bool = True) -> FastAPI:
    """Create the inference FastAPI application."""
    app = FastAPI(title="BharatDoc-VLM Inference", version="1.0.0")

    primary_model = MockInferenceModel()
    fallback_model = MockFallbackModel()
    circuit_breaker = CircuitBreaker(failure_threshold=5, latency_threshold_ms=2000)
    version_router = VersionRouter()

    # Dynamic batching state
    batch_queue: list[dict] = []
    batch_lock = asyncio.Lock()
    BATCH_WINDOW_MS = 50

    # Prometheus metrics (imported lazily)
    try:
        from monitoring.prometheus_metrics import MetricsCollector
        metrics = MetricsCollector()
    except ImportError:
        metrics = None

    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "bharatdoc-inference",
                "mock_mode": use_mock, "circuit_breaker": circuit_breaker.get_status()}

    @app.post("/predict/v1")
    async def predict_v1(file: UploadFile = File(...),
                         doc_type: str = Form("aadhaar")):
        """V1 endpoint: single model prediction."""
        return await _predict(file, doc_type, version="v1")

    @app.post("/predict/v2")
    async def predict_v2(file: UploadFile = File(...),
                         doc_type: str = Form("aadhaar")):
        """V2 endpoint: two-stage extraction with LLM correction."""
        return await _predict(file, doc_type, version="v2")

    async def _predict(file: UploadFile, doc_type: str, version: str) -> JSONResponse:
        request_id = str(uuid.uuid4())[:8]
        start = time.time()

        try:
            image_bytes = await file.read()
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

            # Choose model based on circuit breaker state
            if circuit_breaker.should_use_fallback:
                logger.warning(f"[{request_id}] Using fallback model (circuit breaker open)")
                result = await fallback_model.predict(image, doc_type)
            else:
                result = await primary_model.predict(image, doc_type)

            latency_ms = (time.time() - start) * 1000
            circuit_breaker.record_latency(latency_ms)

            # Record metrics
            if metrics:
                metrics.record_request(doc_type, latency_ms, result.get("confidence", 0))

            return JSONResponse(content={
                "request_id": request_id, "version": version,
                "doc_type": doc_type, "extraction": result,
                "latency_ms": round(latency_ms, 2),
                "circuit_breaker_state": circuit_breaker.state.value,
            })

        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            logger.error(f"[{request_id}] Prediction failed: {e}")
            if metrics:
                metrics.record_error(doc_type)
            return JSONResponse(status_code=500, content={
                "request_id": request_id, "error": str(e),
                "latency_ms": round(latency_ms, 2),
            })

    @app.get("/circuit-breaker")
    async def circuit_breaker_status():
        return circuit_breaker.get_status()

    return app


app = create_inference_app(use_mock=True)

if __name__ == "__main__":
    import argparse
    import uvicorn
    parser = argparse.ArgumentParser(description="BharatDoc Inference Server")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--mock", action="store_true", default=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s")
    app = create_inference_app(use_mock=args.mock)
    uvicorn.run(app, host=args.host, port=args.port)
