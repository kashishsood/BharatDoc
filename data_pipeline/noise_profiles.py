"""
BharatDoc-VLM: Noise Profiles
==============================

Applies realistic scan/capture noise to document images, simulating
real-world conditions: photocopies, mobile scans, stamps, handwriting.

Each profile is composable and configurable via intensity parameters.
"""

from __future__ import annotations

import logging
import random
import math
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

logger = logging.getLogger(__name__)


def photocopy(image: Image.Image, intensity: float = 0.5) -> Image.Image:
    """
    Simulate photocopy degradation: gaussian noise + blur + contrast shift.
    
    Real photocopy artifacts:
    - Toner noise (salt-and-pepper)
    - Slight defocus from platen distance
    - Reduced contrast from toner density variations
    """
    img_array = np.array(image, dtype=np.float32)
    # Gaussian noise — intensity controls standard deviation
    noise = np.random.normal(0, 15 * intensity, img_array.shape)
    img_array = np.clip(img_array + noise, 0, 255).astype(np.uint8)
    result = Image.fromarray(img_array)
    # Slight blur to simulate defocus
    if intensity > 0.3:
        result = result.filter(ImageFilter.GaussianBlur(radius=0.5 + intensity))
    # Reduce contrast (photocopies lose dynamic range)
    enhancer = ImageEnhance.Contrast(result)
    result = enhancer.enhance(1.0 - 0.3 * intensity)
    return result


def mobile_scan(image: Image.Image, intensity: float = 0.5) -> Image.Image:
    """
    Simulate mobile phone camera capture: perspective warp + motion blur + vignette.
    
    Mobile scan artifacts:
    - Perspective distortion from non-perpendicular capture angle
    - Motion blur from hand shake
    - Vignetting from lens optics
    """
    w, h = image.size
    # Perspective warp — shift corners slightly
    offset = int(20 * intensity)
    coeffs = _find_perspective_coeffs(
        [(0, 0), (w, 0), (w, h), (0, h)],
        [(random.randint(0, offset), random.randint(0, offset)),
         (w - random.randint(0, offset), random.randint(0, offset)),
         (w - random.randint(0, offset), h - random.randint(0, offset)),
         (random.randint(0, offset), h - random.randint(0, offset))],
    )
    if coeffs is not None:
        result = image.transform((w, h), Image.PERSPECTIVE, coeffs, Image.BICUBIC)
    else:
        result = image.copy()
    # Motion blur (horizontal)
    if intensity > 0.3:
        result = result.filter(ImageFilter.GaussianBlur(radius=1.0 * intensity))
    # Vignette effect
    result = _apply_vignette(result, intensity * 0.4)
    return result


def stamp_overlay(image: Image.Image, text: str = "VERIFIED",
                  color: tuple = (200, 0, 0), intensity: float = 0.5) -> Image.Image:
    """
    Add a semi-transparent stamp overlay (common on verified Indian documents).
    Stamps are circular with text, in red or blue, rotated at random angle.
    """
    result = image.copy()
    overlay = Image.new("RGBA", result.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    # Stamp position and size
    cx = random.randint(result.width // 3, 2 * result.width // 3)
    cy = random.randint(result.height // 3, 2 * result.height // 3)
    radius = random.randint(60, 100)
    alpha = int(80 * intensity)
    stamp_color = (*color, alpha)
    # Draw circle
    draw.ellipse([(cx - radius, cy - radius), (cx + radius, cy + radius)],
                 outline=stamp_color, width=3)
    # Draw text in center
    try:
        from PIL import ImageFont
        font = ImageFont.truetype("arial.ttf", 16)
    except (OSError, IOError):
        font = ImageFont.load_default() if hasattr(ImageFont, 'load_default') else None
    if font:
        draw.text((cx - 30, cy - 8), text, fill=stamp_color, font=font)
    # Composite
    result = result.convert("RGBA")
    result = Image.alpha_composite(result, overlay)
    return result.convert("RGB")


def handwriting_overlay(image: Image.Image, text: Optional[str] = None,
                        intensity: float = 0.5) -> Image.Image:
    """
    Add a cursive handwriting-style text layer at a random position.
    Simulates annotations, signatures, or corrections on documents.
    """
    result = image.copy()
    draw = ImageDraw.Draw(result)
    if text is None:
        text = random.choice(["Approved", "Verified ✓", "Signature", "OK", "Received",
                              "मंजूर", "सत्यापित", "प्राप्त"])
    x = random.randint(20, max(21, result.width - 200))
    y = random.randint(20, max(21, result.height - 50))
    # Simulate handwriting with slightly irregular placement
    try:
        from PIL import ImageFont
        font = ImageFont.truetype("arial.ttf", random.randint(18, 28))
    except (OSError, IOError):
        font = ImageFont.load_default() if hasattr(ImageFont, 'load_default') else None
    color = (random.randint(0, 50), random.randint(0, 50), random.randint(100, 200))
    if font:
        draw.text((x, y), text, fill=color, font=font)
    return result


def apply_noise_profile(image: Image.Image, profile: str = "photocopy",
                        intensity: float = 0.5) -> Image.Image:
    """Apply a named noise profile to an image."""
    profiles = {
        "photocopy": photocopy,
        "mobile_scan": mobile_scan,
        "stamp_overlay": stamp_overlay,
        "handwriting_overlay": handwriting_overlay,
    }
    if profile not in profiles:
        raise ValueError(f"Unknown profile: {profile}. Choose from: {list(profiles.keys())}")
    return profiles[profile](image, intensity=intensity)


def apply_random_noise(image: Image.Image, max_profiles: int = 2) -> Image.Image:
    """Apply 1-N random noise profiles for diverse augmentation."""
    profiles = ["photocopy", "mobile_scan", "stamp_overlay", "handwriting_overlay"]
    n = random.randint(1, min(max_profiles, len(profiles)))
    selected = random.sample(profiles, n)
    result = image
    for profile in selected:
        intensity = random.uniform(0.2, 0.7)
        result = apply_noise_profile(result, profile, intensity)
    return result


def _find_perspective_coeffs(source_pts, target_pts):
    """Compute perspective transform coefficients."""
    try:
        matrix = []
        for s, t in zip(source_pts, target_pts):
            matrix.append([t[0], t[1], 1, 0, 0, 0, -s[0]*t[0], -s[0]*t[1]])
            matrix.append([0, 0, 0, t[0], t[1], 1, -s[1]*t[0], -s[1]*t[1]])
        A = np.matrix(matrix, dtype=np.float64)
        B = np.array([s for pair in source_pts for s in pair]).reshape(8)
        res = np.dot(np.linalg.inv(A.T * A) * A.T, B)
        return np.array(res).reshape(8).tolist()
    except Exception:
        return None


def _apply_vignette(image: Image.Image, strength: float = 0.3) -> Image.Image:
    """Apply vignette darkening at edges."""
    w, h = image.size
    img_array = np.array(image, dtype=np.float32)
    Y, X = np.ogrid[:h, :w]
    cx, cy = w / 2, h / 2
    dist = np.sqrt((X - cx)**2 + (Y - cy)**2)
    max_dist = math.sqrt(cx**2 + cy**2)
    vignette = 1.0 - strength * (dist / max_dist)**2
    vignette = np.clip(vignette, 0, 1)
    for c in range(min(3, img_array.shape[2] if img_array.ndim == 3 else 1)):
        if img_array.ndim == 3:
            img_array[:, :, c] *= vignette
    return Image.fromarray(np.clip(img_array, 0, 255).astype(np.uint8))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    img = Image.new("RGB", (800, 600), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((100, 100), "Test Document Content", fill=(0, 0, 0))
    for profile in ["photocopy", "mobile_scan", "stamp_overlay", "handwriting_overlay"]:
        result = apply_noise_profile(img, profile, intensity=0.5)
        result.save(f"test_noise_{profile}.png")
        print(f"✅ Generated {profile} noise sample")
