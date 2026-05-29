"""
BharatDoc-VLM: Retrain Trigger
=================================

Watches failure buffer. When count exceeds threshold (default: 500),
sends notification to trigger retraining pipeline.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 500
FAILURES_PATH = Path("data/failures.jsonl")


def count_failures(path: Path = FAILURES_PATH) -> int:
    """Count failures in the JSONL buffer."""
    if not path.exists():
        return 0
    with open(path, "r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def check_retrain_trigger(threshold: int = DEFAULT_THRESHOLD,
                           path: Path = FAILURES_PATH) -> dict:
    """
    Check if retraining should be triggered.
    
    Returns trigger status and failure count.
    """
    count = count_failures(path)
    should_trigger = count >= threshold

    result = {
        "failure_count": count,
        "threshold": threshold,
        "should_retrain": should_trigger,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    if should_trigger:
        logger.warning(f"🔄 RETRAIN TRIGGER: {count} failures >= {threshold} threshold")
        logger.warning("  Action: Initiate retraining pipeline")
        logger.warning("  1. Sample hard negatives from failure buffer")
        logger.warning("  2. Export for annotation via Label Studio")
        logger.warning("  3. Retrain model with new annotated data")
        logger.warning("  4. Evaluate and compare with baseline")
        logger.warning("  5. Deploy if metrics improve")
    else:
        logger.info(f"Retrain check: {count}/{threshold} failures (not triggered)")

    return result


def watch_failures(threshold: int = DEFAULT_THRESHOLD,
                   check_interval: int = 60,
                   path: Path = FAILURES_PATH):
    """
    Continuously watch the failure buffer and trigger retraining.
    
    In production, this would be a Celery periodic task or cron job.
    """
    logger.info(f"Watching failure buffer (threshold={threshold}, interval={check_interval}s)")
    while True:
        result = check_retrain_trigger(threshold, path)
        if result["should_retrain"]:
            # In production: send notification (Slack, PagerDuty, etc.)
            logger.warning("Retraining notification sent")
            break
        time.sleep(check_interval)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD)
    parser.add_argument("--watch", action="store_true", help="Continuously watch")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    
    if args.watch:
        watch_failures(args.threshold)
    else:
        result = check_retrain_trigger(args.threshold)
        print(json.dumps(result, indent=2))
