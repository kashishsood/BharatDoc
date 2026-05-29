"""
End-to-end output check — runs extraction on all 4 Aadhaar images
and prints the results. No Streamlit needed.
"""
import sys, os, json
sys.path.insert(0, ".")

from core.vlm_extractor import run_paddle_ocr, DocumentExtractor

IMAGES = [
    "data/mock_dataset/aadhaar_0000.png",
    "data/mock_dataset/aadhaar_0005.png",
    "data/mock_dataset/aadhaar_0010.png",
    "data/mock_dataset/aadhaar_0015.png",
]

print("=" * 60)
print("STEP 1: PaddleOCR — reading real image content")
print("=" * 60)
for img in IMAGES:
    ocr = run_paddle_ocr(img)
    print(f"\n[{os.path.basename(img)}]")
    print(f"  words : {ocr['word_count']}")
    print(f"  text  : {ocr['full_text'][:120]}")
    assert "rajesh" not in ocr["full_text"].lower(), \
        f"MOCK DATA DETECTED in {img}"
print("\n[PASS] All images read real OCR content — no mock data\n")

print("=" * 60)
print("STEP 2: DocumentExtractor — model availability")
print("=" * 60)
e = DocumentExtractor()
print(f"  PaddleOCR  : {'OK' if e._paddle_available else 'MISSING'}")
print(f"  Qwen2.5-VL : {'OK' if e._qwen_available else 'MISSING'}")
print(f"  Donut      : {'OK' if e._donut_available else 'MISSING'}")
assert e._paddle_available, "PaddleOCR not available"
assert e._qwen_available,   "Qwen2.5-VL not available"

print("\n[PASS] Required models available\n")

print("=" * 60)
print("STEP 3: Full extraction on aadhaar_0000.png")
print("(Qwen model load — takes 2-5 min on first run)")
print("=" * 60)
result = e.extract(IMAGES[0], doc_type="aadhaar")

print("\nExtracted fields:")
for k, v in result.items():
    if not k.startswith("_"):
        print(f"  {k:20s}: {v}")

method = result.get("_extraction_method", "")
dob    = str(result.get("dob", ""))

print(f"\n  _extraction_method : {method}")
print(f"  _doc_type          : {result.get('_doc_type')}")
print(f"  _ocr_word_count    : {len(result.get('_ocr_words', []))}")

print("\n--- Assertions ---")
assert method == "qwen2.5-vl", f"FAIL: method='{method}', expected 'qwen2.5-vl'"
print("[PASS] Extraction method = qwen2.5-vl")

assert "male" not in dob.lower() and "female" not in dob.lower(), \
    f"FAIL: gender merged into dob: '{dob}'"
print(f"[PASS] DOB = '{dob}' — no gender leakage")

assert result.get("name") not in (None, "", "null"), \
    "FAIL: name field is empty"
print(f"[PASS] Name extracted: '{result.get('name')}'")

print("\n" + "=" * 60)
print("ALL CHECKS PASSED")
print("=" * 60)
