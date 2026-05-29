"""
BharatDoc-VLM: Active Learning
=================================

Scores production images by model entropy. Ranks by uncertainty
descending for prioritised annotation. High-uncertainty samples
provide the most learning signal per annotation dollar.
"""

from __future__ import annotations

import logging
import math
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


def compute_entropy(probabilities: list[float]) -> float:
    """Compute Shannon entropy of a probability distribution."""
    entropy = 0.0
    for p in probabilities:
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy


def score_by_uncertainty(predictions: list[dict]) -> list[dict]:
    """
    Score predictions by model uncertainty (entropy).
    
    Higher entropy = less certain = more valuable for annotation.
    
    Each prediction dict should have:
    - 'confidence': overall confidence score
    - 'all_scores': dict of class → probability (optional)
    """
    scored = []
    for pred in predictions:
        if "all_scores" in pred and pred["all_scores"]:
            probs = list(pred["all_scores"].values())
            entropy = compute_entropy(probs)
        else:
            # Estimate entropy from single confidence value
            conf = pred.get("confidence", 0.5)
            probs = [conf, 1.0 - conf]
            entropy = compute_entropy(probs)

        scored.append({
            **pred,
            "uncertainty_score": round(entropy, 4),
            "priority": "high" if entropy > 1.0 else "medium" if entropy > 0.5 else "low",
        })

    # Sort by uncertainty (highest first)
    scored.sort(key=lambda x: -x["uncertainty_score"])
    return scored


def select_for_annotation(predictions: list[dict], budget: int = 50) -> list[dict]:
    """Select top-k most uncertain samples within annotation budget."""
    scored = score_by_uncertainty(predictions)
    selected = scored[:budget]
    logger.info(f"Selected {len(selected)}/{len(predictions)} samples for annotation "
                f"(entropy range: {selected[0]['uncertainty_score']:.3f} - "
                f"{selected[-1]['uncertainty_score']:.3f})")
    return selected


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    preds = [
        {"id": "doc_001", "confidence": 0.95, "doc_type": "aadhaar"},
        {"id": "doc_002", "confidence": 0.52, "doc_type": "invoice"},
        {"id": "doc_003", "confidence": 0.71, "doc_type": "lic_policy"},
        {"id": "doc_004", "confidence": 0.30, "doc_type": "aadhaar"},
        {"id": "doc_005", "confidence": 0.88, "doc_type": "invoice"},
    ]
    selected = select_for_annotation(preds, budget=3)
    for s in selected:
        print(f"  {s['id']}: uncertainty={s['uncertainty_score']:.3f} ({s['priority']})")
