"""
BharatDoc-VLM: Data Pipeline Tests
=====================================
"""

import pytest
import sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestCollect:
    def test_generate_mock_dataset(self, tmp_path):
        from data_pipeline.collect import generate_mock_dataset
        result = generate_mock_dataset(tmp_path, num_samples=5)
        assert result.exists()
        assert (result / "manifest.json").exists()
        pngs = list(result.glob("*.png"))
        assert len(pngs) == 5

    def test_ground_truth_format(self, tmp_path):
        from data_pipeline.collect import generate_mock_dataset
        import json
        result = generate_mock_dataset(tmp_path, num_samples=3, doc_types=["aadhaar"])
        jsons = list(result.glob("*.json"))
        # Exclude manifest.json
        gt_files = [f for f in jsons if f.name != "manifest.json"]
        for gt_file in gt_files:
            data = json.loads(gt_file.read_text(encoding="utf-8"))
            assert "doc_type" in data
            assert data["doc_type"] == "aadhaar"


class TestNoiseProfiles:
    def test_photocopy(self):
        from data_pipeline.noise_profiles import photocopy
        img = Image.new("RGB", (200, 200), (255, 255, 255))
        result = photocopy(img, intensity=0.5)
        assert result.size == img.size

    def test_mobile_scan(self):
        from data_pipeline.noise_profiles import mobile_scan
        img = Image.new("RGB", (200, 200), (255, 255, 255))
        result = mobile_scan(img, intensity=0.5)
        assert result.size == img.size

    def test_stamp_overlay(self):
        from data_pipeline.noise_profiles import stamp_overlay
        img = Image.new("RGB", (200, 200), (255, 255, 255))
        result = stamp_overlay(img, intensity=0.5)
        assert result.size == img.size

    def test_apply_random(self):
        from data_pipeline.noise_profiles import apply_random_noise
        img = Image.new("RGB", (200, 200), (255, 255, 255))
        result = apply_random_noise(img)
        assert result.size == img.size


class TestQualityFilter:
    def test_good_image_passes(self):
        from data_pipeline.quality_filter import assess_quality
        from PIL import ImageDraw
        img = Image.new("RGB", (800, 600), (240, 240, 240))
        draw = ImageDraw.Draw(img)
        draw.text((100, 100), "High contrast text on light background", fill=(0, 0, 0))
        report = assess_quality(img)
        assert report.quality_score > 0

    def test_tiny_image_fails(self):
        from data_pipeline.quality_filter import assess_quality
        img = Image.new("RGB", (50, 50), (128, 128, 128))
        report = assess_quality(img)
        assert not report.passed


class TestOCR:
    def test_ocr_on_blank_image(self):
        """Real OCR on a blank image should return 0 words (not mock data)."""
        from data_pipeline.ocr_parse import ocr_image
        img = Image.new("RGB", (800, 600), (255, 255, 255))
        try:
            result = ocr_image(img)
            # Blank image → 0 words is correct; mock data would have words
            assert "Rajesh" not in result.full_text, \
                "Mock data detected — ocr_image is still returning hardcoded text"
        except RuntimeError as e:
            # No OCR engine installed — acceptable in CI without paddleocr
            assert "OCR engine" in str(e) or "paddleocr" in str(e).lower()


class TestAugment:
    def test_augment_image(self):
        from data_pipeline.augment import augment_image
        img = Image.new("RGB", (200, 200), (255, 255, 255))
        result = augment_image(img)
        assert result.size == img.size
