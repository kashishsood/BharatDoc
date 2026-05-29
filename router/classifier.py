"""
BharatDoc-VLM: Document Type Classifier
========================================

Classifies input document images into one of the supported document types,
enabling the gateway to route to the correct specialist model.

Architecture decision:
- Uses CLIP embeddings for zero-shot classification in production mode.
  CLIP is preferred over a trained CNN classifier because:
  1. It generalises to unseen document layouts without retraining
  2. New doc types can be added by updating label prompts, not retraining
  3. Embedding similarity gives a natural confidence score
- Falls back to MockClassifier when real models aren't available,
  returning realistic confidence distributions for testing.

Supported doc types:
  aadhaar, invoice, lic_policy, handwritten_form, printed_form, table_doc
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Document types supported by the routing system
DOC_TYPES = [
    "aadhaar",
    "invoice",
    "lic_policy",
    "handwritten_form",
    "printed_form",
    "table_doc",
]

# CLIP text prompts per doc type — these are the "class labels" for zero-shot classification
# Prompt engineering matters here: specific descriptions outperform generic labels
CLIP_PROMPTS = {
    "aadhaar": "a photograph of an Indian Aadhaar identity card with a 12-digit number and personal details",
    "invoice": "a photograph of a commercial invoice or GST bill with line items and amounts",
    "lic_policy": "a photograph of a Life Insurance Corporation of India policy document",
    "handwritten_form": "a photograph of a handwritten form or application with cursive writing",
    "printed_form": "a photograph of a printed government or official form with typed text and fields",
    "table_doc": "a photograph of a document containing dense data tables with rows and columns",
}


@dataclass
class ClassificationResult:
    """Result of document classification."""
    doc_type: str
    confidence: float
    all_scores: dict[str, float] = field(default_factory=dict)
    latency_ms: float = 0.0

    @property
    def needs_review(self) -> bool:
        """Flag if confidence is too low for automatic routing."""
        return self.confidence < 0.6


class MockClassifier:
    """
    Mock classifier for testing without real model weights.
    
    Returns realistic confidence distributions:
    - Primary class gets 0.65-0.95 confidence
    - Runner-up gets 0.05-0.20
    - Others get small residual scores
    This mimics real CLIP behaviour where related doc types get partial scores.
    """

    def __init__(self, default_type: Optional[str] = None):
        self.default_type = default_type
        logger.info("Initialized MockClassifier (no real model loaded)")

    def classify(self, image: Image.Image) -> ClassificationResult:
        """Return mock classification with realistic confidence distribution."""
        start = time.time()

        # Determine the "detected" type
        if self.default_type and self.default_type in DOC_TYPES:
            primary = self.default_type
        else:
            # Use image properties to semi-deterministically pick a type
            # (so the same image gives the same result — useful for testing)
            w, h = image.size
            idx = (w * h) % len(DOC_TYPES)
            primary = DOC_TYPES[idx]

        # Generate realistic confidence distribution
        primary_conf = random.uniform(0.65, 0.95)
        remaining = 1.0 - primary_conf
        other_types = [t for t in DOC_TYPES if t != primary]
        # Distribute remaining confidence with some randomness
        raw_scores = [random.random() for _ in other_types]
        score_sum = sum(raw_scores)
        other_confs = [remaining * (s / score_sum) for s in raw_scores]

        all_scores = {primary: round(primary_conf, 4)}
        for t, c in zip(other_types, other_confs):
            all_scores[t] = round(c, 4)

        latency = (time.time() - start) * 1000

        result = ClassificationResult(
            doc_type=primary,
            confidence=round(primary_conf, 4),
            all_scores=all_scores,
            latency_ms=round(latency, 2),
        )
        logger.info(f"Mock classification: {primary} ({primary_conf:.2%})")
        return result


class CLIPClassifier:
    """
    CLIP-based zero-shot document classifier.
    
    Uses OpenAI CLIP (or open-source alternatives like open_clip) to compute
    similarity between the input image and text prompts describing each doc type.
    
    Why CLIP over a trained classifier:
    - No labelled training data needed for new doc types
    - Works across visual styles (scan, photo, screenshot)
    - Confidence scores are naturally calibrated via softmax over similarities
    """

    def __init__(self, model_name: str = "openai/clip-vit-base-patch32", device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        self.model = None
        self.processor = None
        self._load_model()

    def _load_model(self):
        """Load CLIP model and processor from HuggingFace."""
        try:
            from transformers import CLIPModel, CLIPProcessor
            logger.info(f"Loading CLIP model: {self.model_name}")
            self.processor = CLIPProcessor.from_pretrained(self.model_name)
            self.model = CLIPModel.from_pretrained(self.model_name).to(self.device)
            self.model.eval()
            logger.info(f"CLIP model loaded on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load CLIP model: {e}")
            raise

    def classify(self, image: Image.Image) -> ClassificationResult:
        """
        Classify document image using CLIP zero-shot similarity.
        
        Process:
        1. Encode image with CLIP vision encoder
        2. Encode all doc type prompts with CLIP text encoder
        3. Compute cosine similarity between image and each prompt
        4. Softmax over similarities → confidence scores
        5. Return highest-scoring doc type
        """
        import torch

        start = time.time()

        # Prepare inputs
        prompts = [CLIP_PROMPTS[dt] for dt in DOC_TYPES]
        inputs = self.processor(
            text=prompts,
            images=image,
            return_tensors="pt",
            padding=True,
        ).to(self.device)

        # Forward pass
        with torch.no_grad():
            outputs = self.model(**inputs)
            # logits_per_image shape: [1, num_doc_types]
            logits = outputs.logits_per_image[0]
            # Temperature-scaled softmax for calibrated probabilities
            probs = torch.softmax(logits / 0.5, dim=0).cpu().numpy()

        # Build result
        all_scores = {dt: round(float(p), 4) for dt, p in zip(DOC_TYPES, probs)}
        best_idx = int(np.argmax(probs))
        best_type = DOC_TYPES[best_idx]
        best_conf = float(probs[best_idx])

        latency = (time.time() - start) * 1000

        result = ClassificationResult(
            doc_type=best_type,
            confidence=round(best_conf, 4),
            all_scores=all_scores,
            latency_ms=round(latency, 2),
        )
        logger.info(f"CLIP classification: {best_type} ({best_conf:.2%}) in {latency:.0f}ms")
        return result


def get_classifier(use_mock: bool = True, **kwargs) -> MockClassifier | CLIPClassifier:
    """
    Factory function for document classifier.
    
    Args:
        use_mock: If True, returns MockClassifier (no GPU/model needed).
                  If False, loads real CLIP model.
        **kwargs: Passed to the classifier constructor.
    
    Returns:
        Classifier instance with a .classify(image) method.
    """
    if use_mock:
        return MockClassifier(**kwargs)
    return CLIPClassifier(**kwargs)


# =============================================================
# CLI for standalone testing
# =============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Classify a document image")
    parser.add_argument("--image", type=str, help="Path to document image")
    parser.add_argument("--mock", action="store_true", default=True, help="Use mock classifier")
    parser.add_argument("--model", type=str, default="openai/clip-vit-base-patch32")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    classifier = get_classifier(use_mock=args.mock, model_name=args.model)

    if args.image:
        img = Image.open(args.image).convert("RGB")
    else:
        # Create a dummy image for testing
        img = Image.new("RGB", (800, 600), color=(255, 255, 255))
        logger.info("No image provided, using dummy white image")

    result = classifier.classify(img)
    print(f"\n{'='*50}")
    print(f"Document Type:  {result.doc_type}")
    print(f"Confidence:     {result.confidence:.2%}")
    print(f"Needs Review:   {result.needs_review}")
    print(f"Latency:        {result.latency_ms:.1f}ms")
    print(f"\nAll Scores:")
    for dt, score in sorted(result.all_scores.items(), key=lambda x: -x[1]):
        bar = "█" * int(score * 40)
        print(f"  {dt:20s} {score:.4f} {bar}")
