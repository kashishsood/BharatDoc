"""
BharatDoc-VLM: Production VLM Extraction Engine
==================================================

PaddleOCR + Qwen2.5-VL + Donut — replaces Tesseract + regex.

Architecture:
  1. PaddleOCR  → OCR engine (Hindi + English, word-level bboxes)
  2. Qwen2.5-VL → primary VLM extractor (aadhaar, handwritten, generic)
  3. Donut      → structured form extractor (invoices, LIC policies)
  4. Rule-based → document type router (keyword matching on OCR text)

Every app imports DocumentExtractor from this module. Nothing else.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Optional

# Must be set before any paddle/paddleocr import.
# paddlepaddle 2.x uses protobuf-generated _pb2 files that are incompatible
# with the C++ protobuf runtime on some environments — force pure-Python impl.
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

import numpy as np
from PIL import Image

# Pre-import torch at module level so that transformers' lazy loader finds it
# already cached in sys.modules. On Windows, torch's shm.dll is only loaded
# on first import; if it's caught inside a try/except it raises OSError and
# falsely marks Qwen as unavailable.
try:
    import torch as _torch  # noqa: F401
except OSError:
    pass  # GPU/DLL issue — torch may still work for CPU ops after this

logger = logging.getLogger(__name__)

# ── Lazy model singletons (load once, reuse) ──────────────────────────────────

_paddle_ocr = None
_qwen_model = None
_qwen_processor = None
_donut_model = None
_donut_processor = None


def _has_torch_cuda() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


def get_paddle_ocr():
    """Load PaddleOCR once and reuse. Compatible with paddleocr 2.x API."""
    global _paddle_ocr
    if _paddle_ocr is None:
        from paddleocr import PaddleOCR
        _paddle_ocr = PaddleOCR(lang="en", use_angle_cls=True, show_log=False)
        logger.info("PaddleOCR loaded")
    return _paddle_ocr


def get_qwen_model():
    """Load Qwen2.5-VL once and reuse."""
    global _qwen_model, _qwen_processor
    if _qwen_model is None:
        import torch
        from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor

        model_id = os.getenv("QWEN_MODEL_ID", "Qwen/Qwen2.5-VL-3B-Instruct")
        logger.info(f"Loading Qwen2.5-VL: {model_id} ...")

        _qwen_processor = AutoProcessor.from_pretrained(
            model_id, trust_remote_code=True
        )
        _qwen_model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_id,
            torch_dtype=torch.float16 if torch.cuda.is_available()
                        else torch.float32,
            device_map="auto" if torch.cuda.is_available() else "cpu",
            trust_remote_code=True,
        )
        _qwen_model.eval()
        logger.info("Qwen2.5-VL loaded")
    return _qwen_model, _qwen_processor


def get_donut_model():
    """Load Donut once and reuse."""
    global _donut_model, _donut_processor
    if _donut_model is None:
        import torch
        from transformers import DonutProcessor, VisionEncoderDecoderModel

        model_id = "naver-clova-ix/donut-base-finetuned-docvqa"
        logger.info(f"Loading Donut: {model_id} ...")

        _donut_processor = DonutProcessor.from_pretrained(model_id)
        _donut_model = VisionEncoderDecoderModel.from_pretrained(model_id)
        _donut_model.eval()
        if torch.cuda.is_available():
            _donut_model = _donut_model.cuda()
        logger.info("Donut loaded")
    return _donut_model, _donut_processor


# ── PaddleOCR wrapper ─────────────────────────────────────────────────────────

def run_paddle_ocr(image_path: str) -> dict:
    """
    Run PaddleOCR on full image.
    Returns words, polygon bounding boxes, confidence, and full text.
    """
    assert isinstance(image_path, str), f"image_path must be str, got {type(image_path)}"
    assert os.path.exists(image_path), f"File does not exist: {image_path}"
    assert os.path.getsize(image_path) > 0, f"File is empty: {image_path}"

    ocr = get_paddle_ocr()
    result = ocr.ocr(image_path, cls=True)

    words = []
    lines = []

    if result and result[0]:
        for line in result[0]:
            box, (text, conf) = line
            x_coords = [p[0] for p in box]
            y_coords = [p[1] for p in box]
            x = int(min(x_coords))
            y = int(min(y_coords))
            w = int(max(x_coords) - x)
            h = int(max(y_coords) - y)

            word_entry = {
                "text": text,
                "conf": round(conf, 3),
                "x": x, "y": y, "w": w, "h": h,
                "box": box,
            }
            words.append(word_entry)
            lines.append(text)

    full_text = "\n".join(lines)
    return {
        "full_text": full_text,
        "words": words,
        "word_count": len(words),
        "engine": "paddleocr",
    }


# ── Qwen2.5-VL extractor ─────────────────────────────────────────────────────

QWEN_PROMPTS = {
    "aadhaar": (
        "You are reading an Aadhaar card image.\n"
        "Extract information and return ONLY a valid JSON object.\n\n"
        "STRICT RULES:\n"
        "- \"dob\" must contain ONLY the date in DD/MM/YYYY format.\n"
        "  Do NOT include gender, name, or any other word in this field.\n"
        "  WRONG: \"15/08/1990 Male\"\n"
        "  RIGHT: \"15/08/1990\"\n\n"
        "- \"gender\" must be ONLY one word: Male, Female, or Transgender.\n"
        "  Do NOT include date or any other word in this field.\n\n"
        "- \"aadhaar_number\" must be ONLY the 12-digit number.\n"
        "  Format: XXXX XXXX XXXX. Do NOT include any label text.\n\n"
        "- \"name\" must be ONLY the person's name.\n"
        "  Do NOT include \"Name:\", \"To:\", or any prefix.\n\n"
        "- \"address\" must be the COMPLETE address including PIN code.\n"
        "  Do NOT truncate.\n\n"
        "Return this exact JSON structure:\n"
        '{\n  "name": "person full name only",\n'
        '  "name_hindi": "name in Hindi script or null",\n'
        '  "dob": "DD/MM/YYYY only, no other text",\n'
        '  "gender": "Male or Female or Transgender only",\n'
        '  "aadhaar_number": "XXXX XXXX XXXX format",\n'
        '  "address": "complete address, do not truncate",\n'
        '  "address_hindi": "address in Hindi script or null",\n'
        '  "photo_present": true or false\n}\n'
        "Return ONLY the JSON. No explanation. No markdown. No code blocks."
    ),
    "lic_policy": (
        "Extract all information from this LIC policy document.\n"
        "Return ONLY valid JSON with these exact fields.\n\n"
        "STRICT RULES:\n"
        "- Each field must contain ONLY its own value. Do NOT merge two fields.\n"
        "- \"dob\" must contain ONLY the date. Do NOT include name or gender.\n"
        "- \"maturity_date\" and \"commencement_date\" must contain ONLY dates.\n"
        "- \"sum_assured\" and \"annual_premium\" must contain ONLY the amount.\n"
        "  Do NOT include labels like 'Sum Assured:' in the value.\n"
        "- \"policy_number\" must be ONLY the number, no label text.\n\n"
        '{\n  "policy_number": "policy number or null",\n'
        '  "holder_name": "policyholder name or null",\n'
        '  "plan_name": "plan/scheme name or null",\n'
        '  "sum_assured": "amount with currency only, no label",\n'
        '  "annual_premium": "amount with currency only, no label",\n'
        '  "commencement_date": "date only, no other text",\n'
        '  "maturity_date": "date only, no other text",\n'
        '  "nominee": "nominee name only",\n'
        '  "dob": "date only in DD/MM/YYYY, no other text",\n'
        '  "branch": "branch name or null",\n'
        '  "all_amounts": ["every currency amount visible in document"],\n'
        '  "all_dates": ["every date visible in document"]\n}\n'
        "Return ONLY the JSON object. No explanation. No markdown. No code blocks."
    ),
    "invoice": (
        "Extract all information from this invoice/bill.\n"
        "Return ONLY valid JSON with these exact fields.\n\n"
        "STRICT RULES:\n"
        "- Each field must contain ONLY its own value. Do NOT merge two fields.\n"
        "- \"invoice_number\" must be ONLY the number, no label text.\n"
        "- \"invoice_date\" must contain ONLY the date, no other text.\n"
        "- \"grand_total\", \"subtotal\", \"tax_amount\", \"cgst\", \"sgst\", \"igst\"\n"
        "  must each contain ONLY the numeric amount (with currency symbol if present).\n"
        "  Do NOT include the label name in the value.\n"
        "- \"vendor_gstin\" must be ONLY the GSTIN number, no label.\n\n"
        '{\n  "invoice_number": "number only, no label",\n'
        '  "invoice_date": "date only, no other text",\n'
        '  "vendor_name": "seller name only",\n'
        '  "vendor_gstin": "GSTIN number only, no label",\n'
        '  "buyer_name": "buyer name only",\n'
        '  "line_items": [{"description": "", "qty": "", "rate": "", "amount": ""}],\n'
        '  "subtotal": "amount only",\n'
        '  "tax_amount": "total tax amount only",\n'
        '  "grand_total": "final total amount only",\n'
        '  "cgst": "CGST amount only or null",\n'
        '  "sgst": "SGST amount only or null",\n'
        '  "igst": "IGST amount only or null"\n}\n'
        "Return ONLY the JSON object. No explanation. No markdown. No code blocks."
    ),
    "generic": (
        "Extract all visible information from this Indian document.\n"
        "Return ONLY valid JSON:\n"
        '{\n  "document_type": "your best guess at document type",\n'
        '  "all_names": ["every person or company name found"],\n'
        '  "all_dates": ["every date found"],\n'
        '  "all_amounts": ["every currency amount found"],\n'
        '  "all_ids": ["every ID, reference, or number found"],\n'
        '  "key_fields": {"every label": "its value"},\n'
        '  "language": "English/Hindi/Mixed"\n}\n'
        "Return ONLY the JSON object. No explanation."
    ),
}


def run_qwen_extraction(image_path: str, doc_type: str = "generic") -> dict:
    """Use Qwen2.5-VL to extract structured fields from document image."""
    import torch
    model, processor = get_qwen_model()
    prompt = QWEN_PROMPTS.get(doc_type, QWEN_PROMPTS["generic"])

    image = Image.open(image_path).convert("RGB")

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ],
        }
    ]

    text_input = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

    from qwen_vl_utils import process_vision_info
    image_inputs, video_inputs = process_vision_info(messages)

    inputs = processor(
        text=[text_input],
        images=image_inputs,
        videos=video_inputs,
        return_tensors="pt",
        padding=True,
    )

    device = next(model.parameters()).device
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=1024,
            do_sample=False,
            temperature=None,
            top_p=None,
        )

    generated = output_ids[0][inputs["input_ids"].shape[1]:]
    raw_text = processor.decode(generated, skip_special_tokens=True).strip()

    extracted = _parse_json_response(raw_text)
    extracted["_extraction_method"] = "qwen2.5-vl"
    extracted["_doc_type"] = doc_type
    return extracted


# ── Donut extractor ───────────────────────────────────────────────────────────

def run_donut_qa(image_path: str, question: str) -> str:
    """Use Donut to answer a specific question about a document."""
    import torch
    model, processor = get_donut_model()
    image = Image.open(image_path).convert("RGB")

    task_prompt = f"<s_docvqa><s_question>{question}</s_question><s_answer>"

    pixel_values = processor(image, return_tensors="pt").pixel_values
    if torch.cuda.is_available():
        pixel_values = pixel_values.cuda()

    decoder_input_ids = processor.tokenizer(
        task_prompt, add_special_tokens=False, return_tensors="pt"
    ).input_ids
    if torch.cuda.is_available():
        decoder_input_ids = decoder_input_ids.cuda()

    with torch.no_grad():
        outputs = model.generate(
            pixel_values,
            decoder_input_ids=decoder_input_ids,
            max_length=model.decoder.config.max_position_embeddings,
            early_stopping=True,
            pad_token_id=processor.tokenizer.pad_token_id,
            eos_token_id=processor.tokenizer.eos_token_id,
            use_cache=True,
            num_beams=1,
            bad_words_ids=[[processor.tokenizer.unk_token_id]],
            return_dict_in_generate=True,
        )

    seq = processor.batch_decode(outputs.sequences)[0]
    seq = seq.replace(processor.tokenizer.eos_token, "")
    seq = seq.replace(processor.tokenizer.pad_token, "")
    seq = re.sub(r"<.*?>", "", seq, count=1).strip()
    answer = seq.split("</s_answer>")[0].strip()
    return answer


DONUT_QUESTION_MAP = {
    "lic_policy": [
        "What is the policy number?",
        "What is the name of the policyholder?",
        "What is the sum assured?",
        "What is the annual premium?",
        "What is the maturity date?",
        "What is the commencement date?",
        "What is the name of the nominee?",
    ],
    "invoice": [
        "What is the invoice number?",
        "What is the invoice date?",
        "What is the total amount?",
        "What is the vendor name?",
        "What is the GSTIN?",
        "What is the subtotal?",
        "What is the tax amount?",
    ],
    "aadhaar": [
        "What is the name?",
        "What is the date of birth?",
        "What is the Aadhaar number?",
        "What is the gender?",
        "What is the address?",
    ],
}

DONUT_FIELD_MAP = {
    "lic_policy": [
        "policy_number", "holder_name", "sum_assured",
        "annual_premium", "maturity_date", "commencement_date", "nominee",
    ],
    "invoice": [
        "invoice_number", "invoice_date", "grand_total",
        "vendor_name", "gstin", "subtotal", "tax_amount",
    ],
    "aadhaar": [
        "name", "dob", "aadhaar_number", "gender", "address",
    ],
}


def run_donut_extraction(image_path: str, doc_type: str) -> dict:
    """Use Donut to extract all key fields for a known doc type."""
    questions = DONUT_QUESTION_MAP.get(doc_type, [])
    fields = DONUT_FIELD_MAP.get(doc_type, [])

    extracted = {}
    for question, field in zip(questions, fields):
        try:
            answer = run_donut_qa(image_path, question)
            extracted[field] = answer if answer and answer != "unanswerable" else None
        except Exception as e:
            extracted[field] = None
            logger.warning(f"Donut failed on '{question}': {e}")

    extracted["_extraction_method"] = "donut"
    extracted["_doc_type"] = doc_type
    return extracted


# ── Document Router ───────────────────────────────────────────────────────────

KEYWORD_RULES = {
    "aadhaar": [
        "aadhaar", "aadhar", "आधार", "uidai", "unique identification",
        "enrollment no", "वैध आधार",
    ],
    "lic_policy": [
        "life insurance", "lic", "policy number", "sum assured",
        "maturity", "premium", "nominee", "policyholder",
        "endowment", "jeevan", "जीवन बीमा",
    ],
    "invoice": [
        "invoice", "bill", "gst", "gstin", "tax invoice",
        "total amount", "subtotal", "cgst", "sgst", "igst",
        "buyer", "seller", "vendor",
    ],
    "handwritten_form": [
        "application form", "declaration", "undertaking",
    ],
}


def classify_document(ocr_result: dict) -> str:
    """Rule-based document classifier using PaddleOCR text."""
    text_lower = ocr_result["full_text"].lower()
    scores = {doc_type: 0 for doc_type in KEYWORD_RULES}
    for doc_type, keywords in KEYWORD_RULES.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                scores[doc_type] += 1
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "generic"
    return best


# ── Utilities ─────────────────────────────────────────────────────────────────

def _parse_json_response(text: str) -> dict:
    """Parse JSON from VLM text response, stripping markdown fences."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw_response": text, "parse_error": True}


def _save_temp_image(image: Image.Image, suffix: str = ".png") -> str:
    """Save a PIL image to a temp file and return its path."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    image.save(tmp, format="PNG")
    tmp.close()
    return tmp.name



# ── Master Extraction Class ──────────────────────────────────────────────────

class DocumentExtractor:
    """
    Master extractor. This is the ONLY class all apps should import.

    Routing logic:
      1. PaddleOCR first (fast, gives text + bounding boxes)
      2. OCR text → keyword-based doc type classification
      3. aadhaar / handwritten / unknown → Qwen2.5-VL
      4. lic_policy / invoice           → Donut (falls back to Qwen if >50% fields missing)
      5. If Qwen/Donut not installed    → raises RuntimeError (no silent fallback)
    """

    def __init__(self, use_qwen: bool = True, use_donut: bool = True):
        self.use_qwen = use_qwen
        self.use_donut = use_donut

        # Check model availability at startup — log clearly, not silently
        self._paddle_available = self._probe_import("paddleocr", "PaddleOCR",
            "PaddleOCR", "pip install paddlepaddle paddleocr")
        self._qwen_available = self._probe_import("transformers",
            "Qwen2_5_VLForConditionalGeneration",
            "Qwen2.5-VL", "pip install transformers>=4.45.0 qwen-vl-utils torch")
        self._donut_available = self._probe_import("transformers",
            "DonutProcessor",
            "Donut", "pip install transformers torch")

    @staticmethod
    def _probe_import(module: str, cls_name: str, label: str, install: str) -> bool:
        try:
            import importlib
            mod = importlib.import_module(module)
            getattr(mod, cls_name)
            logger.info(f"{label} imports OK")
            return True
        except (ImportError, AttributeError, OSError) as e:
            logger.error(f"{label} not available: {e}. Run: {install}")
            return False

    def extract(
        self,
        image_path: str,
        doc_type: Optional[str] = None,
        force_qwen: bool = False,
    ) -> dict:
        """
        Full pipeline: OCR -> classify -> VLM extract -> return.

        NEVER falls back to field_extractor. If Qwen/Donut are not
        installed, raises RuntimeError so the user knows to install them.
        """
        # Validate input file is real
        assert isinstance(image_path, str), f"image_path must be str, got {type(image_path)}"
        assert os.path.exists(image_path), f"File does not exist: {image_path}"
        assert os.path.getsize(image_path) > 0, f"File is empty: {image_path}"

        # Step 1: PaddleOCR on full image
        if self._paddle_available:
            logger.info(f"Running PaddleOCR on {image_path}")
            ocr_result = run_paddle_ocr(image_path)
        else:
            raise RuntimeError(
                "PaddleOCR is required but not installed. "
                "Run: pip install paddlepaddle paddleocr"
            )

        # Step 2: Classify if not provided
        if doc_type is None:
            doc_type = classify_document(ocr_result)
        logger.info(f"Document type: {doc_type}")

        # Step 3: Route to correct model — NO silent fallback
        if force_qwen or doc_type in ("aadhaar", "handwritten_form", "generic"):
            if not self._qwen_available:
                raise RuntimeError(
                    "Qwen2.5-VL is required but not installed. "
                    "Run: pip install transformers>=4.45.0 qwen-vl-utils torch"
                )
            logger.info("Routing to Qwen2.5-VL")
            extracted = run_qwen_extraction(image_path, doc_type)

        elif doc_type in ("lic_policy", "invoice") and self.use_donut:
            if not self._donut_available:
                raise RuntimeError(
                    "Donut is required but not installed. "
                    "Run: pip install transformers torch"
                )
            logger.info("Routing to Donut")
            extracted = run_donut_extraction(image_path, doc_type)
            # If Donut misses >50% fields, retry with Qwen
            user_fields = {k: v for k, v in extracted.items()
                           if not str(k).startswith("_")}
            none_count = sum(1 for v in user_fields.values() if v is None)
            total = len(user_fields)
            if total > 0 and none_count / total > 0.5:
                if self._qwen_available:
                    logger.info("Donut insufficient, retrying with Qwen")
                    extracted = run_qwen_extraction(image_path, doc_type)
        else:
            if not self._qwen_available:
                raise RuntimeError(
                    "Qwen2.5-VL is required but not installed. "
                    "Run: pip install transformers>=4.45.0 qwen-vl-utils torch"
                )
            extracted = run_qwen_extraction(image_path, doc_type)

        # Step 4: Attach OCR words for grounding visualiser
        extracted["_ocr_words"] = ocr_result["words"]
        extracted["_ocr_text"] = ocr_result["full_text"]
        extracted["_doc_type"] = doc_type

        return extracted

    def extract_from_pil(
        self,
        image: Image.Image,
        doc_type: Optional[str] = None,
    ) -> dict:
        """
        Convenience: extract from a PIL Image (saves to temp file internally).
        Used by Streamlit apps that have PIL images from file_uploader.
        """
        tmp_path = _save_temp_image(image)
        try:
            return self.extract(tmp_path, doc_type=doc_type)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def ask(self, image_path: str, question: str) -> str:
        """Ask a free-form question about any document via Donut."""
        if self._check_donut():
            return run_donut_qa(image_path, question)
        return "(Donut model not available)"
