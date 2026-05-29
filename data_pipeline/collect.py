"""
BharatDoc-VLM: Dataset Collection
==================================

Downloads benchmark datasets (DocVQA, RVL-CDIP) or generates mock data
for offline pipeline testing. All outputs in unified format: image + JSON.
"""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)
DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

NAMES_EN = [
    "Rajesh Kumar", "Priya Sharma", "Amit Patel", "Sneha Gupta",
    "Vikram Singh", "Ananya Reddy", "Suresh Nair", "Kavita Iyer",
    "Deepak Joshi", "Meera Krishnan", "Arjun Verma", "Pooja Das",
]
NAMES_HI = [
    "राजेश कुमार", "प्रिया शर्मा", "अमित पटेल", "स्नेहा गुप्ता",
    "विक्रम सिंह", "अनन्या रेड्डी", "सुरेश नायर", "कविता अय्यर",
]
ADDRESSES = [
    "H.No 45, Sector 12, Dwarka, New Delhi - 110075",
    "Flat 301, Sunshine Apartments, Koramangala, Bengaluru - 560034",
    "12/A, Gandhi Nagar, Pune - 411041",
    "Plot 67, Anna Nagar, Chennai - 600040",
]


def generate_mock_dataset(output_dir: Path, num_samples: int = 50,
                          doc_types: Optional[list[str]] = None) -> Path:
    """Generate a small mock dataset with known ground truth for testing."""
    if doc_types is None:
        doc_types = ["aadhaar", "invoice", "lic_policy", "handwritten_form", "printed_form"]

    dataset_dir = output_dir / "mock_dataset"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    manifest = []

    for i in range(num_samples):
        doc_type = doc_types[i % len(doc_types)]
        sample_id = f"{doc_type}_{i:04d}"
        img = _generate_doc_image(doc_type)
        gt = _generate_ground_truth(doc_type)

        img.save(dataset_dir / f"{sample_id}.png")
        with open(dataset_dir / f"{sample_id}.json", "w", encoding="utf-8") as f:
            json.dump(gt, f, ensure_ascii=False, indent=2)

        manifest.append({
            "id": sample_id, "doc_type": doc_type,
            "image_path": f"{sample_id}.png", "gt_path": f"{sample_id}.json",
            "language": random.choice(["english", "hindi", "mixed"]),
            "scan_quality": random.choice(["clean", "noisy"]),
        })

    with open(dataset_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    logger.info(f"Generated {num_samples} mock samples in {dataset_dir}")
    return dataset_dir


def _generate_doc_image(doc_type: str) -> Image.Image:
    """Generate a simple document-like image with text fields."""
    sizes = {"aadhaar": (856, 540), "invoice": (800, 1100), "lic_policy": (800, 1000)}
    w, h = sizes.get(doc_type, (800, 600))
    img = Image.new("RGB", (w, h), color=(255, 255, 252))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 16)
        font_lg = ImageFont.truetype("arial.ttf", 24)
    except (OSError, IOError):
        font = ImageFont.load_default()
        font_lg = font

    name = random.choice(NAMES_EN)
    if doc_type == "aadhaar":
        draw.rectangle([(0, 0), (w-1, h-1)], outline=(0, 100, 0), width=3)
        draw.text((20, 20), "Government of India - UIDAI", fill=(0, 0, 0), font=font_lg)
        draw.text((20, 110), f"Name: {name}", fill=(0, 0, 0), font=font)
        num = f"{random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(1000,9999)}"
        draw.text((20, 210), f"Aadhaar: {num}", fill=(0, 0, 0), font=font_lg)
    elif doc_type == "invoice":
        draw.text((20, 20), "TAX INVOICE", fill=(0, 0, 0), font=font_lg)
        draw.text((20, 60), f"INV-2024-{random.randint(1,9999):04d}", fill=(0, 0, 0), font=font)
        draw.text((20, 130), f"Vendor: {name} Enterprises", fill=(0, 0, 0), font=font)
    elif doc_type == "lic_policy":
        draw.text((20, 20), "LIFE INSURANCE CORPORATION OF INDIA", fill=(0, 0, 128), font=font_lg)
        draw.text((20, 110), f"Policy No: {random.randint(10000000,99999999)}", fill=(0, 0, 0), font=font)
        draw.text((20, 140), f"Holder: {name}", fill=(0, 0, 0), font=font)
    else:
        draw.text((20, 20), f"{doc_type.replace('_', ' ').title()}", fill=(0, 0, 0), font=font_lg)
        draw.text((20, 60), f"Name: {name}", fill=(0, 0, 0), font=font)
    return img


def _generate_ground_truth(doc_type: str) -> dict:
    """Generate ground truth extraction matching our schema format."""
    name = random.choice(NAMES_EN)
    if doc_type == "aadhaar":
        return {
            "doc_type": "aadhaar", "name": name, "name_hindi": random.choice(NAMES_HI),
            "date_of_birth": f"{random.randint(1,28):02d}/{random.randint(1,12):02d}/{random.randint(1970,2005)}",
            "gender": random.choice(["MALE", "FEMALE"]),
            "aadhaar_number": f"{random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(1000,9999)}",
            "address": random.choice(ADDRESSES), "pincode": str(random.randint(100000, 999999)),
            "photo_present": True,
        }
    elif doc_type == "lic_policy":
        sa = random.randint(5, 50) * 100000
        return {
            "doc_type": "lic_policy", "policy_number": str(random.randint(10000000, 99999999)),
            "holder_name": name, "plan_name": random.choice(["Jeevan Anand", "Jeevan Labh"]),
            "sum_assured": float(sa), "premium_amount": float(sa // 40),
            "maturity_date": f"{random.randint(1,28):02d}/{random.randint(1,12):02d}/{random.randint(2035,2060)}",
        }
    elif doc_type == "invoice":
        qty, price = random.randint(1, 100), random.randint(100, 10000)
        sub = qty * price
        tax = round(sub * 0.18)
        return {
            "doc_type": "invoice", "invoice_number": f"INV-2024-{random.randint(1,9999):04d}",
            "vendor_name": f"{name} Enterprises",
            "invoice_date": f"{random.randint(1,28):02d}/{random.randint(1,12):02d}/2024",
            "line_items": [{"description": "Service", "quantity": qty, "unit_price": price, "amount": sub}],
            "subtotal": float(sub), "total_tax": float(tax), "total_amount": float(sub + tax),
        }
    return {"doc_type": doc_type, "fields": {"name": name}}


def download_docvqa(output_dir: Path) -> None:
    """Download DocVQA dataset (falls back to mock if unavailable)."""
    try:
        from datasets import load_dataset
        logger.info("Downloading DocVQA from HuggingFace...")
        ds = load_dataset("lmms-lab/DocVQA", split="train[:100]")
        save_dir = output_dir / "docvqa"
        save_dir.mkdir(parents=True, exist_ok=True)
        for i, s in enumerate(ds):
            s["image"].save(save_dir / f"docvqa_{i:04d}.png")
            with open(save_dir / f"docvqa_{i:04d}.json", "w", encoding="utf-8") as f:
                json.dump({"question": s.get("question", ""), "answer": s.get("answer", "")}, f, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"DocVQA download failed ({e}), using mock data")
        generate_mock_dataset(output_dir, num_samples=20)


def download_rvl_cdip(output_dir: Path) -> None:
    """Download RVL-CDIP subset (falls back to mock if unavailable)."""
    try:
        from datasets import load_dataset
        logger.info("Downloading RVL-CDIP subset...")
        ds = load_dataset("rvl_cdip", split="train[:100]")
        save_dir = output_dir / "rvl_cdip"
        save_dir.mkdir(parents=True, exist_ok=True)
        for i, s in enumerate(ds):
            s["image"].save(save_dir / f"rvlcdip_{i:04d}.png")
    except Exception as e:
        logger.warning(f"RVL-CDIP download failed ({e}), using mock data")
        generate_mock_dataset(output_dir, num_samples=20)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Collect/generate datasets")
    parser.add_argument("--output", type=str, default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--num-samples", type=int, default=50)
    parser.add_argument("--mock", action="store_true", default=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    generate_mock_dataset(Path(args.output), num_samples=args.num_samples)
    print(f"✅ Dataset generated in {args.output}/mock_dataset")
