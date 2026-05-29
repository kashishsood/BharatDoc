"""
BharatDoc-VLM: Annotation Export
===================================

Converts flagged failures to Label Studio import format.
Includes image paths and pre-annotations from the model.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def export_for_annotation(failures_path: str = "data/failures.jsonl",
                          output_path: str = "data/label_studio_tasks.json",
                          limit: int = 100) -> str:
    """
    Convert failures to Label Studio import format.
    
    Each task includes:
    - Image path for the failed document
    - Pre-annotations from model predictions (so reviewers correct, not annotate from scratch)
    - Doc type metadata for filtering in Label Studio
    """
    failures = []
    fp = Path(failures_path)
    if fp.exists():
        with open(fp, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    failures.append(json.loads(line))

    failures = failures[:limit]
    tasks = []

    for i, failure in enumerate(failures):
        task = {
            "id": i + 1,
            "data": {
                "image": failure.get("image_path", f"/data/uploads/failure_{failure.get('request_id', i)}.png"),
                "doc_type": failure.get("doc_type", "unknown"),
                "request_id": failure.get("request_id", ""),
                "original_timestamp": failure.get("timestamp", ""),
            },
            "predictions": [{
                "model_version": "bharatdoc-vlm-v1",
                "score": failure.get("predicted", {}).get("confidence", 0.5),
                "result": _build_pre_annotations(failure.get("predicted", {})),
            }],
        }
        tasks.append(task)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

    logger.info(f"Exported {len(tasks)} tasks to {output_path}")
    return output_path


def _build_pre_annotations(predicted: dict) -> list[dict]:
    """Convert prediction dict to Label Studio annotation format."""
    annotations = []
    for field_name, value in predicted.items():
        if field_name in ("confidence", "stage", "corrections_applied", "fallback"):
            continue
        annotations.append({
            "id": f"pred_{field_name}",
            "type": "textarea",
            "value": {"text": [str(value)]},
            "from_name": field_name,
            "to_name": "document",
        })
    return annotations


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    path = export_for_annotation()
    print(f"✅ Exported to {path}")
