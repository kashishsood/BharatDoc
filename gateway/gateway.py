"""
BharatDoc-VLM: API Gateway
============================

Central orchestration layer that receives all document processing requests,
classifies the document type, routes to the correct specialist model,
validates the output against the schema, and returns structured responses.

Architecture:
    Client → Gateway → Classifier → Router → Specialist Model → Schema Validation → Response

This is the single entry point for all document intelligence requests.
Internal services (classifier, specialist models) are never exposed directly.

Error handling philosophy:
    - Never return raw 500 errors
    - Always return structured error responses with actionable field-level details
    - Log errors with correlation IDs for debugging
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from pathlib import Path
from typing import Optional

import yaml
import httpx
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image
import io

# Local imports
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from router.classifier import get_classifier, ClassificationResult
from schemas.models import SchemaValidator

logger = logging.getLogger(__name__)

# =============================================================
# Configuration
# =============================================================

def load_routing_config(config_path: Optional[str] = None) -> dict:
    """Load routing configuration from YAML file."""
    if config_path is None:
        config_path = Path(__file__).resolve().parent.parent / "router" / "routing_config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


# =============================================================
# Mock specialist model (for testing without real inference server)
# =============================================================

class MockSpecialistRouter:
    """
    Simulates specialist model responses when real inference servers aren't running.
    
    Returns realistic extraction results per doc type so the full pipeline
    can be demonstrated end-to-end without GPUs or model weights.
    """

    # Realistic mock responses per doc type
    MOCK_RESPONSES = {
        "aadhaar": {
            "name": "Rajesh Kumar Sharma",
            "name_hindi": "राजेश कुमार शर्मा",
            "date_of_birth": "15/08/1990",
            "gender": "MALE",
            "aadhaar_number": "9234 5678 9012",
            "address": "H.No 45, Sector 12, Dwarka, New Delhi",
            "pincode": "110075",
            "photo_present": True,
            "vid": None,
            "issue_date": "01/03/2021",
        },
        "lic_policy": {
            "policy_number": "12345678",
            "holder_name": "Priya Nair",
            "plan_name": "Jeevan Anand",
            "plan_number": "815",
            "sum_assured": 1000000.0,
            "premium_amount": 25000.0,
            "premium_frequency": "YEARLY",
            "policy_term_years": 25,
            "premium_paying_term_years": 20,
            "commencement_date": "01/04/2020",
            "maturity_date": "01/04/2045",
            "nominee_name": "Arun Nair",
            "nominee_relationship": "SPOUSE",
            "branch_code": "MUM-042",
            "rider_benefits": [
                {"rider_name": "Accident Benefit Rider", "rider_sum_assured": 500000.0}
            ],
        },
        "invoice": {
            "invoice_number": "INV-2024-0042",
            "vendor_name": "Tata Consultancy Services Ltd",
            "vendor_gstin": "27AAACT2727Q1ZV",
            "buyer_name": "Infosys Limited",
            "buyer_gstin": "29AABCI1234F1ZE",
            "invoice_date": "15/01/2024",
            "due_date": "14/02/2024",
            "line_items": [
                {
                    "description": "Software Development Services",
                    "hsn_code": "998314",
                    "quantity": 160.0,
                    "unit_price": 5000.0,
                    "amount": 800000.0,
                },
                {
                    "description": "Cloud Infrastructure Support",
                    "hsn_code": "998315",
                    "quantity": 1.0,
                    "unit_price": 150000.0,
                    "amount": 150000.0,
                },
            ],
            "subtotal": 950000.0,
            "cgst_amount": None,
            "sgst_amount": None,
            "igst_amount": 171000.0,
            "total_tax": 171000.0,
            "total_amount": 1121000.0,
            "amount_in_words": "Eleven Lakh Twenty-One Thousand Rupees Only",
            "place_of_supply": "Karnataka",
            "payment_terms": "Net 30",
        },
        # Generic response for doc types without dedicated schemas
        "handwritten_form": {
            "raw_text": "Application for Transfer Certificate\nName: Ananya Gupta\nClass: XII-A\nRoll No: 42\nDate: 10/03/2024",
            "fields": {"name": "Ananya Gupta", "class": "XII-A", "roll_no": "42"},
            "confidence": 0.72,
        },
        "printed_form": {
            "raw_text": "Government of India\nMinistry of External Affairs\nPassport Application Form",
            "fields": {"form_type": "Passport Application", "ministry": "External Affairs"},
            "confidence": 0.88,
        },
        "table_doc": {
            "raw_text": "Quarterly Sales Report Q3 2024",
            "tables": [
                {
                    "headers": ["Product", "Q1", "Q2", "Q3"],
                    "rows": [
                        ["Widget A", "₹1,20,000", "₹1,35,000", "₹1,50,000"],
                        ["Widget B", "₹80,000", "₹95,000", "₹1,10,000"],
                    ],
                }
            ],
            "confidence": 0.85,
        },
    }

    async def route(self, doc_type: str, image_bytes: bytes) -> dict:
        """Return mock specialist model response."""
        # Simulate model inference latency
        await asyncio.sleep(0.1)
        response = self.MOCK_RESPONSES.get(doc_type, self.MOCK_RESPONSES["printed_form"])
        return response.copy()


class HTTPSpecialistRouter:
    """
    Routes requests to real specialist model endpoints via HTTP.
    
    Uses the routing_config.yaml to determine which endpoint to hit
    for each doc_type. Falls back to the fallback endpoint if the
    primary fails.
    """

    def __init__(self, routing_config: dict):
        self.config = routing_config.get("routing", {})
        self.settings = routing_config.get("settings", {})
        self.timeout = self.settings.get("request_timeout", 10)
        self.max_retries = self.settings.get("max_retries", 2)

    async def route(self, doc_type: str, image_bytes: bytes) -> dict:
        """Send image to the specialist model endpoint and return extraction."""
        route_config = self.config.get(doc_type)
        if not route_config:
            raise ValueError(f"No routing config for doc_type: {doc_type}")

        endpoints = [route_config["primary"], route_config.get("fallback")]
        endpoints = [e for e in endpoints if e]

        last_error = None
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for endpoint in endpoints:
                for attempt in range(self.max_retries):
                    try:
                        response = await client.post(
                            endpoint,
                            files={"file": ("document.png", image_bytes, "image/png")},
                            data={"doc_type": doc_type},
                        )
                        response.raise_for_status()
                        return response.json()
                    except Exception as e:
                        last_error = e
                        logger.warning(
                            f"Endpoint {endpoint} attempt {attempt + 1} failed: {e}"
                        )

        raise RuntimeError(f"All endpoints failed for {doc_type}: {last_error}")


# =============================================================
# FastAPI Application
# =============================================================

def create_app(use_mock: bool = True) -> FastAPI:
    """
    Create the gateway FastAPI application.
    
    Args:
        use_mock: Use mock classifier and router (no real models needed)
    """
    app = FastAPI(
        title="BharatDoc-VLM Gateway",
        description="Document intelligence gateway for Indian documents",
        version="1.0.0",
    )

    # CORS for Streamlit and web frontends
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialise components
    classifier = get_classifier(use_mock=use_mock)
    schema_validator = SchemaValidator()

    if use_mock:
        router = MockSpecialistRouter()
    else:
        routing_config = load_routing_config()
        router = HTTPSpecialistRouter(routing_config)

    @app.get("/health")
    async def health_check():
        """Health check endpoint for load balancers and monitoring."""
        return {
            "status": "healthy",
            "service": "bharatdoc-gateway",
            "mock_mode": use_mock,
            "supported_doc_types": schema_validator.supported_types,
        }

    @app.post("/process")
    async def process_document(
        file: UploadFile = File(..., description="Document image to process"),
        doc_type_override: Optional[str] = Query(
            None, description="Override auto-classification with explicit doc type"
        ),
    ):
        """
        Process a document image: classify → route → extract → validate → respond.
        
        Flow:
        1. Classify the document type (or use override)
        2. Route to specialist model endpoint
        3. Get extraction result
        4. Validate against schema (if schema exists for this doc type)
        5. Return structured response with metadata
        
        Returns structured errors with field-level details, never raw 500s.
        """
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        try:
            # Read uploaded image
            image_bytes = await file.read()
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            logger.info(f"[{request_id}] Processing document: {file.filename} ({image.size})")

            # Step 1: Classify document type
            if doc_type_override:
                classification = ClassificationResult(
                    doc_type=doc_type_override,
                    confidence=1.0,
                    all_scores={doc_type_override: 1.0},
                )
                logger.info(f"[{request_id}] Using override doc_type: {doc_type_override}")
            else:
                classification = classifier.classify(image)
                logger.info(
                    f"[{request_id}] Classified as {classification.doc_type} "
                    f"({classification.confidence:.2%})"
                )

            # Step 2: Route to specialist model
            extraction = await router.route(classification.doc_type, image_bytes)
            logger.info(
                f"[{request_id}] Extraction complete: "
                f"doc_type={classification.doc_type}, "
                f"fields={list(extraction.keys()) if isinstance(extraction, dict) else 'N/A'}, "
                f"confidence={extraction.get('confidence', 'N/A') if isinstance(extraction, dict) else 'N/A'}"
            )

            # Step 3: Validate against schema (if available)
            validation_result = None
            if classification.doc_type in schema_validator.supported_types:
                validation_result = schema_validator.validate(
                    classification.doc_type, extraction
                )
                if validation_result["valid"]:
                    extraction = validation_result["data"]
                    logger.info(f"[{request_id}] Schema validation PASSED")
                else:
                    logger.warning(
                        f"[{request_id}] Schema validation FAILED: "
                        f"{len(validation_result['errors'])} errors — "
                        f"{[e['field'] for e in validation_result['errors'][:5]]}"
                    )

            # Step 4: Build response
            total_latency = (time.time() - start_time) * 1000
            response = {
                "request_id": request_id,
                "status": "success",
                "doc_type": classification.doc_type,
                "classification_confidence": classification.confidence,
                "needs_human_review": classification.needs_review,
                "extraction": extraction,
                "schema_validation": {
                    "valid": validation_result["valid"] if validation_result else None,
                    "errors": validation_result["errors"] if validation_result else None,
                },
                "metadata": {
                    "filename": file.filename,
                    "image_size": list(image.size),
                    "total_latency_ms": round(total_latency, 2),
                    "classification_latency_ms": classification.latency_ms,
                    "all_classification_scores": classification.all_scores,
                },
            }

            return JSONResponse(content=response)

        except Exception as e:
            total_latency = (time.time() - start_time) * 1000
            logger.error(f"[{request_id}] Processing failed: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "request_id": request_id,
                    "status": "error",
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "metadata": {"total_latency_ms": round(total_latency, 2)},
                },
            )

    @app.get("/schemas/{doc_type}")
    async def get_schema(doc_type: str):
        """Return the JSON schema for a given document type."""
        try:
            schema = schema_validator.get_schema_json(doc_type)
            return JSONResponse(content=schema)
        except ValueError as e:
            return JSONResponse(
                status_code=404,
                content={"error": str(e), "supported_types": schema_validator.supported_types},
            )

    return app


# =============================================================
# Entrypoint
# =============================================================

app = create_app(use_mock=True)

if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="BharatDoc-VLM Gateway")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Server host")
    parser.add_argument("--mock", action="store_true", default=True, help="Use mock models")
    parser.add_argument("--no-mock", dest="mock", action="store_false", help="Use real models")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )

    app = create_app(use_mock=args.mock)
    uvicorn.run(app, host=args.host, port=args.port)
