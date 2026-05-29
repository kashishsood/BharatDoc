"""
BharatDoc-VLM: PyTorch Dataset for Document VQA
=================================================

Unified dataset class supporting multiple doc types and models.
Loads image + question + answer triples from the manifest format.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional, Callable

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class DocumentVQADataset:
    """
    PyTorch-compatible dataset for document visual question answering.
    
    Loads from manifest.json which maps each sample to:
    - image path
    - ground truth JSON
    - doc_type, language, scan_quality metadata
    
    Supports per-model preprocessing via transform functions.
    """

    def __init__(self, manifest_path: str, transform: Optional[Callable] = None,
                 doc_types: Optional[list[str]] = None, max_samples: Optional[int] = None):
        self.manifest_path = Path(manifest_path)
        self.transform = transform
        self.samples = self._load_manifest(doc_types, max_samples)
        logger.info(f"Loaded {len(self.samples)} samples from {manifest_path}")

    def _load_manifest(self, doc_types, max_samples) -> list[dict]:
        """Load and filter the dataset manifest."""
        if not self.manifest_path.exists():
            logger.warning(f"Manifest not found: {self.manifest_path}, creating empty dataset")
            return []
        
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        
        # Filter by doc type if specified
        if doc_types:
            manifest = [s for s in manifest if s.get("doc_type") in doc_types]
        
        # Limit samples
        if max_samples:
            manifest = manifest[:max_samples]
        
        return manifest

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> dict:
        sample = self.samples[idx]
        
        # Resolve paths relative to manifest directory
        base_dir = self.manifest_path.parent
        img_path = base_dir / sample.get("image_path", sample.get("id", "") + ".png")
        gt_path = base_dir / sample.get("gt_path", sample.get("id", "") + ".json")

        # Load image
        if img_path.exists():
            image = Image.open(img_path).convert("RGB")
        else:
            # Create placeholder image for testing
            image = Image.new("RGB", (800, 600), (255, 255, 255))

        # Load ground truth
        ground_truth = {}
        if gt_path.exists():
            with open(gt_path, "r", encoding="utf-8") as f:
                ground_truth = json.load(f)

        result = {
            "image": image,
            "ground_truth": ground_truth,
            "doc_type": sample.get("doc_type", "unknown"),
            "language": sample.get("language", "english"),
            "scan_quality": sample.get("scan_quality", "clean"),
            "sample_id": sample.get("id", f"sample_{idx}"),
        }

        # Apply model-specific transform
        if self.transform:
            result = self.transform(result)

        return result

    def get_splits(self, train_ratio: float = 0.8, val_ratio: float = 0.1):
        """Split dataset into train/val/test sets."""
        n = len(self.samples)
        indices = list(range(n))
        np.random.shuffle(indices)
        
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))
        
        return {
            "train": indices[:train_end],
            "val": indices[train_end:val_end],
            "test": indices[val_end:],
        }


def create_donut_transform(processor=None, max_length: int = 512):
    """Create transform function for Donut model preprocessing."""
    def transform(sample):
        image = sample["image"]
        if processor:
            pixel_values = processor(image, return_tensors="pt").pixel_values.squeeze(0)
            sample["pixel_values"] = pixel_values
        else:
            sample["pixel_values"] = np.array(image.resize((960, 720)))
        
        # Format ground truth as Donut-style token sequence
        gt = sample["ground_truth"]
        sample["target_text"] = json.dumps(gt, ensure_ascii=False)
        return sample
    return transform


def create_trocr_transform(processor=None, max_length: int = 256):
    """Create transform for TrOCR handwriting recognition."""
    def transform(sample):
        image = sample["image"]
        if processor:
            pixel_values = processor(image, return_tensors="pt").pixel_values.squeeze(0)
            sample["pixel_values"] = pixel_values
        else:
            sample["pixel_values"] = np.array(image.resize((384, 384)))
        
        gt = sample["ground_truth"]
        sample["target_text"] = gt.get("raw_text", json.dumps(gt, ensure_ascii=False))
        return sample
    return transform


import json

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Generate mock manifest for testing
    from data_pipeline.collect import generate_mock_dataset
    dataset_dir = generate_mock_dataset(Path("data"), num_samples=10)
    
    ds = DocumentVQADataset(str(dataset_dir / "manifest.json"))
    print(f"Dataset size: {len(ds)}")
    if len(ds) > 0:
        sample = ds[0]
        print(f"Sample: {sample['sample_id']} ({sample['doc_type']})")
        print(f"  GT keys: {list(sample['ground_truth'].keys())}")
