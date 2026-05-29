"""
BharatDoc-VLM: Regression Tracker
====================================

Compares current run metrics to last passing run. Prints a regression
report showing which metrics improved/degraded. Essential for CI/CD.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def load_baseline_metrics(path: str = "evaluation/last_run_metrics.json") -> Optional[dict]:
    """Load metrics from the last passing run."""
    p = Path(path)
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    logger.warning(f"No baseline metrics found at {path}")
    return None


def save_metrics(metrics: dict, path: str = "evaluation/last_run_metrics.json"):
    """Save current run metrics for future comparison."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)


def compare_runs(current: dict, baseline: dict, 
                 regression_threshold: float = 0.02) -> dict:
    """
    Compare current run to baseline.
    
    A metric has regressed if it dropped by more than regression_threshold.
    """
    report = {"improved": [], "degraded": [], "stable": [], "new": []}

    all_keys = set(list(current.keys()) + list(baseline.keys()))
    for key in sorted(all_keys):
        curr_val = current.get(key)
        base_val = baseline.get(key)

        if curr_val is None or not isinstance(curr_val, (int, float)):
            continue
        if base_val is None or not isinstance(base_val, (int, float)):
            report["new"].append({"metric": key, "current": curr_val})
            continue

        diff = curr_val - base_val
        pct = diff / abs(base_val) if base_val != 0 else 0

        entry = {"metric": key, "current": round(curr_val, 4),
                 "baseline": round(base_val, 4), "diff": round(diff, 4),
                 "pct_change": round(pct * 100, 2)}

        if diff > regression_threshold:
            report["improved"].append(entry)
        elif diff < -regression_threshold:
            report["degraded"].append(entry)
        else:
            report["stable"].append(entry)

    report["has_regression"] = len(report["degraded"]) > 0
    return report


def print_regression_report(report: dict):
    """Print regression analysis report."""
    print(f"\n{'='*65}")
    print("REGRESSION REPORT")
    print(f"{'='*65}")
    
    if report["improved"]:
        print(f"\n✅ IMPROVED ({len(report['improved'])} metrics):")
        for m in report["improved"]:
            print(f"  {m['metric']:<25} {m['baseline']:.4f} → {m['current']:.4f} ({m['pct_change']:+.1f}%)")
    
    if report["degraded"]:
        print(f"\n🚨 DEGRADED ({len(report['degraded'])} metrics):")
        for m in report["degraded"]:
            print(f"  {m['metric']:<25} {m['baseline']:.4f} → {m['current']:.4f} ({m['pct_change']:+.1f}%)")
    
    if report["stable"]:
        print(f"\n➡️  STABLE ({len(report['stable'])} metrics)")
    
    status = "🚨 REGRESSION DETECTED" if report["has_regression"] else "✅ NO REGRESSIONS"
    print(f"\n{'='*65}")
    print(f"Status: {status}")
    print(f"{'='*65}")


if __name__ == "__main__":
    baseline = {"mean_f1": 0.85, "doc_accuracy": 0.72, "ece": 0.08}
    current = {"mean_f1": 0.88, "doc_accuracy": 0.70, "ece": 0.06, "latency_p95": 450}
    report = compare_runs(current, baseline)
    print_regression_report(report)
