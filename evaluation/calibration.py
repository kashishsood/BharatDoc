"""
BharatDoc-VLM: Model Calibration Analysis
============================================

Plots reliability diagram and computes Expected Calibration Error (ECE).
Flags predictions with confidence < 0.6 as "needs human review".
"""

from __future__ import annotations

import logging
import numpy as np

logger = logging.getLogger(__name__)


def compute_ece(confidences: list[float], accuracies: list[bool],
                n_bins: int = 10) -> dict:
    """
    Compute Expected Calibration Error.
    
    ECE measures how well model confidence aligns with actual accuracy.
    A well-calibrated model with 80% confidence should be correct 80% of the time.
    """
    conf_arr = np.array(confidences)
    acc_arr = np.array(accuracies, dtype=float)
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    
    bin_data = []
    ece = 0.0
    
    for i in range(n_bins):
        lo, hi = bin_boundaries[i], bin_boundaries[i + 1]
        mask = (conf_arr >= lo) & (conf_arr < hi)
        if hi == 1.0:
            mask = mask | (conf_arr == 1.0)
        
        count = mask.sum()
        if count > 0:
            avg_conf = conf_arr[mask].mean()
            avg_acc = acc_arr[mask].mean()
            ece += (count / len(conf_arr)) * abs(avg_acc - avg_conf)
            bin_data.append({
                "bin": f"{lo:.1f}-{hi:.1f}", "count": int(count),
                "avg_confidence": round(float(avg_conf), 4),
                "avg_accuracy": round(float(avg_acc), 4),
                "gap": round(float(abs(avg_acc - avg_conf)), 4),
            })
        else:
            bin_data.append({"bin": f"{lo:.1f}-{hi:.1f}", "count": 0})

    needs_review = sum(1 for c in confidences if c < 0.6)
    
    return {
        "ece": round(float(ece), 4),
        "n_samples": len(confidences),
        "bins": bin_data,
        "needs_human_review": needs_review,
        "review_percentage": round(100 * needs_review / max(len(confidences), 1), 1),
    }


def print_calibration_report(results: dict):
    """Print calibration analysis report."""
    print(f"\n{'='*60}")
    print(f"Expected Calibration Error (ECE): {results['ece']:.4f}")
    print(f"Samples needing review: {results['needs_human_review']}/{results['n_samples']} ({results['review_percentage']}%)")
    print(f"\n{'Bin':<12} {'Count':>6} {'Avg Conf':>10} {'Avg Acc':>10} {'Gap':>8}")
    print(f"{'-'*50}")
    for b in results["bins"]:
        if b["count"] > 0:
            print(f"{b['bin']:<12} {b['count']:>6} {b['avg_confidence']:>10.4f} {b['avg_accuracy']:>10.4f} {b['gap']:>8.4f}")
    print(f"{'='*60}")


if __name__ == "__main__":
    np.random.seed(42)
    confs = np.random.uniform(0.3, 0.99, 100).tolist()
    accs = [np.random.random() < c for c in confs]
    results = compute_ece(confs, accs)
    print_calibration_report(results)
