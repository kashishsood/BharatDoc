"""Quick OCR-only test to verify Bug 1 fix (no mock data)."""
import sys
sys.path.insert(0, ".")

from core.vlm_extractor import run_paddle_ocr

image_path = "data/mock_dataset/aadhaar_0000.png"
print(f"Testing: {image_path}")
print("="*60)

result = run_paddle_ocr(image_path)

print(f"OCR Engine: {result['engine']}")
print(f"Words found: {result['word_count']}")
print(f"\nOCR Text:\n{result['full_text']}")
print("="*60)

# Verify no mock data
assert result['word_count'] > 0, "FAIL: No words detected"
assert "rajesh" not in result['full_text'].lower(), "FAIL: Mock data detected (Rajesh Kumar)"
assert "ananya" in result['full_text'].lower() or "government" in result['full_text'].lower(), \
    "FAIL: Expected real content from aadhaar_0000.png"

print("\n[PASS] SUCCESS: PaddleOCR reading real data (not mock)")
print("[PASS] Bug 1 FIXED: Mock data eliminated from pipeline")
