"""
BharatDoc-VLM: Annotation Sampling Strategy
=============================================

Hard negative + random sampling for efficient human annotation.
Prioritizes cases where the model is most likely to be wrong.
"""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path

logger = logging.getLogger(__name__)


def sample_for_annotation(failures_path: str = "data/failures.jsonl",
                          unlabelled_path: str = "data/unlabelled/",
                          n_hard: int = 30, n_random: int = 20) -> list[dict]:
    """
    Sample documents for human annotation using a mixed strategy.
    
    Strategy:
    - n_hard: hard negatives (flagged failures with lowest confidence)
    - n_random: random samples from unlabelled pool (prevents bias)
    """
    samples = []

    # Hard negatives from failure buffer
    failures = _load_failures(failures_path)
    # Sort by model confidence (lowest first — hardest cases)
    failures.sort(key=lambda x: x.get("predicted", {}).get("confidence", 1.0))
    hard_samples = failures[:n_hard]
    for s in hard_samples:
        s["sampling_strategy"] = "hard_negative"
    samples.extend(hard_samples)

    # Random samples from unlabelled pool
    unlabelled_dir = Path(unlabelled_path)
    if unlabelled_dir.exists():
        unlabelled_files = list(unlabelled_dir.glob("*.png")) + list(unlabelled_dir.glob("*.jpg"))
        random_files = random.sample(unlabelled_files, min(n_random, len(unlabelled_files)))
        for f in random_files:
            samples.append({"image_path": str(f), "sampling_strategy": "random",
                            "doc_type": "unknown"})

    logger.info(f"Sampled {len(samples)} for annotation: {len(hard_samples)} hard + {len(samples) - len(hard_samples)} random")
    return samples


def _load_failures(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    failures = []
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                failures.append(json.loads(line))
    return failures


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    samples = sample_for_annotation()
    print(f"✅ {len(samples)} samples selected for annotation")
