"""
BharatDoc-VLM: OCR Parsing
===========================

Tesseract OCR with OpenCV bounding box extraction.
Returns structured OCR output with word-level boxes for layout-aware models.

Preprocessing pipeline:
1. Upscale small images (Tesseract needs ~300 DPI)
2. Grayscale conversion
3. Deskew rotated scans
4. Adaptive thresholding for uneven lighting
5. Denoising

NEVER crops or resizes below original dimensions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class OCRWord:
    """Single word detected by OCR with bounding box."""
    text: str
    confidence: float
    x: int
    y: int
    width: int
    height: int
    block_num: int = 0
    line_num: int = 0
    word_num: int = 0


@dataclass
class OCRResult:
    """Complete OCR result for a document image."""
    words: list[OCRWord] = field(default_factory=list)
    full_text: str = ""
    image_width: int = 0
    image_height: int = 0
    language: str = "eng"
    ocr_image_shape: tuple = (0, 0)

    @property
    def num_words(self) -> int:
        return len(self.words)

    @property
    def avg_confidence(self) -> float:
        if not self.words:
            return 0.0
        return sum(w.confidence for w in self.words) / len(self.words)

    def to_dict(self) -> dict:
        return {
            "full_text": self.full_text,
            "num_words": self.num_words,
            "avg_confidence": round(self.avg_confidence, 2),
            "image_size": [self.image_width, self.image_height],
            "words": [
                {"text": w.text, "confidence": round(w.confidence, 2),
                 "bbox": [w.x, w.y, w.width, w.height]}
                for w in self.words
            ],
        }

    def to_field_extractor_format(self) -> dict:
        """Convert to dict format expected by field_extractor.run_extraction()."""
        return {
            "full_text": self.full_text,
            "words": [
                {
                    "word": w.text,
                    "conf": int(w.confidence * 100),
                    "x": w.x, "y": w.y,
                    "w": w.width, "h": w.height,
                    "block_num": w.block_num,
                    "line_num": w.line_num,
                }
                for w in self.words
            ],
            "image_shape": self.ocr_image_shape,
        }


def preprocess_for_ocr(image: Image.Image) -> np.ndarray:
    """
    Preprocess image to maximise Tesseract accuracy.
    DO NOT crop or resize below original dimensions.
    """
    try:
        import cv2
    except ImportError:
        return np.array(image.convert("L"))

    img = np.array(image)
    if len(img.shape) == 2:
        gray = img
    else:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    h, w = gray.shape[:2]

    # Step 1: Upscale if image is small
    if w < 1000:
        scale = 1000 / w
        gray = cv2.resize(gray, None, fx=scale, fy=scale,
                          interpolation=cv2.INTER_CUBIC)
        logger.debug(f"Upscaled image from {w}x{h} to {gray.shape[1]}x{gray.shape[0]}")

    # Step 2: Deskew
    try:
        coords = np.column_stack(np.where(gray < 200))
        if len(coords) > 100:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            if abs(angle) > 0.5 and abs(angle) < 15:
                (dh, dw) = gray.shape[:2]
                center = (dw // 2, dh // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                gray = cv2.warpAffine(gray, M, (dw, dh),
                                      flags=cv2.INTER_CUBIC,
                                      borderMode=cv2.BORDER_REPLICATE)
                logger.debug(f"Deskewed by {angle:.1f} degrees")
    except Exception as e:
        logger.debug(f"Deskew skipped: {e}")

    # Step 3: Adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 10
    )

    # Step 4: Denoise
    denoised = cv2.fastNlMeansDenoising(thresh, h=10)

    return denoised


def ocr_image(image: Image.Image, lang: str = "eng+hin",
              use_mock: bool = False) -> OCRResult:
    """
    Run OCR on a document image.

    Args:
        image: PIL Image to OCR
        lang: Tesseract language string (eng+hin for bilingual)
        use_mock: DEPRECATED — kept for signature compatibility only.
                  Mock OCR is NEVER used; always attempts real OCR.
                  If real OCR is unavailable, raises RuntimeError.
    """
    # Always attempt real OCR — never fall back to static mock data.
    result = _try_real_ocr(image, lang)
    if result is not None:
        return result
    # PaddleOCR fallback (no Tesseract)
    result = _paddle_ocr(image, lang)
    if result is not None and result.num_words > 0:
        return result
    raise RuntimeError(
        "No OCR engine available. "
        "Install PaddleOCR: pip install paddlepaddle paddleocr"
    )


def _try_real_ocr(image: Image.Image, lang: str) -> Optional[OCRResult]:
    """Attempt real OCR silently - return None if not available."""
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return _tesseract_ocr(image, lang)
    except Exception:
        return None


def _tesseract_ocr(image: Image.Image, lang: str) -> OCRResult:
    """
    Real Tesseract OCR with optimised config for Indian documents.
    Preprocessing: upscale + deskew + threshold + denoise
    Config: PSM 3 (full auto), OEM 3 (LSTM), DPI 300
    """
    try:
        import pytesseract

        processed = preprocess_for_ocr(image)
        ocr_shape = processed.shape[:2]

        custom_config = (
            r'--oem 3 '
            r'--psm 3 '
            r'--dpi 300 '
            r'-c preserve_interword_spaces=1'
        )

        pil_processed = Image.fromarray(processed)
        data = pytesseract.image_to_data(pil_processed, lang=lang,
                                          output_type=pytesseract.Output.DICT,
                                          config=custom_config)
        words = []
        for i in range(len(data["text"])):
            text = data["text"][i].strip()
            conf = int(data["conf"][i])
            if text and conf > 30:
                words.append(OCRWord(
                    text=text, confidence=conf / 100.0,
                    x=data["left"][i], y=data["top"][i],
                    width=data["width"][i], height=data["height"][i],
                    block_num=data["block_num"][i],
                    line_num=data["line_num"][i],
                    word_num=data["word_num"][i],
                ))

        full_text = pytesseract.image_to_string(pil_processed, lang=lang,
                                                 config=custom_config)
        w, h = image.size

        logger.info(f"Tesseract OCR: {len(words)} words, lang={lang}, "
                     f"preprocessed={ocr_shape[1]}x{ocr_shape[0]}")
        return OCRResult(words=words, full_text=full_text.strip(),
                         image_width=w, image_height=h, language=lang,
                         ocr_image_shape=ocr_shape)

    except ImportError:
        logger.warning("pytesseract not installed, trying PaddleOCR...")
        return None
    except Exception as e:
        logger.error(f"Tesseract OCR failed: {e}, trying PaddleOCR...")
        return None


def _paddle_ocr(image: Image.Image, lang: str) -> OCRResult:
    """PaddleOCR fallback."""
    try:
        from paddleocr import PaddleOCR
        paddle_lang = "hi" if "hin" in lang else "en"
        ocr = PaddleOCR(use_angle_cls=True, lang=paddle_lang, show_log=False)
        img_array = np.array(image)
        paddle_result = ocr.ocr(img_array, cls=True)
        words = []
        text_lines = []
        if paddle_result and paddle_result[0]:
            for idx, line_info in enumerate(paddle_result[0]):
                box = line_info[0]
                text = line_info[1][0]
                conf = float(line_info[1][1])
                x_min = int(min(p[0] for p in box))
                y_min = int(min(p[1] for p in box))
                x_max = int(max(p[0] for p in box))
                y_max = int(max(p[1] for p in box))
                words.append(OCRWord(
                    text=text, confidence=conf,
                    x=x_min, y=y_min,
                    width=x_max - x_min, height=y_max - y_min,
                    block_num=1, line_num=idx + 1, word_num=1,
                ))
                text_lines.append(text)
        w, h = image.size
        full_text = "\n".join(text_lines)
        logger.info(f"PaddleOCR: {len(words)} lines detected, lang={paddle_lang}")
        return OCRResult(words=words, full_text=full_text,
                         image_width=w, image_height=h, language=lang,
                         ocr_image_shape=(h, w))
    except ImportError:
        logger.error("PaddleOCR not installed. Run: pip install paddlepaddle paddleocr")
        return None
    except Exception as e:
        logger.error(f"PaddleOCR failed: {e}")
        return None


def _mock_ocr(image: Image.Image) -> OCRResult:
    """Mock OCR returning realistic structured output for testing."""
    w, h = image.size
    mock_words = [
        OCRWord("Government", 0.95, 100, 20, 120, 25, 1, 1, 1),
        OCRWord("of", 0.98, 225, 20, 20, 25, 1, 1, 2),
        OCRWord("India", 0.96, 250, 20, 60, 25, 1, 1, 3),
        OCRWord("Name:", 0.92, 100, 80, 60, 20, 2, 1, 1),
        OCRWord("Rajesh", 0.88, 170, 80, 70, 20, 2, 1, 2),
        OCRWord("Kumar", 0.90, 245, 80, 65, 20, 2, 1, 3),
        OCRWord("DOB:", 0.94, 100, 110, 45, 20, 3, 1, 1),
        OCRWord("15/08/1990", 0.85, 150, 110, 100, 20, 3, 1, 2),
        OCRWord("Male", 0.93, 100, 140, 50, 20, 4, 1, 1),
        OCRWord("Aadhaar:", 0.91, 100, 170, 80, 20, 5, 1, 1),
        OCRWord("9234", 0.87, 190, 170, 45, 20, 5, 1, 2),
        OCRWord("5678", 0.89, 240, 170, 45, 20, 5, 1, 3),
        OCRWord("9012", 0.86, 290, 170, 45, 20, 5, 1, 4),
        OCRWord("Address:", 0.90, 100, 200, 80, 20, 6, 1, 1),
        OCRWord("H.No", 0.85, 190, 200, 50, 20, 6, 1, 2),
        OCRWord("45,", 0.88, 245, 200, 30, 20, 6, 1, 3),
        OCRWord("Sector", 0.87, 280, 200, 60, 20, 6, 1, 4),
        OCRWord("12", 0.90, 345, 200, 25, 20, 6, 1, 5),
    ]
    full_text = (
        "Government of India\n"
        "Name: Rajesh Kumar\n"
        "DOB: 15/08/1990\n"
        "Male\n"
        "Aadhaar: 9234 5678 9012\n"
        "Address: H.No 45, Sector 12"
    )
    return OCRResult(words=mock_words, full_text=full_text,
                     image_width=w, image_height=h, language="eng+hin",
                     ocr_image_shape=(h, w))


def extract_full_page(image_or_path, lang: str = "eng+hin") -> dict:
    """
    Run OCR on the COMPLETE image with word-level bounding boxes.
    Returns structured OCR dict.

    This is the main entry point for all apps.
    """
    if isinstance(image_or_path, (str, Path)):
        image = Image.open(image_or_path).convert("RGB")
    elif isinstance(image_or_path, np.ndarray):
        image = Image.fromarray(image_or_path)
    else:
        image = image_or_path

    ocr_result = ocr_image(image, lang=lang)
    return ocr_result.to_field_extractor_format()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    img = Image.new("RGB", (800, 600), (255, 255, 255))
    result = ocr_image(img, use_mock=True)
    print(f"OCR result: {result.num_words} words, avg confidence {result.avg_confidence:.2f}")
    print(f"Full text:\n{result.full_text}")
