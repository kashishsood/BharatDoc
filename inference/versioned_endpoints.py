"""
BharatDoc-VLM: Versioned Endpoints Router
============================================

Manages /predict/v1 and /predict/v2 with A/B traffic splitting.
"""

from __future__ import annotations

import logging
import random
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


class VersionRouter:
    """Routes traffic between v1 and v2 based on ab_config.yaml."""

    def __init__(self, config_path: str = "inference/ab_config.yaml"):
        self.config = self._load_config(config_path)
        self.v2_percentage = self.config.get("v2_traffic_percentage", 50)
        logger.info(f"Version router: v2 traffic = {self.v2_percentage}%")

    def _load_config(self, path: str) -> dict:
        try:
            with open(path, "r") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return {"v2_traffic_percentage": 50}

    def get_version(self) -> str:
        """Determine which version to route to based on traffic split."""
        if random.randint(1, 100) <= self.v2_percentage:
            return "v2"
        return "v1"

    def get_endpoint(self, base_url: str) -> str:
        version = self.get_version()
        return f"{base_url}/predict/{version}"


if __name__ == "__main__":
    router = VersionRouter()
    counts = {"v1": 0, "v2": 0}
    for _ in range(1000):
        counts[router.get_version()] += 1
    print(f"Traffic split over 1000 requests: {counts}")
