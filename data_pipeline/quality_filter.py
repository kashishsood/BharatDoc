"""
BharatDoc-VLM: Quality Filter
===============================

Filters document images based on quality metrics: blur detection,
resolution check, and contrast analysis. Returns a quality score
and pass/fail per image.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageStat

logger = logging.getLogger(__name__)

# Quality thresholds — tuned for Indian document scans
MIN_RESOLUTION = (200, 200)        # Minimum width x height
MIN_BLUR_SCORE = 50.0              # Laplacian variance threshold
MIN_CONTRAST = 30.0                # Minimum standard deviation of pixel values
MAX_ASPECT_RATIO = 5.0             # Reject extremely elongated crops


@dataclass
class QualityReport:
    """Quality assessment for a single document image."""
    image_path: str
    passed: bool
    blur_score: float        # Higher = sharper (Laplacian variance)
    resolution: tuple[int, int]
    contrast: float          # Std dev of pixel intensities
    aspect_ratio: float
    quality_score: float     # 0-1 composite score
    issues: list[str]

    @property
    def scan_quality(self) -> str:
        """Categorize as clean/noisy for slice evaluation."""
        return "clean" if self.quality_score > 0.6 else "noisy"


def compute_blur_score(image: Image.Image) -> float:
    """
    Compute blur score using Laplacian variance.
    Higher value = sharper image. Threshold ~50 for readable documents.
    
    Why Laplacian: It's a second-derivative operator that responds strongly
    to edges. Blurry images have fewer sharp edges → lower variance.
    """
    try:
        import cv2
        gray = np.array(image.convert("L"))
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        return float(laplacian.var())
    except ImportError:
        # Fallback without OpenCV: use PIL edge detection
        from PIL import ImageFilter
        edges = image.convert("L").filter(ImageFilter.FIND_EDGES)
        return float(np.array(edges).var())


def compute_contrast(image: Image.Image) -> float:
    """Compute contrast as standard deviation of grayscale pixel values."""
    gray = np.array(image.convert("L"), dtype=np.float32)
    return float(gray.std())


def assess_quality(image: Image.Image, image_path: str = "") -> QualityReport:
    """
    Run full quality assessment on a document image.
    
    Checks:
    1. Resolution: minimum 200x200 for OCR readability
    2. Blur: Laplacian variance > 50 for sharp text
    3. Contrast: std dev > 30 to ensure text/background separation
    4. Aspect ratio: reject extreme crops (> 5:1)
    """
    w, h = image.size
    issues = []
    scores = []

    # Resolution check
    if w < MIN_RESOLUTION[0] or h < MIN_RESOLUTION[1]:
        issues.append(f"Low resolution: {w}x{h} (min {MIN_RESOLUTION[0]}x{MIN_RESOLUTION[1]})")
        scores.append(0.3)
    else:
        scores.append(1.0)

    # Blur detection
    blur = compute_blur_score(image)
    if blur < MIN_BLUR_SCORE:
        issues.append(f"Blurry image: score {blur:.1f} (min {MIN_BLUR_SCORE})")
        scores.append(max(0.1, blur / MIN_BLUR_SCORE))
    else:
        scores.append(min(1.0, blur / (MIN_BLUR_SCORE * 3)))

    # Contrast check
    contrast = compute_contrast(image)
    if contrast < MIN_CONTRAST:
        issues.append(f"Low contrast: {contrast:.1f} (min {MIN_CONTRAST})")
        scores.append(max(0.1, contrast / MIN_CONTRAST))
    else:
        scores.append(min(1.0, contrast / 80.0))

    # Aspect ratio
    aspect = max(w, h) / max(min(w, h), 1)
    if aspect > MAX_ASPECT_RATIO:
        issues.append(f"Extreme aspect ratio: {aspect:.1f} (max {MAX_ASPECT_RATIO})")
        scores.append(0.3)
    else:
        scores.append(1.0)

    quality_score = sum(scores) / len(scores)
    passed = len(issues) == 0

    return QualityReport(
        image_path=image_path, passed=passed,
        blur_score=round(blur, 2), resolution=(w, h),
        contrast=round(contrast, 2), aspect_ratio=round(aspect, 2),
        quality_score=round(quality_score, 3), issues=issues,
    )


def filter_dataset(image_paths: list[str | Path]) -> tuple[list[str], list[QualityReport]]:
    """Filter a list of images, returning paths that pass quality checks."""
    passed = []
    reports = []
    for path in image_paths:
        path = Path(path)
        if not path.exists():
            continue
        image = Image.open(path).convert("RGB")
        report = assess_quality(image, str(path))
        reports.append(report)
        if report.passed:
            passed.append(str(path))
    
    logger.info(f"Quality filter: {len(passed)}/{len(image_paths)} passed")
    return passed, reports


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Test with a dummy image
    img = Image.new("RGB", (800, 600), (240, 240, 240))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.text((100, 100), "Test document text for quality check", fill=(0, 0, 0))
    
    report = assess_quality(img, "test_image.png")
    print(f"Quality: {'PASS' if report.passed else 'FAIL'} (score={report.quality_score})")
    print(f"  Blur: {report.blur_score}, Contrast: {report.contrast}, Resolution: {report.resolution}")
    if report.issues:
        for issue in report.issues:
            print(f"  ⚠️  {issue}")
