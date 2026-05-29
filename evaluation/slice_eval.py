"""
BharatDoc-VLM: Slice-Based Evaluation
=======================================

Reports metrics sliced by: language (hindi/english/mixed),
scan_quality (clean/noisy), and doc_type.

Why slicing matters: aggregate metrics hide critical failure modes.
A model might have 90% overall F1 but 40% on Hindi-only documents.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Optional

from evaluation.field_level_eval import compute_field_f1
from evaluation.document_level_eval import compute_document_accuracy

logger = logging.getLogger(__name__)


def compute_slice_metrics(predictions: list[dict], ground_truths: list[dict],
                          metadata: list[dict]) -> dict:
    """
    Compute metrics sliced by language, scan_quality, and doc_type.
    
    Args:
        predictions: list of prediction dicts
        ground_truths: list of ground truth dicts
        metadata: list of metadata dicts with keys: language, scan_quality, doc_type
    """
    slices = defaultdict(lambda: {"preds": [], "gts": []})

    for pred, gt, meta in zip(predictions, ground_truths, metadata):
        lang = meta.get("language", "unknown")
        quality = meta.get("scan_quality", "unknown")
        doc_type = meta.get("doc_type", "unknown")

        slices[f"lang/{lang}"]["preds"].append(pred)
        slices[f"lang/{lang}"]["gts"].append(gt)
        slices[f"quality/{quality}"]["preds"].append(pred)
        slices[f"quality/{quality}"]["gts"].append(gt)
        slices[f"doc_type/{doc_type}"]["preds"].append(pred)
        slices[f"doc_type/{doc_type}"]["gts"].append(gt)

    results = {}
    for slice_name, data in slices.items():
        field_results = compute_field_f1(data["preds"], data["gts"])
        doc_results = compute_document_accuracy(data["preds"], data["gts"])
        results[slice_name] = {
            "count": len(data["preds"]),
            "mean_f1": field_results["_mean"]["f1"],
            "document_accuracy": doc_results["document_accuracy"],
        }

    return results


def print_slice_report(results: dict):
    """Print slice evaluation report."""
    print(f"\n{'='*65}")
    print(f"{'Slice':<30} {'Count':>6} {'Mean F1':>10} {'Doc Acc':>10}")
    print(f"{'='*65}")
    for slice_name in sorted(results.keys()):
        r = results[slice_name]
        print(f"{slice_name:<30} {r['count']:>6} {r['mean_f1']:>10.4f} {r['document_accuracy']:>10.4f}")
    print(f"{'='*65}")


if __name__ == "__main__":
    preds = [{"name": "Rajesh"}, {"name": "Priya"}, {"name": "Amit"}]
    gts = [{"name": "Rajesh"}, {"name": "Priya"}, {"name": "Amit Patel"}]
    meta = [
        {"language": "english", "scan_quality": "clean", "doc_type": "aadhaar"},
        {"language": "hindi", "scan_quality": "noisy", "doc_type": "aadhaar"},
        {"language": "mixed", "scan_quality": "clean", "doc_type": "invoice"},
    ]
    results = compute_slice_metrics(preds, gts, meta)
    print_slice_report(results)
