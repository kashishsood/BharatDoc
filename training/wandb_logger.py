"""
BharatDoc-VLM: Weights & Biases Logger
========================================

W&B integration for experiment tracking: loss curves, per-field F1,
and sample prediction images per epoch.

Gracefully degrades to console logging when W&B is not configured.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class WandbLogger:
    """
    W&B logger that gracefully falls back to console logging.
    
    Controlled by config.yaml logging.use_wandb flag.
    """

    def __init__(self, config: dict):
        self.config = config
        log_cfg = config.get("logging", {})
        self.enabled = log_cfg.get("use_wandb", False)
        self.project = log_cfg.get("wandb_project", "bharatdoc-vlm")
        self.entity = log_cfg.get("wandb_entity")
        self._run = None

        if self.enabled:
            try:
                import wandb
                self._run = wandb.init(
                    project=self.project,
                    entity=self.entity,
                    config=config,
                )
                logger.info(f"W&B initialized: {self.project}")
            except ImportError:
                logger.warning("wandb not installed, falling back to console logging")
                self.enabled = False
            except Exception as e:
                logger.warning(f"W&B init failed: {e}, falling back to console logging")
                self.enabled = False
        else:
            logger.info("W&B logging disabled (set logging.use_wandb=true to enable)")

    def log_metrics(self, metrics: dict, step: Optional[int] = None):
        """Log metrics to W&B or console."""
        if self.enabled and self._run:
            import wandb
            wandb.log(metrics, step=step)
        else:
            # Console fallback — format nicely
            parts = [f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}" for k, v in metrics.items()]
            logger.info(f"Metrics: {' | '.join(parts)}")

    def log_image(self, key: str, image, caption: str = ""):
        """Log an image to W&B."""
        if self.enabled and self._run:
            import wandb
            wandb.log({key: wandb.Image(image, caption=caption)})
        else:
            logger.info(f"Image logged: {key} ({caption})")

    def log_table(self, key: str, columns: list, data: list):
        """Log a table to W&B."""
        if self.enabled and self._run:
            import wandb
            table = wandb.Table(columns=columns, data=data)
            wandb.log({key: table})
        else:
            logger.info(f"Table logged: {key} ({len(data)} rows)")

    def finish(self):
        """Finish W&B run."""
        if self.enabled and self._run:
            import wandb
            wandb.finish()
            logger.info("W&B run finished")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    config = {"logging": {"use_wandb": False, "wandb_project": "test"}}
    wb = WandbLogger(config)
    wb.log_metrics({"loss": 0.5, "f1": 0.85})
    wb.finish()
