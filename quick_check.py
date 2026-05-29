"""Quick check — Tests 1 & 2 only (no Qwen model load)."""
import sys, os
sys.path.insert(0, ".")

image_path = "data/mock_dataset/aadhaar_0000.png"
print(f"File: {image_path}")
print(f"Exists: {os.path.exists(image_path)}")
print(f"Size: {os.path.getsize(image_path)} bytes")
print()

# Test 1: PaddleOCR reads real content
from core.vlm_extractor import run_paddle_ocr
ocr = run_paddle_ocr(image_path)
print(f"PaddleOCR words: {ocr['word_count']}")
print(f"OCR text:\n{ocr['full_text']}")
print()
assert ocr["word_count"] > 0, "FAIL: 0 words returned"
assert "rajesh" not in ocr["full_text"].lower(), "FAIL: mock data detected (Rajesh Kumar)"
print("[PASS] Test 1: Real OCR — no mock data")

# Test 2: Qwen available
from core.vlm_extractor import DocumentExtractor
e = DocumentExtractor()
assert e._qwen_available, "FAIL: Qwen not available — check transformers install"
print("[PASS] Test 2: Qwen2.5-VL imports OK")
assert e._paddle_available, "FAIL: PaddleOCR not available"
print("[PASS] Test 3: PaddleOCR available")

print()
print("=== All fast checks passed ===")
print("NOTE: Full verify_fix.py (Qwen extraction + DOB check) requires")
print("      model load time (~2-5 min on CPU). Run: python verify_fix.py data/mock_dataset/aadhaar_0000.png")
