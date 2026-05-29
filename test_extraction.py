"""
BharatDoc-VLM: Quick extraction verification script.

Tests the full pipeline: PaddleOCR → classify → Qwen/Donut → result.
Falls back gracefully if models aren't installed.

Usage:
    python test_extraction.py path/to/doc.jpg [doc_type]
    python test_extraction.py                 # uses test image
"""

import sys
import logging

sys.path.insert(0, ".")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)


def test(image_path: str, doc_type: str = None):
    from core.vlm_extractor import DocumentExtractor

    print(f"\n{'='*60}")
    print(f"File: {image_path}")
    print(f"Doc type override: {doc_type or 'auto-detect'}")
    print(f"{'='*60}")

    extractor = DocumentExtractor()
    result = extractor.extract(image_path, doc_type=doc_type)

    print(f"\nDetected doc_type : {result.get('_doc_type')}")
    print(f"Extraction method : {result.get('_extraction_method')}")
    print(f"OCR words found   : {len(result.get('_ocr_words', []))}")
    ocr_text = result.get("_ocr_text", "")
    print(f"OCR text preview  :\n{ocr_text[:300]}")

    print("\nExtracted fields:")
    for k, v in result.items():
        if not k.startswith("_"):
            print(f"  {k}: {v}")

    print(f"\n{'='*60}")
    print("[OK] Pipeline executed successfully")


def test_with_blank_image():
    """Test with a blank image to verify the pipeline runs end-to-end."""
    import tempfile
    from PIL import Image

    img = Image.new("RGB", (800, 600), (255, 255, 255))
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(tmp, format="PNG")
    tmp.close()
    test(tmp.name, "aadhaar")

    import os
    os.unlink(tmp.name)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1]
        dtype = sys.argv[2] if len(sys.argv) > 2 else None
        test(path, dtype)
    else:
        print("No image path provided — running with blank test image")
        test_with_blank_image()
