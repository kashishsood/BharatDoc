"""
BharatDoc-VLM: Document-Level Evaluation
==========================================

A document is "correct" only if ALL required fields match ground truth.
This strict accuracy metric reflects real-world requirements where
partial extractions are not useful (e.g., an Aadhaar card with wrong
number is as bad as no extraction at all).
"""

from __future__ import annotations

import logging
from typing import Optional

from evaluation.field_level_eval import normalize_field

logger = logging.getLogger(__name__)


def compute_document_accuracy(predictions: list[dict], ground_truths: list[dict],
                               required_fields: Optional[list[str]] = None) -> dict:
    """
    Compute strict document-level accuracy.
    
    A document passes only if EVERY required field matches exactly.
    """
    total = len(predictions)
    correct = 0
    failures = []

    for i, (pred, gt) in enumerate(zip(predictions, ground_truths)):
        # Determine required fields
        fields = required_fields or [k for k in gt.keys()
                                      if k not in ("doc_type", "confidence", "stage", "corrections_applied")]
        all_match = True
        failed_fields = []

        for field in fields:
            pred_val = normalize_field(pred.get(field))
            gt_val = normalize_field(gt.get(field))
            if gt_val and pred_val != gt_val:
                all_match = False
                failed_fields.append({"field": field, "predicted": pred.get(field), "expected": gt.get(field)})

        if all_match:
            correct += 1
        else:
            failures.append({"doc_index": i, "failed_fields": failed_fields})

    accuracy = correct / total if total > 0 else 0.0
    return {
        "document_accuracy": round(accuracy, 4),
        "correct": correct,
        "total": total,
        "num_failures": len(failures),
        "failures": failures[:20],  # Cap for readability
    }


def print_document_report(results: dict):
    """Print document-level accuracy report."""
    print(f"\n{'='*50}")
    print(f"Document-Level Accuracy: {results['document_accuracy']:.2%}")
    print(f"  Correct: {results['correct']} / {results['total']}")
    print(f"  Failures: {results['num_failures']}")
    if results["failures"]:
        print(f"\nSample failures:")
        for f in results["failures"][:5]:
            print(f"  Doc {f['doc_index']}:")
            for ff in f["failed_fields"]:
                print(f"    {ff['field']}: predicted='{ff['predicted']}' expected='{ff['expected']}'")
    print(f"{'='*50}")


if __name__ == "__main__":
    preds = [
        {"name": "Rajesh Kumar", "dob": "15/08/1990", "aadhaar": "9234 5678 9012"},
        {"name": "Priya Sharma", "dob": "22/03/1986", "aadhaar": "4567 8901 2345"},
    ]
    gts = [
        {"name": "Rajesh Kumar", "dob": "15/08/1990", "aadhaar": "9234 5678 9012"},
        {"name": "Priya Sharma", "dob": "22/03/1985", "aadhaar": "4567 8901 2345"},
    ]
    results = compute_document_accuracy(preds, gts)
    print_document_report(results)
