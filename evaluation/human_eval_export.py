"""
BharatDoc-VLM: Human Evaluation Export
========================================

Exports failed predictions to Label Studio JSON format for human review.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def export_to_label_studio(failures: list[dict], output_path: str = "evaluation/label_studio_tasks.json") -> str:
    """
    Convert failures to Label Studio import format.
    
    Each task includes the image path and pre-annotations from the model
    so human reviewers can correct rather than annotate from scratch.
    """
    tasks = []
    for i, failure in enumerate(failures):
        task = {
            "id": i + 1,
            "data": {
                "image": failure.get("image_path", f"/data/images/failure_{i:04d}.png"),
                "doc_type": failure.get("doc_type", "unknown"),
            },
            "predictions": [{
                "model_version": "bharatdoc-vlm-v1",
                "result": [],
            }],
        }
        # Add pre-annotations for each predicted field
        for field_name, field_value in failure.get("predicted", {}).items():
            task["predictions"][0]["result"].append({
                "type": "textarea",
                "value": {"text": [str(field_value)]},
                "from_name": field_name,
                "to_name": "document",
            })
        tasks.append(task)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

    logger.info(f"Exported {len(tasks)} tasks to {output_path}")
    return output_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    failures = [
        {"image_path": "/data/img_001.png", "doc_type": "aadhaar",
         "predicted": {"name": "Rajesh Kunar", "dob": "15/08/1990"}},
        {"image_path": "/data/img_002.png", "doc_type": "invoice",
         "predicted": {"total": "1,121,0OO"}},
    ]
    export_to_label_studio(failures)
    print("✅ Exported to Label Studio format")
