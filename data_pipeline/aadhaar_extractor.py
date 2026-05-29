"""
BharatDoc-VLM: Rule-Based Aadhaar Field Extractor
====================================================

Regex + heuristic extraction layer that runs AFTER OCR to pull structured
fields from raw text. Works regardless of which OCR engine produced the text.

This is the practical fix: instead of relying on a trained model, we use
domain knowledge about Aadhaar card layout to extract fields reliably.

Fields extracted:
- aadhaar_number: XXXX XXXX XXXX (12 digits)
- date_of_birth: DD/MM/YYYY
- gender: MALE/FEMALE/पुरुष/महिला
- name: heuristic from OCR lines (first non-header proper-case line)
- vid: 16-digit Virtual ID (if present)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class AadhaarExtraction:
    """Structured Aadhaar extraction result with per-field confidence."""
    aadhaar_number: Optional[str] = None
    aadhaar_confidence: float = 0.0
    name: Optional[str] = None
    name_confidence: float = 0.0
    date_of_birth: Optional[str] = None
    dob_confidence: float = 0.0
    gender: Optional[str] = None
    gender_confidence: float = 0.0
    address: Optional[str] = None
    address_confidence: float = 0.0
    vid: Optional[str] = None
    vid_confidence: float = 0.0
    raw_text: str = ""
    warnings: list[str] = field(default_factory=list)
    overall_confidence: float = 0.0

    def to_dict(self) -> dict:
        """Return structured JSON with confidence scores and warnings."""
        fields = {}
        for fname in ["aadhaar_number", "name", "date_of_birth", "gender", "address", "vid"]:
            value = getattr(self, fname)
            conf_key = f"{fname.split('_')[0]}_confidence" if fname != "date_of_birth" else "dob_confidence"
            if fname == "aadhaar_number":
                conf_key = "aadhaar_confidence"
            elif fname == "name":
                conf_key = "name_confidence"
            elif fname == "address":
                conf_key = "address_confidence"
            elif fname == "vid":
                conf_key = "vid_confidence"
            elif fname == "gender":
                conf_key = "gender_confidence"
            
            conf = getattr(self, conf_key, 0.0)
            if value is not None:
                fields[fname] = {"value": value, "confidence": round(conf, 3)}
            else:
                fields[fname] = {"value": None, "confidence": 0.0}

        extracted_count = sum(1 for f in fields.values() if f["value"] is not None)
        total_fields = len(fields)

        return {
            "doc_type": "aadhaar",
            "fields": fields,
            "overall_confidence": round(self.overall_confidence, 3),
            "extraction_completeness": f"{extracted_count}/{total_fields}",
            "warnings": self.warnings,
        }


# --- Regex patterns ---

# Aadhaar: 12 digits, optionally separated by spaces
AADHAAR_PATTERN = re.compile(
    r'(?<!\d)'                  # Not preceded by digit
    r'(\d{4})\s*(\d{4})\s*(\d{4})'  # 3 groups of 4 digits
    r'(?!\d)',                  # Not followed by digit
)

# Date: DD/MM/YYYY or DD-MM-YYYY
DATE_PATTERN = re.compile(
    r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})'
)

# Gender keywords (English + Hindi)
# Note: \b doesn't work with Devanagari, so we use (?:^|\s) and (?:$|\s) instead
GENDER_PATTERNS = {
    "MALE": re.compile(r'(?:^|\s|:)(MALE|Male|male|पुरुष)(?:$|\s|,)', re.UNICODE),
    "FEMALE": re.compile(r'(?:^|\s|:)(FEMALE|Female|female|महिला|स्त्री)(?:$|\s|,)', re.UNICODE),
}

# VID: 16 digits
VID_PATTERN = re.compile(r'(?<!\d)(\d{4}\s?\d{4}\s?\d{4}\s?\d{4})(?!\d)')

# Skip lines that are headers/labels (not names)
HEADER_KEYWORDS = {
    "government", "india", "uidai", "unique", "identification", "authority",
    "aadhaar", "enrollment", "enrolment", "dob", "date", "birth",
    "address", "male", "female", "vid", "to", "of", "the",
    "भारत", "सरकार", "आधार", "जन्म", "पता",
}


def _preclean_ocr_text(text: str) -> str:
    """
    Pre-clean common OCR letter→digit substitutions BEFORE regex matching.
    
    Only applied in digit-heavy contexts (near Aadhaar/VID numbers).
    We clean the entire text since Aadhaar cards are digit-heavy documents.
    """
    # Replace common OCR confusions in digit contexts
    # O→0, o→0 only when adjacent to digits
    text = re.sub(r'(?<=\d)[Oo]', '0', text)
    text = re.sub(r'[Oo](?=\d)', '0', text)
    # l→1, I→1 only when adjacent to digits  
    text = re.sub(r'(?<=\d)[lI]', '1', text)
    text = re.sub(r'[lI](?=\d)', '1', text)
    return text


def extract_aadhaar_fields(ocr_text: str) -> AadhaarExtraction:
    """
    Extract structured Aadhaar fields from raw OCR text.
    
    Uses regex for numbers/dates and heuristics for name extraction.
    Returns partial results with warnings for missing fields.
    """
    result = AadhaarExtraction(raw_text=ocr_text)
    lines = [line.strip() for line in ocr_text.split("\n") if line.strip()]
    
    # Pre-clean OCR digit substitutions before regex matching
    cleaned_text = _preclean_ocr_text(ocr_text)
    
    logger.debug(f"Aadhaar extractor: processing {len(lines)} lines")

    # --- Extract Aadhaar Number ---
    aadhaar_match = AADHAAR_PATTERN.search(cleaned_text)
    if aadhaar_match:
        # Format as XXXX XXXX XXXX
        result.aadhaar_number = f"{aadhaar_match.group(1)} {aadhaar_match.group(2)} {aadhaar_match.group(3)}"
        # OCR correction: common substitutions
        result.aadhaar_number = _fix_ocr_digits(result.aadhaar_number)
        result.aadhaar_confidence = 0.90
        logger.debug(f"  Aadhaar number: {result.aadhaar_number}")
    else:
        # Try harder: look for any 12-digit sequence in cleaned text
        digits_only = re.findall(r'\d+', cleaned_text)
        for d in digits_only:
            if len(d) == 12:
                result.aadhaar_number = f"{d[:4]} {d[4:8]} {d[8:12]}"
                result.aadhaar_confidence = 0.70
                result.warnings.append("Aadhaar number found as continuous digits (lower confidence)")
                break
        if not result.aadhaar_number:
            result.warnings.append("Aadhaar number not found in OCR text")

    # --- Extract Date of Birth ---
    date_candidates = DATE_PATTERN.findall(ocr_text)
    if date_candidates:
        # Pick the first valid date (DOB is usually near "DOB" or "Date of Birth" label)
        for dd, mm, yyyy in date_candidates:
            dd, mm = int(dd), int(mm)
            yyyy_int = int(yyyy)
            if 1 <= dd <= 31 and 1 <= mm <= 12 and 1900 <= yyyy_int <= 2025:
                result.date_of_birth = f"{dd:02d}/{mm:02d}/{yyyy}"
                result.dob_confidence = 0.88
                logger.debug(f"  DOB: {result.date_of_birth}")
                break
        if not result.date_of_birth:
            result.warnings.append("Date found but failed validation")
    else:
        result.warnings.append("Date of birth not found in OCR text")

    # --- Extract Gender ---
    for gender_label, pattern in GENDER_PATTERNS.items():
        if pattern.search(ocr_text):
            result.gender = gender_label
            result.gender_confidence = 0.95
            logger.debug(f"  Gender: {result.gender}")
            break
    if not result.gender:
        result.warnings.append("Gender not detected")

    # --- Extract Name (heuristic) ---
    result.name, result.name_confidence = _extract_name(lines)
    if result.name:
        logger.debug(f"  Name: {result.name}")
    else:
        result.warnings.append("Name extraction failed — no suitable text line found")

    # --- Extract VID ---
    vid_match = VID_PATTERN.search(ocr_text)
    if vid_match:
        vid_raw = vid_match.group(1).replace(" ", "")
        if len(vid_raw) == 16 and vid_raw != (result.aadhaar_number or "").replace(" ", ""):
            result.vid = f"{vid_raw[:4]} {vid_raw[4:8]} {vid_raw[8:12]} {vid_raw[12:16]}"
            result.vid_confidence = 0.80

    # --- Extract Address (lines after "Address" keyword) ---
    result.address, result.address_confidence = _extract_address(lines)

    # --- Overall confidence ---
    confidences = [
        result.aadhaar_confidence,
        result.dob_confidence,
        result.gender_confidence,
        result.name_confidence,
    ]
    non_zero = [c for c in confidences if c > 0]
    result.overall_confidence = sum(non_zero) / len(non_zero) if non_zero else 0.0

    logger.info(f"Aadhaar extraction: {len(non_zero)}/4 fields found, "
                f"overall confidence={result.overall_confidence:.2f}")
    return result


def _fix_ocr_digits(text: str) -> str:
    """Fix common OCR digit substitutions."""
    text = text.replace("O", "0").replace("o", "0")
    text = text.replace("l", "1").replace("I", "1")
    text = text.replace("S", "5").replace("B", "8")
    return text


def _extract_name(lines: list[str]) -> tuple[Optional[str], float]:
    """
    Extract name using heuristic: first proper-case line that isn't a header.
    
    Aadhaar card layout: header lines → name → DOB/gender → number → address
    Name is typically the first line with 2-4 capitalized words that aren't keywords.
    Also handles labeled lines like "Name: Rajesh Kumar Sharma".
    """
    # Pass 1: Try labeled lines first (higher confidence)
    for line in lines:
        label_match = re.match(r'^(?:Name|नाम)\s*[:\-]\s*(.+)$', line, re.IGNORECASE)
        if label_match:
            name_part = label_match.group(1).strip()
            name_words = [w for w in name_part.split() if re.match(r'^[A-Za-z\u0900-\u097F]+$', w)]
            if len(name_words) >= 1:
                return " ".join(name_words), 0.88

    # Pass 2: Unlabeled name line (first proper-case non-header line)
    for line in lines:
        words = line.split()
        if len(words) < 2 or len(words) > 6:
            continue
        
        # Skip lines with header keywords
        line_lower = line.lower()
        if any(kw in line_lower for kw in HEADER_KEYWORDS):
            continue
        
        # Skip lines with digits (dates, numbers)
        if any(c.isdigit() for c in line):
            continue
        
        # Skip lines with special characters
        if re.search(r'[:/\-@#]', line):
            continue
        
        # Check if it looks like a name (proper case or all caps, alphabetic)
        alpha_words = [w for w in words if re.match(r'^[A-Za-z\u0900-\u097F]+$', w)]
        if len(alpha_words) >= 2:
            name = " ".join(alpha_words)
            # Higher confidence if it's proper case
            if all(w[0].isupper() for w in alpha_words if w[0].isascii()):
                return name, 0.80
            return name, 0.60
    
    return None, 0.0


def _extract_address(lines: list[str]) -> tuple[Optional[str], float]:
    """Extract address from lines following 'Address' keyword."""
    address_started = False
    address_lines = []
    
    for line in lines:
        if re.search(r'\b(address|पता)\b', line, re.IGNORECASE):
            # Start collecting from this line (remove the label)
            after_label = re.sub(r'^.*?(address|पता)[:\s]*', '', line, flags=re.IGNORECASE).strip()
            if after_label:
                address_lines.append(after_label)
            address_started = True
            continue
        
        if address_started:
            # Stop at next field label or empty-ish line
            if re.search(r'\b(aadhaar|vid|dob|date|gender|male|female)\b', line, re.IGNORECASE):
                break
            if len(line) < 3:
                break
            address_lines.append(line)
            if len(address_lines) >= 3:  # Cap address to 3 lines
                break
    
    if address_lines:
        return ", ".join(address_lines), 0.70
    return None, 0.0


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    # Test with realistic OCR output
    sample_text = """Government of India
Unique Identification Authority
Name: Rajesh Kumar Sharma
DOB: 15/08/1990
Male
9234 5678 9012
Address: H.No 45, Sector 12
Dwarka, New Delhi - 110075
VID: 1234 5678 9012 3456"""

    result = extract_aadhaar_fields(sample_text)
    import json
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
