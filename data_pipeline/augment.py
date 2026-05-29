"""
BharatDoc-VLM: Data Augmentation
==================================

Post-rasterisation augmentation for document images.
Applies geometric and photometric transforms to increase training diversity.
"""

from __future__ import annotations

import logging
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger(__name__)


def random_rotation(image: Image.Image, max_angle: float = 5.0) -> Image.Image:
    """Small rotation to simulate slight document skew during scanning."""
    angle = random.uniform(-max_angle, max_angle)
    return image.rotate(angle, expand=False, fillcolor=(255, 255, 255))


def color_jitter(image: Image.Image, brightness: float = 0.2,
                 contrast: float = 0.2, saturation: float = 0.1) -> Image.Image:
    """Random brightness, contrast, and saturation adjustments."""
    result = image
    if random.random() < 0.5:
        factor = 1.0 + random.uniform(-brightness, brightness)
        result = ImageEnhance.Brightness(result).enhance(factor)
    if random.random() < 0.5:
        factor = 1.0 + random.uniform(-contrast, contrast)
        result = ImageEnhance.Contrast(result).enhance(factor)
    if random.random() < 0.5:
        factor = 1.0 + random.uniform(-saturation, saturation)
        result = ImageEnhance.Color(result).enhance(factor)
    return result


def random_crop(image: Image.Image, margin_pct: float = 0.05) -> Image.Image:
    """Simulate imperfect document cropping with small random margins."""
    w, h = image.size
    mx = int(w * margin_pct)
    my = int(h * margin_pct)
    left = random.randint(0, mx)
    top = random.randint(0, my)
    right = w - random.randint(0, mx)
    bottom = h - random.randint(0, my)
    cropped = image.crop((left, top, right, bottom))
    return cropped.resize((w, h), Image.LANCZOS)


def elastic_distortion(image: Image.Image, intensity: float = 0.3) -> Image.Image:
    """
    Simplified elastic distortion to simulate paper warping.
    Uses random displacement fields applied to the image.
    """
    img_array = np.array(image)
    h, w = img_array.shape[:2]
    # Generate smooth displacement fields
    grid_size = 10
    dx = np.random.randn(grid_size, grid_size) * intensity * 10
    dy = np.random.randn(grid_size, grid_size) * intensity * 10
    # Resize displacement to image size (creates smooth warping)
    from PIL import Image as PILImage
    dx_img = PILImage.fromarray(dx.astype(np.float32)).resize((w, h), PILImage.BILINEAR)
    dy_img = PILImage.fromarray(dy.astype(np.float32)).resize((w, h), PILImage.BILINEAR)
    dx_full = np.array(dx_img)
    dy_full = np.array(dy_img)
    # Apply displacement
    x_coords = np.clip(np.arange(w)[None, :] + dx_full, 0, w - 1).astype(np.int32)
    y_coords = np.clip(np.arange(h)[:, None] + dy_full, 0, h - 1).astype(np.int32)
    if img_array.ndim == 3:
        result = img_array[y_coords, x_coords, :]
    else:
        result = img_array[y_coords, x_coords]
    return Image.fromarray(result)


def gaussian_noise(image: Image.Image, std: float = 10.0) -> Image.Image:
    """Add Gaussian noise to simulate sensor noise."""
    img_array = np.array(image, dtype=np.float32)
    noise = np.random.normal(0, std, img_array.shape)
    result = np.clip(img_array + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(result)


def sharpen(image: Image.Image, factor: float = 1.5) -> Image.Image:
    """Apply sharpening filter."""
    return ImageEnhance.Sharpness(image).enhance(factor)


# Registry of all augmentation functions with their default probability
AUGMENTATIONS = [
    ("rotation", random_rotation, 0.5),
    ("color_jitter", color_jitter, 0.6),
    ("random_crop", random_crop, 0.3),
    ("elastic", elastic_distortion, 0.2),
    ("noise", gaussian_noise, 0.3),
    ("sharpen", sharpen, 0.2),
]


def augment_image(image: Image.Image, num_augments: int = 3) -> Image.Image:
    """Apply a random subset of augmentations to an image."""
    result = image.copy()
    selected = random.sample(AUGMENTATIONS, min(num_augments, len(AUGMENTATIONS)))
    applied = []
    for name, fn, prob in selected:
        if random.random() < prob:
            result = fn(result)
            applied.append(name)
    if applied:
        logger.debug(f"Applied augmentations: {', '.join(applied)}")
    return result


def augment_dataset(input_dir: Path, output_dir: Path,
                    augments_per_image: int = 3) -> int:
    """Augment all images in a directory, saving results to output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for img_path in sorted(input_dir.glob("*.png")):
        image = Image.open(img_path).convert("RGB")
        for j in range(augments_per_image):
            augmented = augment_image(image)
            out_path = output_dir / f"{img_path.stem}_aug{j:02d}.png"
            augmented.save(out_path)
            count += 1
    logger.info(f"Generated {count} augmented images in {output_dir}")
    return count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    img = Image.new("RGB", (800, 600), (255, 255, 255))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.text((100, 100), "Augmentation test document", fill=(0, 0, 0))
    result = augment_image(img)
    result.save("test_augmented.png")
    print("✅ Augmented image saved")
