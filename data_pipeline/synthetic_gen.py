"""
BharatDoc-VLM: Synthetic Document Generation
=============================================

Generates synthetic Indian documents using Jinja2 HTML templates → PDF → PNG.
Supports Aadhaar cards, LIC policies, and invoices with randomised fields,
fonts, layouts, and bilingual (Hindi/English) content.

Falls back to Pillow-based rendering if wkhtmltopdf is not installed.
"""

from __future__ import annotations

import logging
import random
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from jinja2 import Template
from PIL import Image

logger = logging.getLogger(__name__)

# =============================================================
# Jinja2 HTML Templates
# =============================================================

AADHAAR_TEMPLATE = Template("""
<!DOCTYPE html>
<html>
<head><style>
  body { font-family: {{font}}; margin: 0; padding: 20px; background: #fff; }
  .card { width: 800px; height: 500px; border: 3px solid #006400; padding: 20px; position: relative; }
  .header { color: #333; font-size: 20px; text-align: center; margin-bottom: 10px; }
  .header-hi { color: #666; font-size: 16px; text-align: center; }
  .photo { width: 120px; height: 150px; border: 1px solid #ccc; float: left; margin: 20px; text-align: center; line-height: 150px; color: #999; }
  .details { margin-left: 170px; margin-top: 20px; }
  .field { margin: 8px 0; font-size: 16px; }
  .label { color: #666; font-size: 13px; }
  .aadhaar-num { font-size: 28px; font-weight: bold; letter-spacing: 3px; margin-top: 20px; }
</style></head>
<body><div class="card">
  <div class="header">भारत सरकार / Government of India</div>
  <div class="header-hi">भारतीय विशिष्ट पहचान प्राधिकरण / Unique Identification Authority of India</div>
  <div class="photo">PHOTO</div>
  <div class="details">
    <div class="field"><span class="label">नाम / Name:</span> {{name_hindi}} / {{name}}</div>
    <div class="field"><span class="label">जन्म तिथि / DOB:</span> {{dob}}</div>
    <div class="field"><span class="label">लिंग / Gender:</span> {{gender}}</div>
    <div class="aadhaar-num">{{aadhaar_number}}</div>
    <div class="field" style="margin-top:15px"><span class="label">पता / Address:</span><br>{{address}}</div>
  </div>
</div></body></html>
""")

INVOICE_TEMPLATE = Template("""
<!DOCTYPE html>
<html>
<head><style>
  body { font-family: {{font}}; margin: 0; padding: 20px; }
  .invoice { width: 760px; border: 1px solid #333; padding: 20px; }
  h1 { text-align: center; color: #1a1a2e; border-bottom: 2px solid #16213e; }
  table { width: 100%; border-collapse: collapse; margin: 15px 0; }
  th { background: #16213e; color: white; padding: 8px; text-align: left; }
  td { border: 1px solid #ddd; padding: 8px; }
  .total-row { font-weight: bold; background: #f0f0f0; }
  .gst-info { font-size: 13px; color: #555; }
</style></head>
<body><div class="invoice">
  <h1>TAX INVOICE</h1>
  <p><strong>Invoice No:</strong> {{invoice_number}} | <strong>Date:</strong> {{date}}</p>
  <p><strong>Vendor:</strong> {{vendor}} <span class="gst-info">GSTIN: {{vendor_gstin}}</span></p>
  <p><strong>Buyer:</strong> {{buyer}} <span class="gst-info">GSTIN: {{buyer_gstin}}</span></p>
  <table>
    <tr><th>Description</th><th>HSN</th><th>Qty</th><th>Rate (₹)</th><th>Amount (₹)</th></tr>
    {% for item in items %}
    <tr><td>{{item.desc}}</td><td>{{item.hsn}}</td><td>{{item.qty}}</td><td>{{item.rate}}</td><td>{{item.amount}}</td></tr>
    {% endfor %}
    <tr class="total-row"><td colspan="4">Subtotal</td><td>₹{{subtotal}}</td></tr>
    <tr><td colspan="4">IGST @ 18%</td><td>₹{{tax}}</td></tr>
    <tr class="total-row"><td colspan="4">Grand Total</td><td>₹{{total}}</td></tr>
  </table>
  <p><strong>Amount in Words:</strong> {{amount_words}}</p>
</div></body></html>
""")

LIC_TEMPLATE = Template("""
<!DOCTYPE html>
<html>
<head><style>
  body { font-family: {{font}}; margin: 0; padding: 30px; }
  .policy { width: 760px; border: 3px solid #000080; padding: 30px; }
  h1 { color: #000080; text-align: center; font-size: 22px; }
  h2 { color: #333; text-align: center; font-size: 18px; border-bottom: 1px solid #000080; }
  .field-row { display: flex; margin: 10px 0; }
  .field-label { width: 250px; font-weight: bold; color: #444; }
  .field-value { flex: 1; }
</style></head>
<body><div class="policy">
  <h1>जीवन बीमा निगम / LIFE INSURANCE CORPORATION OF INDIA</h1>
  <h2>POLICY BOND / पॉलिसी बॉन्ड</h2>
  <div class="field-row"><div class="field-label">Policy Number:</div><div class="field-value">{{policy_number}}</div></div>
  <div class="field-row"><div class="field-label">Name of Assured:</div><div class="field-value">{{holder_name}}</div></div>
  <div class="field-row"><div class="field-label">Plan & Term:</div><div class="field-value">{{plan_name}} ({{plan_number}}) - {{term}} years</div></div>
  <div class="field-row"><div class="field-label">Sum Assured:</div><div class="field-value">₹{{sum_assured}}</div></div>
  <div class="field-row"><div class="field-label">Premium:</div><div class="field-value">₹{{premium}} ({{frequency}})</div></div>
  <div class="field-row"><div class="field-label">Commencement:</div><div class="field-value">{{commence_date}}</div></div>
  <div class="field-row"><div class="field-label">Maturity Date:</div><div class="field-value">{{maturity_date}}</div></div>
  <div class="field-row"><div class="field-label">Nominee:</div><div class="field-value">{{nominee}} ({{nominee_rel}})</div></div>
</div></body></html>
""")

FONTS = ["Arial, sans-serif", "Times New Roman, serif", "Georgia, serif", "Verdana, sans-serif"]


def _check_wkhtmltopdf() -> bool:
    """Check if wkhtmltopdf is available on the system."""
    try:
        subprocess.run(["wkhtmltopdf", "--version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def _html_to_image_wkhtmltopdf(html: str, output_path: Path) -> Image.Image:
    """Render HTML to image via wkhtmltopdf → wkhtmltoimage."""
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as f:
        f.write(html)
        html_path = f.name
    try:
        subprocess.run(
            ["wkhtmltoimage", "--quality", "90", html_path, str(output_path)],
            capture_output=True, check=True,
        )
        return Image.open(output_path)
    except Exception as e:
        logger.warning(f"wkhtmltoimage failed: {e}, falling back to Pillow")
        return _html_to_image_fallback(html, output_path)
    finally:
        Path(html_path).unlink(missing_ok=True)


def _html_to_image_fallback(html: str, output_path: Path) -> Image.Image:
    """Fallback: render a simple document image using Pillow when wkhtmltopdf unavailable."""
    from PIL import ImageDraw, ImageFont
    img = Image.new("RGB", (850, 600), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except (OSError, IOError):
        font = ImageFont.load_default()
    # Simple text rendering of the template content
    lines = [l.strip() for l in html.split("\n") if l.strip() and "<" not in l][:20]
    y = 20
    for line in lines:
        draw.text((20, y), line[:80], fill=(0, 0, 0), font=font)
        y += 22
    img.save(output_path)
    return img


def generate_aadhaar(output_path: Path, **overrides) -> dict:
    """Generate a synthetic Aadhaar card image with random fields."""
    from data_pipeline.collect import NAMES_EN, NAMES_HI, ADDRESSES
    data = {
        "font": random.choice(FONTS),
        "name": random.choice(NAMES_EN), "name_hindi": random.choice(NAMES_HI),
        "dob": f"{random.randint(1,28):02d}/{random.randint(1,12):02d}/{random.randint(1970,2005)}",
        "gender": random.choice(["MALE", "FEMALE"]),
        "aadhaar_number": f"{random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(1000,9999)}",
        "address": random.choice(ADDRESSES),
    }
    data.update(overrides)
    html = AADHAAR_TEMPLATE.render(**data)
    if _check_wkhtmltopdf():
        _html_to_image_wkhtmltopdf(html, output_path)
    else:
        _html_to_image_fallback(html, output_path)
    return data


def generate_invoice(output_path: Path, **overrides) -> dict:
    """Generate a synthetic GST invoice image."""
    items = []
    for _ in range(random.randint(2, 5)):
        qty = random.randint(1, 50)
        rate = random.randint(500, 50000)
        items.append({"desc": random.choice(["IT Services", "Cloud Hosting", "Consulting", "Support"]),
                       "hsn": str(random.randint(990000, 999999)), "qty": qty, "rate": rate, "amount": qty * rate})
    subtotal = sum(i["amount"] for i in items)
    tax = round(subtotal * 0.18)
    data = {
        "font": random.choice(FONTS), "invoice_number": f"INV-2024-{random.randint(1,9999):04d}",
        "date": f"{random.randint(1,28):02d}/{random.randint(1,12):02d}/2024",
        "vendor": f"{random.choice(['TCS', 'Infosys', 'Wipro', 'HCL'])} Ltd",
        "vendor_gstin": f"27AAPFU{random.randint(1000,9999)}F1ZV",
        "buyer": "Acme Corp", "buyer_gstin": f"29AABCI{random.randint(1000,9999)}F1ZE",
        "items": items, "subtotal": subtotal, "tax": tax, "total": subtotal + tax,
        "amount_words": "Amount in words placeholder",
    }
    data.update(overrides)
    html = INVOICE_TEMPLATE.render(**data)
    if _check_wkhtmltopdf():
        _html_to_image_wkhtmltopdf(html, output_path)
    else:
        _html_to_image_fallback(html, output_path)
    return data


def generate_lic_policy(output_path: Path, **overrides) -> dict:
    """Generate a synthetic LIC policy document image."""
    from data_pipeline.collect import NAMES_EN
    sa = random.randint(5, 50) * 100000
    data = {
        "font": random.choice(FONTS),
        "policy_number": str(random.randint(10000000, 99999999)),
        "holder_name": random.choice(NAMES_EN),
        "plan_name": random.choice(["Jeevan Anand", "Jeevan Labh", "New Endowment"]),
        "plan_number": str(random.choice([815, 936, 914])),
        "term": random.choice([15, 20, 25, 30]),
        "sum_assured": f"{sa:,}", "premium": f"{sa // 40:,}",
        "frequency": random.choice(["YEARLY", "HALF_YEARLY", "QUARTERLY"]),
        "commence_date": f"01/04/{random.randint(2015,2023)}",
        "maturity_date": f"01/04/{random.randint(2035,2060)}",
        "nominee": random.choice(NAMES_EN),
        "nominee_rel": random.choice(["Spouse", "Child", "Parent"]),
    }
    data.update(overrides)
    html = LIC_TEMPLATE.render(**data)
    if _check_wkhtmltopdf():
        _html_to_image_wkhtmltopdf(html, output_path)
    else:
        _html_to_image_fallback(html, output_path)
    return data


def generate_batch(output_dir: Path, count: int = 50) -> list[dict]:
    """Generate a batch of synthetic documents across all types."""
    output_dir.mkdir(parents=True, exist_ok=True)
    generators = [generate_aadhaar, generate_invoice, generate_lic_policy]
    results = []
    for i in range(count):
        gen = generators[i % len(generators)]
        doc_type = ["aadhaar", "invoice", "lic_policy"][i % 3]
        path = output_dir / f"synthetic_{doc_type}_{i:04d}.png"
        data = gen(path)
        data["doc_type"] = doc_type
        data["path"] = str(path)
        results.append(data)
    logger.info(f"Generated {count} synthetic documents in {output_dir}")
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate synthetic documents")
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--output", type=str, default="data/synthetic")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    generate_batch(Path(args.output), count=args.count)
    print(f"✅ Generated {args.count} synthetic documents")
