"""
Image Preprocessing Pipeline for Mineral Identification
========================================================
Handles resize, normalize, EXIF correction, quality assessment.
CPU-optimized for Oracle Cloud free tier.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple, Union

import numpy as np
from PIL import Image, ImageOps
from PIL.ExifTags import Base as ExifBase

try:
    import torch
    from torchvision import transforms

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)
EFFICIENTNET_INPUT_SIZE = 380  # EfficientNet-B4
CLIP_INPUT_SIZE = 224  # CLIP ViT-B/32
MIN_QUALITY_SCORE = 0.3  # Below this, image is too blurry
MAX_FILE_SIZE_MB = 20


class ColorSpace(Enum):
    RGB = "rgb"
    HSV = "hsv"
    LAB = "lab"
    GRAYSCALE = "grayscale"


@dataclass
class QualityReport:
    """Result of image quality assessment."""
    blur_score: float          # 0.0 (sharp) to 1.0 (blurry)
    brightness: float          # 0.0 (dark) to 1.0 (bright)
    contrast: float            # 0.0 (low) to 1.0 (high)
    is_usable: bool            # Whether image meets minimum quality
    issues: list[str]          # Human-readable quality issues


def fix_exif_orientation(image: Image.Image) -> Image.Image:
    """
    Correct EXIF orientation tags so images display correctly.
    Photos from phones often have orientation metadata that viewers use
    but ML models ignore, causing wrong predictions.
    """
    try:
        return ImageOps.exif_transpose(image)
    except Exception as exc:
        logger.warning("EXIF orientation correction failed: %s", exc)
        return image


def load_image(
    source: Union[str, Path, bytes, io.BytesIO, Image.Image],
    mode: str = "RGB",
) -> Image.Image:
    """
    Load image from file path, bytes, or PIL Image.
    Always corrects EXIF orientation.
    """
    if isinstance(source, Image.Image):
        img = source
    elif isinstance(source, (str, Path)):
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")
        if path.stat().st_size > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise ValueError(f"Image exceeds {MAX_FILE_SIZE_MB}MB limit")
        img = Image.open(path)
    elif isinstance(source, (bytes, io.BytesIO)):
        img = Image.open(source if isinstance(source, io.BytesIO) else io.BytesIO(source))
    else:
        raise TypeError(f"Unsupported source type: {type(source)}")

    img = fix_exif_orientation(img)
    return img.convert(mode)


def assess_quality(image: Image.Image) -> QualityReport:
    """
    Assess image quality for mineral identification.
    Returns blur score, brightness, contrast, and usability verdict.
    """
    arr = np.array(image.convert("L"), dtype=np.float64) / 255.0
    issues: list[str] = []

    # ── Blur detection via Laplacian variance ──
    # Using a simple finite-difference Laplacian (no scipy dependency)
    laplacian = _laplacian(arr)
    lap_var = laplacian.var()
    # Map variance to 0-1 score (inverted: high variance = sharp)
    blur_score = max(0.0, min(1.0, 1.0 - lap_var / 0.05))
    if blur_score > 0.7:
        issues.append("Image is very blurry — mineral features may be indistinguishable")

    # ── Brightness ──
    brightness = float(arr.mean())
    if brightness < 0.15:
        issues.append("Image is very dark — features may be lost")
    elif brightness > 0.9:
        issues.append("Image is overexposed — color information may be washed out")

    # ── Contrast ──
    contrast = float(arr.std())
    if contrast < 0.05:
        issues.append("Very low contrast — may not distinguish mineral features")

    is_usable = blur_score < MIN_QUALITY_SCORE and 0.1 < brightness < 0.95 and contrast > 0.03

    return QualityReport(
        blur_score=round(blur_score, 4),
        brightness=round(brightness, 4),
        contrast=round(contrast, 4),
        is_usable=is_usable,
        issues=issues,
    )


def _laplacian(arr: np.ndarray) -> np.ndarray:
    """Compute discrete Laplacian for blur detection."""
    h, w = arr.shape
    result = np.zeros_like(arr)
    # Interior points: d²f/dx² + d²f/dy²
    result[1:-1, 1:-1] = (
        arr[0:-2, 1:-1] + arr[2:, 1:-1] + arr[1:-1, 0:-2] + arr[1:-1, 2:] - 4 * arr[1:-1, 1:-1]
    )
    return result


def resize_image(
    image: Image.Image,
    size: int = EFFICIENTNET_INPUT_SIZE,
    maintain_aspect: bool = True,
) -> Image.Image:
    """
    Resize image for model input.
    If maintain_aspect: resize shortest side to `size`, then center-crop.
    """
    if maintain_aspect:
        transforms_fn = transforms.Compose([
            transforms.Resize(size, interpolation=transforms.InterpolationMode.BICUBIC),
            transforms.CenterCrop(size),
        ]) if HAS_TORCH else None

        if transforms_fn:
            return transforms_fn(image)

        # Fallback without torch
        w, h = image.size
        ratio = size / min(w, h)
        new_w, new_h = int(w * ratio), int(h * ratio)
        image = image.resize((new_w, new_h), Image.BICUBIC)
        left = (new_w - size) // 2
        top = (new_h - size) // 2
        return image.crop((left, top, left + size, top + size))
    else:
        return image.resize((size, size), Image.BICUBIC)


def convert_color_space(image: Image.Image, target: ColorSpace) -> np.ndarray:
    """Convert PIL image to specified color space as numpy array."""
    arr = np.array(image)
    if target == ColorSpace.RGB:
        return arr
    elif target == ColorSpace.GRAYSCALE:
        return np.array(image.convert("L"))
    elif target == ColorSpace.HSV:
        from PIL import Image as PILImage
        return np.array(image.convert("HSV"))
    elif target == ColorSpace.LAB:
        from PIL import Image as PILImage
        return np.array(image.convert("LAB"))
    else:
        raise ValueError(f"Unsupported color space: {target}")


def get_efficientnet_transforms(training: bool = False):
    """
    Get standard EfficientNet-B4 preprocessing transforms.
    Returns training augmentation or inference preprocessing.
    """
    if not HAS_TORCH:
        raise ImportError("torch and torchvision required for transforms")

    if training:
        return transforms.Compose([
            transforms.RandomResizedCrop(EFFICIENTNET_INPUT_SIZE, scale=(0.7, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(),
            transforms.RandomRotation(30),
            transforms.ColorJitter(
                brightness=0.3, contrast=0.3, saturation=0.3, hue=0.1
            ),
            transforms.RandomGrayscale(p=0.05),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ])
    else:
        return transforms.Compose([
            transforms.Resize(EFFICIENTNET_INPUT_SIZE, interpolation=transforms.InterpolationMode.BICUBIC),
            transforms.CenterCrop(EFFICIENTNET_INPUT_SIZE),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ])


def get_clip_transforms():
    """Get standard CLIP preprocessing transforms."""
    if not HAS_TORCH:
        raise ImportError("torch and torchvision required for transforms")

    return transforms.Compose([
        transforms.Resize(CLIP_INPUT_SIZE, interpolation=transforms.InterpolationMode.BICUBIC),
        transforms.CenterCrop(CLIP_INPUT_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.48145466, 0.4578275, 0.40821073],
            std=[0.26862954, 0.26130258, 0.27577711],
        ),
    ])


def preprocess_for_model(
    image: Image.Image,
    model_type: str = "efficientnet",
    training: bool = False,
) -> "torch.Tensor":
    """
    Full preprocessing pipeline: load → fix orientation → assess quality → transform.
    Returns a tensor ready for model input.
    """
    if not HAS_TORCH:
        raise ImportError("torch required")

    # Quality check
    report = assess_quality(image)
    if not report.is_usable:
        logger.warning("Image quality issues: %s", report.issues)

    # Select transforms
    if model_type == "efficientnet":
        transform = get_efficientnet_transforms(training=training)
    elif model_type == "clip":
        transform = get_clip_transforms()
    else:
        raise ValueError(f"Unknown model type: {model_type}")

    return transform(image).unsqueeze(0)  # Add batch dimension
