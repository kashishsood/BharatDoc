"""
BharatDoc-VLM: Failure Flagging Service
==========================================

POST /feedback endpoint for logging bad predictions.
Stores failures in failures.jsonl for downstream processing.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

FAILURES_PATH = Path("data/failures.jsonl")


class FeedbackRequest(BaseModel):
    """Feedback payload from production users or QA reviewers."""
    request_id: str
    predicted_output: dict
    correct_output: dict
    doc_type: str
    reporter: Optional[str] = None
    notes: Optional[str] = None


class FailureFlagService:
    """Logs flagged failures to JSONL file for retraining pipeline."""

    def __init__(self, output_path: Path = FAILURES_PATH):
        self.output_path = output_path
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.buffer_count = self._count_existing()
        logger.info(f"Failure flag service: {self.buffer_count} existing failures in {output_path}")

    def _count_existing(self) -> int:
        if not self.output_path.exists():
            return 0
        with open(self.output_path, "r", encoding="utf-8") as f:
            return sum(1 for _ in f)

    def flag(self, feedback: FeedbackRequest) -> dict:
        """Log a flagged failure."""
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "request_id": feedback.request_id,
            "doc_type": feedback.doc_type,
            "predicted": feedback.predicted_output,
            "correct": feedback.correct_output,
            "reporter": feedback.reporter,
            "notes": feedback.notes,
        }
        with open(self.output_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        
        self.buffer_count += 1
        logger.info(f"Failure flagged: {feedback.request_id} ({feedback.doc_type}) "
                     f"[buffer: {self.buffer_count}]")
        return {"status": "flagged", "buffer_count": self.buffer_count}

    def get_failures(self, limit: int = 100) -> list[dict]:
        """Read recent failures from the JSONL file."""
        if not self.output_path.exists():
            return []
        failures = []
        with open(self.output_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    failures.append(json.loads(line))
        return failures[-limit:]


def create_feedback_app() -> FastAPI:
    """Create FastAPI app for the feedback endpoint."""
    app = FastAPI(title="BharatDoc-VLM Feedback", version="1.0.0")
    service = FailureFlagService()

    @app.post("/feedback")
    async def submit_feedback(feedback: FeedbackRequest):
        return service.flag(feedback)

    @app.get("/feedback/count")
    async def get_count():
        return {"buffer_count": service.buffer_count}

    @app.get("/feedback/recent")
    async def get_recent(limit: int = 10):
        return {"failures": service.get_failures(limit)}

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    service = FailureFlagService()
    fb = FeedbackRequest(
        request_id="test_001", doc_type="aadhaar",
        predicted_output={"name": "Rajesh Kunar"},
        correct_output={"name": "Rajesh Kumar"},
    )
    result = service.flag(fb)
    print(f"✅ {result}")
