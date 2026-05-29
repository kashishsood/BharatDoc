"""
BharatDoc-VLM: Context-Aware Field Extractor
===============================================

Spatially-aware, fuzzy-matching field extractor that works with any
OCR word list. Replaces brittle regex with label-alias matching
and spatial proximity heuristics.

Used by ALL apps and mock models to extract real values from OCR output.
"""

from __future__ import annotations

import re
import logging
from typing import Optional
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

# --- Label aliases: handles OCR errors and formatting variants ---
FIELD_ALIASES = {
    "name": ["name", "full name", "insured name", "policy holder",
             "naam", "नाम", "holder name", "member name"],
    "dob": ["date of birth", "dob", "birth date", "d.o.b",
            "janm tithi", "जन्म तिथि"],
    "policy_number": ["policy no", "policy number", "policy no.",
                      "policy #", "polisee", "pol. no"],
    "premium": ["premium", "annual premium", "premium amount",
                "pramium", "premia"],
    "amount": ["amount", "total", "total amount", "grand total",
               "subtotal", "net amount", "invoice total"],
    "date": ["date", "invoice date", "issue date", "dated",
             "tarikh", "दिनांक"],
    "address": ["address", "addr", "pata", "पता", "residence"],
    "phone": ["phone", "mobile", "contact", "tel", "phon", "mob"],
    "gender": ["gender", "sex", "लिंग"],
    "aadhaar_number": ["aadhaar", "uid", "aadhaar no", "aadhaar number"],
    "invoice_number": ["invoice no", "invoice number", "inv no", "bill no",
                       "invoice #", "bill number"],
    "vendor_name": ["vendor", "seller", "supplier", "from", "billed by",
                    "sold by", "vendor name"],
    "buyer_name": ["buyer", "bill to", "billed to", "customer", "buyer name"],
    "gstin": ["gstin", "gst no", "gst number", "gst in", "gst identification"],
    "plan_name": ["plan name", "plan", "scheme", "product name"],
    "sum_assured": ["sum assured", "sa", "sum insured"],
    "nominee": ["nominee", "nominee name", "beneficiary"],
    "maturity_date": ["maturity date", "maturity", "date of maturity"],
}


def fuzzy_match(word: str, candidates: list, threshold: float = 0.75) -> bool:
    """Check if word fuzzy-matches any candidate label."""
    word_lower = word.lower().strip()
    for c in candidates:
        ratio = SequenceMatcher(None, word_lower, c).ratio()
        if ratio >= threshold or c in word_lower:
            return True
    return False


def extract_value_after_label(words: list, label_aliases: list,
                              max_lookahead: int = 8) -> Optional[str]:
    """
    Spatially-aware extraction: find the label, then collect words
    on the same line or immediately after the colon/separator.
    Works even if OCR splits 'Name:' into 'Name' + ':'
    
    Args:
        words: List of dicts with keys: word, conf, x, y, w, h, block_num, line_num
        label_aliases: List of possible label strings for this field
        max_lookahead: How many tokens to look ahead after the label
    """
    for i, token in enumerate(words):
        word_text = token["word"]
        if fuzzy_match(word_text, label_aliases):
            # Collect next N tokens on the same or next line
            value_tokens = []
            label_line = token["line_num"]
            label_block = token["block_num"]

            for j in range(i + 1, min(i + max_lookahead + 1, len(words))):
                next_token = words[j]
                # Skip colons and separators
                if next_token["word"] in [":", "-", "|", ".", ",", ";"]:
                    continue
                # Stop if we've moved too far spatially (new section)
                if (next_token["block_num"] != label_block and
                        next_token["line_num"] > label_line + 2):
                    break
                # Stop if we hit another known label
                is_next_label = False
                for aliases in FIELD_ALIASES.values():
                    if fuzzy_match(next_token["word"], aliases, threshold=0.85):
                        is_next_label = True
                        break
                if is_next_label and len(value_tokens) > 0:
                    break
                value_tokens.append(next_token["word"])
                # Stop at end of line if we have a value
                if (next_token["line_num"] > label_line and
                        len(value_tokens) >= 2):
                    break

            if value_tokens:
                return " ".join(value_tokens).strip()
    return None


def extract_amounts(full_text: str) -> list:
    """Extract all currency amounts from text."""
    patterns = [
        r'₹\s*[\d,]+(?:\.\d{2})?',
        r'Rs\.?\s*[\d,]+(?:\.\d{2})?',
        r'INR\s*[\d,]+(?:\.\d{2})?',
        r'[\d,]+(?:\.\d{2})?\s*(?:/-|rupees|rs)',
    ]
    amounts = []
    for p in patterns:
        amounts.extend(re.findall(p, full_text, re.IGNORECASE))
    return amounts


def extract_dates(full_text: str) -> list:
    """Extract all dates from text in various formats."""
    patterns = [
        r'\d{2}[/-]\d{2}[/-]\d{4}',
        r'\d{4}[/-]\d{2}[/-]\d{2}',
        r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
        r'\s+\d{4}',
        r'(?:January|February|March|April|May|June|July|August|September'
        r'|October|November|December)\s+\d{1,2},?\s+\d{4}',
    ]
    dates = []
    for p in patterns:
        dates.extend(re.findall(p, full_text, re.IGNORECASE))
    return dates


def extract_aadhaar_number(full_text: str) -> Optional[str]:
    """Aadhaar is 12 digits, often written as XXXX XXXX XXXX."""
    # Pre-clean OCR digit substitutions near numbers
    cleaned = re.sub(r'(?<=\d)[Oo]', '0', full_text)
    cleaned = re.sub(r'[Oo](?=\d)', '0', cleaned)
    cleaned = re.sub(r'(?<=\d)[lI]', '1', cleaned)
    cleaned = re.sub(r'[lI](?=\d)', '1', cleaned)

    pattern = r'(?<!\d)(\d{4})\s*(\d{4})\s*(\d{4})(?!\d)'
    match = re.search(pattern, cleaned)
    if match:
        return f"{match.group(1)} {match.group(2)} {match.group(3)}"
    # Fallback: continuous 12-digit
    for d in re.findall(r'\d+', cleaned):
        if len(d) == 12:
            return f"{d[:4]} {d[4:8]} {d[8:12]}"
    return None


def run_extraction(ocr_result: dict, doc_type: str) -> dict:
    """
    Master extraction function. Takes OCR output dict and doc_type.
    Returns extracted fields dict. NEVER returns hardcoded values —
    all values come from the OCR result.

    Args:
        ocr_result: dict with keys "full_text", "words" (list of word dicts),
                    "image_shape" (tuple)
        doc_type: one of "aadhaar", "lic_policy", "invoice", or generic
    """
    words = ocr_result.get("words", [])
    full_text = ocr_result.get("full_text", "")
    extracted = {}

    if doc_type == "aadhaar":
        extracted["name"] = extract_value_after_label(
            words, FIELD_ALIASES["name"])
        extracted["dob"] = extract_value_after_label(
            words, FIELD_ALIASES["dob"])
        extracted["address"] = extract_value_after_label(
            words, FIELD_ALIASES["address"])
        extracted["gender"] = extract_value_after_label(
            words, FIELD_ALIASES["gender"])
        extracted["aadhaar_number"] = extract_aadhaar_number(full_text)

    elif doc_type == "lic_policy":
        extracted["policy_number"] = extract_value_after_label(
            words, FIELD_ALIASES["policy_number"])
        extracted["holder_name"] = extract_value_after_label(
            words, FIELD_ALIASES["name"])
        extracted["plan_name"] = extract_value_after_label(
            words, FIELD_ALIASES["plan_name"])
        extracted["premium"] = extract_value_after_label(
            words, FIELD_ALIASES["premium"])
        extracted["sum_assured"] = extract_value_after_label(
            words, FIELD_ALIASES["sum_assured"])
        extracted["nominee_name"] = extract_value_after_label(
            words, FIELD_ALIASES["nominee"])
        extracted["maturity_date"] = extract_value_after_label(
            words, FIELD_ALIASES["maturity_date"])
        extracted["amounts_found"] = extract_amounts(full_text)
        extracted["dates_found"] = extract_dates(full_text)

    elif doc_type == "invoice":
        extracted["invoice_number"] = extract_value_after_label(
            words, FIELD_ALIASES["invoice_number"])
        extracted["vendor_name"] = extract_value_after_label(
            words, FIELD_ALIASES["vendor_name"])
        extracted["buyer_name"] = extract_value_after_label(
            words, FIELD_ALIASES["buyer_name"])
        extracted["invoice_date"] = extract_value_after_label(
            words, FIELD_ALIASES["date"])
        extracted["gstin"] = extract_value_after_label(
            words, FIELD_ALIASES["gstin"])
        extracted["total"] = extract_value_after_label(
            words, FIELD_ALIASES["amount"])
        extracted["amounts_found"] = extract_amounts(full_text)
        extracted["dates_found"] = extract_dates(full_text)

    else:
        # Generic extraction for unknown doc types
        for field, aliases in FIELD_ALIASES.items():
            val = extract_value_after_label(words, aliases)
            if val:
                extracted[field] = val
        extracted["amounts_found"] = extract_amounts(full_text)
        extracted["dates_found"] = extract_dates(full_text)

    # Always include raw OCR for debugging
    extracted["_raw_ocr_text"] = full_text
    extracted["_word_count"] = len(words)

    logger.info(f"Field extraction ({doc_type}): "
                f"{sum(1 for v in extracted.values() if v and not str(v).startswith('_'))}"
                f" fields found from {len(words)} OCR words")
    return extracted
