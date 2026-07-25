"""
Mineral Dataset Management
==========================
Image loading, label encoding, train/val/test splits, augmentation pipeline.
Supports directory-based organization: data/minerals/{class_name}/*.jpg
"""

from __future__ import annotations

import json
import logging
import random
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

try:
    import torch
    from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
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

# ── 20 Mineral Classes ─────────────────────────────────────────────────────────
MINERAL_CLASSES: List[str] = [
    "gold",
    "copper",
    "pyrite",
    "chalcopyrite",
    "quartz",
    "feldspar",
    "mica",
    "calcite",
    "dolomite",
    "gypsum",
    "magnetite",
    "hematite",
    "limonite",
    "galena",
    "sphalerite",
    "fluorite",
    "tourmaline",
    "garnet",
    "olivine",
    "biotite",
]

# Minerals that are commonly confused (look-alikes)
LOOK_ALIKE_PAIRS: List[Tuple[str, str]] = [
    ("gold", "pyrite"),           # Fool's gold
    ("chalcopyrite", "pyrite"),   # Both metallic, brassy
    ("magnetite", "hematite"),    # Both iron oxides
    ("gypsum", "calcite"),        # Both light-colored, translucent
    ("galena", "sphalerite"),     # Both metallic sulfides
]

# Class to integer mapping
CLASS_TO_IDX: Dict[str, int] = {name: idx for idx, name in enumerate(MINERAL_CLASSES)}
IDX_TO_CLASS: Dict[int, str] = {idx: name for name, idx in CLASS_TO_IDX.items()}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}


@dataclass
class DatasetStats:
    """Statistics about the dataset."""
    total_images: int = 0
    class_counts: Dict[str, int] = field(default_factory=dict)
    split_counts: Dict[str, int] = field(default_factory=dict)
    class_weights: Dict[str, float] = field(default_factory=dict)


class MineralDataset(Dataset if HAS_TORCH else object):
    """
    PyTorch Dataset for mineral images.

    Expected directory structure:
        root/
            gold/
                img001.jpg
                img002.jpg
            copper/
                img001.jpg
            pyrite/
                ...
    """

    def __init__(
        self,
        root: Union[str, Path],
        transform: Optional[Callable] = None,
        split: Optional[str] = None,
        indices: Optional[List[int]] = None,
        cache_images: bool = False,
    ):
        if not HAS_TORCH:
            raise ImportError("torch required for MineralDataset")
        if not HAS_PIL:
            raise ImportError("Pillow required for MineralDataset")

        self.root = Path(root)
        self.transform = transform
        self.split = split
        self.cache_images = cache_images
        self._cache: Dict[int, Image.Image] = {}

        # Scan directory for images
        self.samples: List[Tuple[Path, int]] = []
        self._scan_directory()

        # Apply index filter for splits
        if indices is not None:
            self.samples = [self.samples[i] for i in indices if i < len(self.samples)]

        logger.info(
            "MineralDataset: %d samples, split=%s",
            len(self.samples),
            split or "all",
        )

    def _scan_directory(self):
        """Scan root directory for class-organized images."""
        for class_name in MINERAL_CLASSES:
            class_dir = self.root / class_name
            if not class_dir.is_dir():
                logger.warning("Class directory not found: %s", class_dir)
                continue

            class_idx = CLASS_TO_IDX[class_name]
            for img_path in sorted(class_dir.iterdir()):
                if img_path.suffix.lower() in IMAGE_EXTENSIONS:
                    self.samples.append((img_path, class_idx))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        img_path, label = self.samples[idx]

        # Load image
        if self.cache_images and idx in self._cache:
            image = self._cache[idx]
        else:
            image = Image.open(img_path).convert("RGB")
            if self.cache_images:
                self._cache[idx] = image

        # Apply transforms
        if self.transform:
            image = self.transform(image)

        return image, label

    def get_class_name(self, idx: int) -> str:
        """Get mineral class name from label index."""
        return IDX_TO_CLASS[idx]

    def get_stats(self) -> DatasetStats:
        """Compute dataset statistics."""
        counter = Counter(label for _, label in self.samples)
        total = len(self.samples)

        class_counts = {IDX_TO_CLASS[idx]: count for idx, count in counter.items()}
        class_weights = {}
        if total > 0:
            for idx, count in counter.items():
                class_weights[IDX_TO_CLASS[idx]] = total / (len(counter) * max(count, 1))

        return DatasetStats(
            total_images=total,
            class_counts=class_counts,
            class_weights=class_weights,
        )


def create_splits(
    root: Union[str, Path],
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
    stratified: bool = True,
) -> Dict[str, List[int]]:
    """
    Create stratified train/val/test splits.

    Returns dict with 'train', 'val', 'test' keys containing index lists.
    """
    root = Path(root)
    all_samples: List[Tuple[Path, int]] = []

    for class_name in MINERAL_CLASSES:
        class_dir = root / class_name
        if not class_dir.is_dir():
            continue
        class_idx = CLASS_TO_IDX[class_name]
        for img_path in sorted(class_dir.iterdir()):
            if img_path.suffix.lower() in IMAGE_EXTENSIONS:
                all_samples.append((img_path, class_idx))

    n = len(all_samples)
    if n == 0:
        raise ValueError(f"No images found in {root}")

    indices = list(range(n))

    if stratified:
        # Group indices by class
        class_indices: Dict[int, List[int]] = {}
        for i, (_, label) in enumerate(all_samples):
            class_indices.setdefault(label, []).append(i)

        train_idx, val_idx, test_idx = [], [], []
        rng = random.Random(seed)

        for cls, cls_indices in class_indices.items():
            rng.shuffle(cls_indices)
            n_cls = len(cls_indices)
            n_train = max(1, int(n_cls * train_ratio))
            n_val = max(1, int(n_cls * val_ratio))

            train_idx.extend(cls_indices[:n_train])
            val_idx.extend(cls_indices[n_train:n_train + n_val])
            test_idx.extend(cls_indices[n_train + n_val:])
    else:
        rng = random.Random(seed)
        rng.shuffle(indices)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)
        train_idx = indices[:n_train]
        val_idx = indices[n_train:n_train + n_val]
        test_idx = indices[n_train + n_val:]

    splits = {"train": train_idx, "val": val_idx, "test": test_idx}
    logger.info(
        "Splits created: train=%d, val=%d, test=%d",
        len(train_idx), len(val_idx), len(test_idx),
    )
    return splits


def save_splits(splits: Dict[str, List[int]], path: Union[str, Path]):
    """Save splits to JSON file."""
    with open(path, "w") as f:
        json.dump(splits, f, indent=2)


def load_splits(path: Union[str, Path]) -> Dict[str, List[int]]:
    """Load splits from JSON file."""
    with open(path) as f:
        return json.load(f)


def create_dataloaders(
    root: Union[str, Path],
    splits: Dict[str, List[int]],
    batch_size: int = 32,
    num_workers: int = 0,
    use_weighted_sampling: bool = True,
) -> Dict[str, "DataLoader"]:
    """
    Create PyTorch DataLoaders for train/val/test splits.
    Uses weighted sampling for training to handle class imbalance.
    """
    if not HAS_TORCH:
        raise ImportError("torch required")

    from ..utils.preprocessing import get_efficientnet_transforms

    train_transform = get_efficientnet_transforms(training=True)
    eval_transform = get_efficientnet_transforms(training=False)

    loaders = {}

    for split_name in ["train", "val", "test"]:
        is_train = split_name == "train"
        transform = train_transform if is_train else eval_transform

        dataset = MineralDataset(
            root=root,
            transform=transform,
            split=split_name,
            indices=splits.get(split_name),
        )

        sampler = None
        shuffle = is_train

        if is_train and use_weighted_sampling:
            # Weighted sampling to handle class imbalance
            labels = [label for _, label in dataset.samples]
            class_counts = Counter(labels)
            weights = [1.0 / class_counts[label] for label in labels]
            sampler = WeightedRandomSampler(weights, num_samples=len(weights))
            shuffle = False

        loaders[split_name] = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=shuffle,
            sampler=sampler,
            num_workers=num_workers,
            pin_memory=False,  # CPU-only
            drop_last=is_train,
        )

    return loaders
