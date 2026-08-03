"""
Image preprocessing utilities for mineral classification.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import numpy as np

try:
    import torch
    from torchvision import transforms
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

logger = logging.getLogger(__name__)

EFFICIENTNET_INPUT_SIZE = 380
CLIP_INPUT_SIZE = 224


@dataclass
class ImageQuality:
    """Image quality assessment result."""
    is_usable: bool
    issues: list[str]
    brightness: float
    contrast: float
    blur_score: float


def get_efficientnet_transforms(training: bool = False):
    """Get transforms for EfficientNet-B4."""
    if not HAS_TORCH:
        raise ImportError("torch required")
    
    if training:
        return transforms.Compose([
            transforms.RandomResizedCrop(EFFICIENTNET_INPUT_SIZE),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(15),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
    else:
        return transforms.Compose([
            transforms.Resize(EFFICIENTNET_INPUT_SIZE + 32),
            transforms.CenterCrop(EFFICIENTNET_INPUT_SIZE),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])


def load_image(source: Union[str, Path, "Image.Image"]) -> "Image.Image":
    """Load image from path or PIL Image."""
    if not HAS_PIL:
        raise ImportError("Pillow required")
    
    if isinstance(source, Image.Image):
        return source.convert("RGB")
    
    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    
    return Image.open(path).convert("RGB")


def assess_quality(image: "Image.Image") -> ImageQuality:
    """Assess image quality for mineral identification."""
    issues = []
    
    arr = np.array(image, dtype=np.float32) / 255.0
    
    # Brightness
    brightness = float(arr.mean())
    if brightness < 0.15:
        issues.append("Image is very dark")
    elif brightness > 0.9:
        issues.append("Image is overexposed")
    
    # Contrast
    contrast = float(arr.std())
    if contrast < 0.05:
        issues.append("Very low contrast — may be blurry or uniform")
    
    # Size check
    w, h = image.size
    if w < 100 or h < 100:
        issues.append(f"Image too small ({w}x{h}) — need at least 200x200")
    
    # Blur detection (Laplacian variance)
    gray = np.array(image.convert("L"), dtype=np.float32)
    laplacian = np.array([
        [0, 1, 0], [1, -4, 1], [0, 1, 0]
    ], dtype=np.float32)
    # Simple convolution
    from scipy.signal import convolve2d
    lap = convolve2d(gray, laplacian, mode="valid")
    blur_score = float(lap.var())
    if blur_score < 50:
        issues.append("Image appears blurry")
    
    is_usable = len(issues) == 0 or (len(issues) == 1 and "small" not in issues[0].lower())
    
    return ImageQuality(
        is_usable=is_usable,
        issues=issues,
        brightness=brightness,
        contrast=contrast,
        blur_score=blur_score,
    )
