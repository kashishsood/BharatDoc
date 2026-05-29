"""
BharatDoc-VLM: Failure Analyzer
=================================

Clusters failures by doc_type + noise level to identify systematic patterns.
"""

from __future__ import annotations

import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


def analyze_failures(failures: list[dict], metadata: list[dict]) -> dict:
    """
    Cluster failures by doc_type and scan_quality.
    
    Args:
        failures: list of failure dicts with failed_fields
        metadata: matching metadata with doc_type, scan_quality, language
    """
    clusters = defaultdict(lambda: {"count": 0, "failed_fields": defaultdict(int), "samples": []})

    for failure, meta in zip(failures, metadata):
        doc_type = meta.get("doc_type", "unknown")
        quality = meta.get("scan_quality", "unknown")
        key = f"{doc_type}/{quality}"

        clusters[key]["count"] += 1
        for ff in failure.get("failed_fields", []):
            clusters[key]["failed_fields"][ff.get("field", "unknown")] += 1
        if len(clusters[key]["samples"]) < 3:
            clusters[key]["samples"].append(failure)

    # Sort by failure count
    sorted_clusters = dict(sorted(clusters.items(), key=lambda x: -x[1]["count"]))
    
    return {
        "clusters": {k: {"count": v["count"], "failed_fields": dict(v["failed_fields"]),
                          "sample_count": len(v["samples"])} for k, v in sorted_clusters.items()},
        "total_failures": sum(c["count"] for c in clusters.values()),
        "top_failure_mode": max(clusters.items(), key=lambda x: x[1]["count"])[0] if clusters else None,
    }


def print_failure_report(results: dict):
    """Print failure analysis report."""
    print(f"\n{'='*55}")
    print(f"FAILURE ANALYSIS — {results['total_failures']} total failures")
    print(f"{'='*55}")
    for cluster, data in results["clusters"].items():
        print(f"\n📁 {cluster} ({data['count']} failures)")
        for field, count in sorted(data["failed_fields"].items(), key=lambda x: -x[1]):
            print(f"    {field}: {count} failures")


if __name__ == "__main__":
    failures = [
        {"failed_fields": [{"field": "name"}, {"field": "dob"}]},
        {"failed_fields": [{"field": "name"}]},
        {"failed_fields": [{"field": "amount"}]},
    ]
    meta = [
        {"doc_type": "aadhaar", "scan_quality": "noisy"},
        {"doc_type": "aadhaar", "scan_quality": "noisy"},
        {"doc_type": "invoice", "scan_quality": "clean"},
    ]
    results = analyze_failures(failures, meta)
    print_failure_report(results)
