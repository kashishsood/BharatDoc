"""
Verification script. Run with the actual Aadhaar image.
Expected output: real name from the card, not "Rajesh Kumar".

Usage: python verify_fix.py path/to/aadhaar.jpg
"""
import sys
import os

sys.path.insert(0, ".")


def verify(image_path):
    print(f"File: {image_path}")
    print(f"Exists: {os.path.exists(image_path)}")
    print(f"Size: {os.path.getsize(image_path)} bytes")
    print()

    # Test 1: PaddleOCR reads real content (not mock)
    from core.vlm_extractor import run_paddle_ocr
    ocr = run_paddle_ocr(image_path)
    print(f"PaddleOCR words: {ocr['word_count']}")
    print(f"OCR text:\n{ocr['full_text'][:400]}")
    print()

    assert ocr["word_count"] > 0, "FAIL: PaddleOCR returned 0 words — file not read"
    assert "rajesh" not in ocr["full_text"].lower() or \
           "kashish" in ocr["full_text"].lower(), \
        "FAIL: OCR may be returning mock data (found 'Rajesh Kumar')"
    print("[PASS] Test 1: PaddleOCR returned real words from the actual image")

    # Test 2: Qwen is available
    from core.vlm_extractor import DocumentExtractor
    extractor = DocumentExtractor()
    assert extractor._qwen_available, \
        "FAIL: Qwen not available. Run: pip install transformers>=4.45.0 qwen-vl-utils torch"
    print("[PASS] Test 2: Qwen2.5-VL imports OK")

    # Test 3: Full extraction
    result = extractor.extract(image_path, doc_type="aadhaar")
    print("\nExtracted fields:")
    for k, v in result.items():
        if not k.startswith("_"):
            print(f"  {k}: {v}")

    # Test 4: DOB does not contain gender
    dob = str(result.get("dob", ""))
    assert "male" not in dob.lower() and "female" not in dob.lower(), \
        f"FAIL: gender merged into dob: '{dob}'"
    print(f"\n[PASS] Test 3: DOB = '{dob}' (no gender leakage)")

    # Test 5: Extraction method is Qwen, not field_extractor
    method = result.get("_extraction_method", "")
    assert method == "qwen2.5-vl", \
        f"FAIL: extraction method is '{method}', expected 'qwen2.5-vl' — Qwen not being called"
    print(f"[PASS] Test 4: Extraction method = {method}")

    print("\n=== All checks passed ===")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_fix.py path/to/aadhaar.jpg")
        sys.exit(1)
    verify(sys.argv[1])
