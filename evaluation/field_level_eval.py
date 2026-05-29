"""
BharatDoc-VLM: Field-Level Evaluation
=======================================

Computes F1 separately for each schema field (name, date, amount, etc.).
Reports mean and per-field breakdown. This is the primary evaluation metric
because document extraction quality varies significantly across field types.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import Optional

logger = logging.getLogger(__name__)


def normalize_field(value) -> str:
    """Normalize field value for comparison (lowercase, strip whitespace)."""
    if value is None:
        return ""
    return str(value).strip().lower()


def compute_field_f1(predictions: list[dict], ground_truths: list[dict],
                     fields: Optional[list[str]] = None) -> dict:
    """
    Compute per-field F1 score across all documents.
    
    For each field:
    - TP: predicted value matches ground truth
    - FP: predicted a value but it's wrong or GT is empty
    - FN: GT has a value but prediction is empty/wrong
    
    String matching uses normalized exact match. For production,
    consider fuzzy matching for names (Levenshtein distance < 2).
    """
    field_stats = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    
    # Discover all fields if not specified
    if fields is None:
        all_fields = set()
        for gt in ground_truths:
            all_fields.update(gt.keys())
        fields = sorted(all_fields - {"doc_type", "confidence", "stage", "corrections_applied"})

    for pred, gt in zip(predictions, ground_truths):
        for field in fields:
            pred_val = normalize_field(pred.get(field))
            gt_val = normalize_field(gt.get(field))

            if gt_val and pred_val:
                if pred_val == gt_val:
                    field_stats[field]["tp"] += 1
                else:
                    field_stats[field]["fp"] += 1
                    field_stats[field]["fn"] += 1
            elif gt_val and not pred_val:
                field_stats[field]["fn"] += 1
            elif pred_val and not gt_val:
                field_stats[field]["fp"] += 1

    # Compute F1 per field
    results = {}
    for field in fields:
        stats = field_stats[field]
        tp, fp, fn = stats["tp"], stats["fp"], stats["fn"]
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        results[field] = {
            "f1": round(f1, 4), "precision": round(precision, 4),
            "recall": round(recall, 4), "tp": tp, "fp": fp, "fn": fn,
        }

    # Compute mean F1
    f1_scores = [r["f1"] for r in results.values() if r["tp"] + r["fp"] + r["fn"] > 0]
    mean_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0.0
    results["_mean"] = {"f1": round(mean_f1, 4)}

    return results


def print_field_report(results: dict):
    """Pretty-print field-level evaluation report."""
    print(f"\n{'='*70}")
    print(f"{'Field':<25} {'F1':>8} {'Prec':>8} {'Recall':>8} {'TP':>5} {'FP':>5} {'FN':>5}")
    print(f"{'='*70}")
    for field, stats in sorted(results.items()):
        if field == "_mean":
            continue
        print(f"{field:<25} {stats['f1']:>8.4f} {stats['precision']:>8.4f} "
              f"{stats['recall']:>8.4f} {stats['tp']:>5} {stats['fp']:>5} {stats['fn']:>5}")
    print(f"{'='*70}")
    print(f"{'Mean F1':<25} {results['_mean']['f1']:>8.4f}")
    print(f"{'='*70}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Demo with mock data
    preds = [
        {"name": "Rajesh Kumar", "date_of_birth": "15/08/1990", "aadhaar_number": "9234 5678 9012"},
        {"name": "Priya Sharma", "date_of_birth": "22/03/1986", "aadhaar_number": "4567 8901 2345"},
    ]
    gts = [
        {"name": "Rajesh Kumar", "date_of_birth": "15/08/1990", "aadhaar_number": "9234 5678 9012"},
        {"name": "Priya Sharma", "date_of_birth": "22/03/1985", "aadhaar_number": "4567 8901 2345"},
    ]
    results = compute_field_f1(preds, gts)
    print_field_report(results)
