"""
BharatDoc-VLM: Checkpoint Manager
====================================

Save/load training checkpoints with metadata tracking.
Supports best-model selection by validation metric.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    Manages training checkpoints with metadata and best-model tracking.
    
    Why custom instead of HuggingFace Trainer:
    - Works with mock models that don't have save_pretrained()
    - Tracks custom metrics (field_f1) not just loss
    - Maintains a manifest of all checkpoints for experiment comparison
    """

    def __init__(self, config: dict):
        ckpt_cfg = config.get("checkpoints", {})
        self.output_dir = Path(ckpt_cfg.get("output_dir", "checkpoints"))
        self.save_best = ckpt_cfg.get("save_best", True)
        self.metric_name = ckpt_cfg.get("metric_for_best", "field_f1")
        self.greater_is_better = ckpt_cfg.get("greater_is_better", True)
        self.max_checkpoints = ckpt_cfg.get("max_checkpoints", 3)
        self.best_metric = None
        self.history = []
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save(self, model, epoch: int, metrics: dict, extra: Optional[dict] = None) -> Path:
        """Save a checkpoint with metadata."""
        ckpt_dir = self.output_dir / f"checkpoint_epoch{epoch:03d}"
        ckpt_dir.mkdir(parents=True, exist_ok=True)

        # Save model if it has save_pretrained (real HF models)
        if hasattr(model, "save_pretrained"):
            model.save_pretrained(str(ckpt_dir))
            logger.info(f"Model weights saved to {ckpt_dir}")

        # Save metadata
        metadata = {
            "epoch": epoch,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "metrics": metrics,
            "extra": extra or {},
        }
        with open(ckpt_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        self.history.append(metadata)

        # Track best model
        metric_val = metrics.get(self.metric_name) or metrics.get("loss")
        if metric_val is not None:
            is_best = False
            if self.best_metric is None:
                is_best = True
            elif self.greater_is_better and metric_val > self.best_metric:
                is_best = True
            elif not self.greater_is_better and metric_val < self.best_metric:
                is_best = True

            if is_best:
                self.best_metric = metric_val
                best_path = self.output_dir / "best"
                best_path.mkdir(parents=True, exist_ok=True)
                with open(best_path / "metadata.json", "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2)
                logger.info(f"New best model: {self.metric_name}={metric_val}")

        # Cleanup old checkpoints
        self._cleanup()
        return ckpt_dir

    def _cleanup(self):
        """Remove oldest checkpoints beyond max_checkpoints."""
        ckpt_dirs = sorted(
            [d for d in self.output_dir.iterdir() if d.is_dir() and d.name.startswith("checkpoint_")],
            key=lambda d: d.stat().st_mtime,
        )
        while len(ckpt_dirs) > self.max_checkpoints:
            oldest = ckpt_dirs.pop(0)
            import shutil
            shutil.rmtree(oldest)
            logger.info(f"Removed old checkpoint: {oldest.name}")

    def load_best(self) -> Optional[dict]:
        """Load metadata of the best checkpoint."""
        best_meta = self.output_dir / "best" / "metadata.json"
        if best_meta.exists():
            with open(best_meta, "r", encoding="utf-8") as f:
                return json.load(f)
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    config = {"checkpoints": {"output_dir": "checkpoints", "save_best": True,
                               "metric_for_best": "loss", "greater_is_better": False, "max_checkpoints": 3}}
    mgr = CheckpointManager(config)
    
    class DummyModel:
        pass
    
    for epoch in range(5):
        loss = 2.0 - epoch * 0.3
        mgr.save(DummyModel(), epoch, {"loss": loss})
    
    best = mgr.load_best()
    print(f"Best checkpoint: {best}")
