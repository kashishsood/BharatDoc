"""
BharatDoc-VLM: Two-Stage Extraction Pipeline
===============================================

Stage 1: OCR + layout model → structured JSON
Stage 2: Small LLM (phi-2 / llama-3.2-1b) corrects errors using context

Why two stages:
- Stage 1 is fast but makes OCR errors (e.g., '0' vs 'O', date format issues)
- Stage 2 uses language understanding to fix errors that pure OCR cannot
- This mimics production systems where a fast model + slow corrector is cheaper
  than running a large VLM on every request
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import yaml
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class Stage1OCRExtractor:
    """Stage 1: Extract structured JSON from document image using OCR + layout model."""

    def __init__(self, config: dict):
        self.config = config
        self.model_name = config["models"][config["two_stage"]["stage1_model"]]["name"]
        logger.info(f"Stage 1 extractor: {self.model_name}")

    def extract(self, image: Image.Image, doc_type: str = "aadhaar") -> dict:
        """Extract fields from image (mock: returns extraction with intentional OCR errors)."""
        # Simulate OCR errors that Stage 2 should fix
        mock_extractions = {
            "aadhaar": {
                "name": "Rajesh Kumar Sharrna",  # OCR error: 'm' → 'rn'
                "date_of_birth": "I5/O8/199O",  # OCR errors: '1'→'I', '0'→'O'
                "gender": "MALE",
                "aadhaar_number": "9234 5678 9O12",  # '0'→'O'
                "address": "H.No 45, Sector l2, Dwarka",  # 'l' vs '1'
                "confidence": 0.72,
                "stage": "ocr_raw",
            },
            "invoice": {
                "invoice_number": "INV-2O24-OO42",
                "vendor_name": "TCS Lirnited",
                "total_amount": "1,l2l,OOO",  # Mixed up chars
                "confidence": 0.68,
                "stage": "ocr_raw",
            },
        }
        return mock_extractions.get(doc_type, mock_extractions["aadhaar"])


class Stage2LLMCorrector:
    """Stage 2: LLM-based error correction using context understanding."""

    def __init__(self, config: dict):
        self.config = config
        self.model_name = config["models"]["corrector_llm"]["name"]
        logger.info(f"Stage 2 corrector: {self.model_name}")

    def correct(self, ocr_output: dict, doc_type: str = "aadhaar") -> dict:
        """
        Correct OCR errors using LLM context understanding.
        
        The LLM prompt includes:
        - The raw OCR output
        - The expected schema for this doc type
        - Instructions to fix common OCR errors
        """
        corrected = ocr_output.copy()

        # Simulate LLM corrections
        for key, value in corrected.items():
            if isinstance(value, str):
                # Fix common OCR substitutions
                value = value.replace("rn", "m")  # 'rn' → 'm'
                value = value.replace("I5", "15").replace("O8", "08")
                value = value.replace("199O", "1990").replace("9O12", "9012")
                value = value.replace("l2", "12").replace("l1", "11")
                value = value.replace("2O24", "2024").replace("OO", "00")
                value = value.replace("Lirnited", "Limited")
                value = value.replace("1,l2l,OOO", "1,121,000")
                corrected[key] = value

        corrected["confidence"] = min(0.95, ocr_output.get("confidence", 0.7) + 0.15)
        corrected["stage"] = "llm_corrected"
        corrected["corrections_applied"] = True

        logger.info(f"Stage 2 corrections applied (confidence: {ocr_output.get('confidence', 0):.2f} → {corrected['confidence']:.2f})")
        return corrected


class TwoStagePipeline:
    """Full two-stage extraction pipeline: OCR → LLM correction."""

    def __init__(self, config_path: str = "training/config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        
        self.stage1 = Stage1OCRExtractor(self.config)
        self.stage2 = Stage2LLMCorrector(self.config)
        self.use_stage2 = self.config["two_stage"]["use_stage2"]

    def extract(self, image: Image.Image, doc_type: str = "aadhaar") -> dict:
        """Run full two-stage extraction."""
        # Stage 1: OCR extraction
        ocr_result = self.stage1.extract(image, doc_type)
        logger.info(f"Stage 1 output: {list(ocr_result.keys())}")

        if not self.use_stage2:
            return ocr_result

        # Stage 2: LLM correction
        corrected = self.stage2.correct(ocr_result, doc_type)
        logger.info(f"Stage 2 output: confidence {corrected.get('confidence', 0):.2f}")

        return corrected


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    pipeline = TwoStagePipeline()
    img = Image.new("RGB", (800, 600), (255, 255, 255))
    
    print("\n--- Aadhaar Extraction ---")
    result = pipeline.extract(img, "aadhaar")
    print(json.dumps(result, indent=2))
    
    print("\n--- Invoice Extraction ---")
    result = pipeline.extract(img, "invoice")
    print(json.dumps(result, indent=2))
