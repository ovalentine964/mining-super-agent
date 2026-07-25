"""
Mineral classifier training — 3-phase transfer learning with EfficientNet-B4.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, Dataset
    from torchvision import models
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from ..data.dataset import MINERAL_CLASSES, NUM_CLASSES
from ..utils.preprocessing import get_efficientnet_transforms

logger = logging.getLogger(__name__)


class MineralDataset(Dataset):
    """Dataset for mineral images."""

    def __init__(self, root_dir: str, split: str = "train"):
        if not HAS_TORCH:
            raise ImportError("torch required")
        
        self.root = Path(root_dir) / split
        self.transform = get_efficientnet_transforms(training=(split == "train"))
        self.samples = []
        
        for class_idx, class_name in enumerate(MINERAL_CLASSES):
            class_dir = self.root / class_name
            if class_dir.exists():
                for img_path in class_dir.glob("*"):
                    if img_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                        self.samples.append((str(img_path), class_idx))
        
        logger.info(f"Loaded {len(self.samples)} samples from {self.root}")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        from PIL import Image
        path, label = self.samples[idx]
        image = Image.open(path).convert("RGB")
        tensor = self.transform(image)
        return tensor, label


def train(
    data_dir: str,
    output_path: str,
    epochs_phase1: int = 5,
    epochs_phase2: int = 10,
    epochs_phase3: int = 15,
    batch_size: int = 16,
    lr: float = 1e-3,
    device: Optional[str] = None,
):
    """
    3-phase training:
    Phase 1: Train classifier head only (backbone frozen)
    Phase 2: Unfreeze last 3 blocks, fine-tune
    Phase 3: Full network fine-tune with low LR
    """
    if not HAS_TORCH:
        raise ImportError("torch required")

    device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
    logger.info(f"Training on {device}")

    # Load data
    train_ds = MineralDataset(data_dir, "train")
    val_ds = MineralDataset(data_dir, "val")
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=4)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=4)

    # Build model
    model = models.efficientnet_b4(weights=models.EfficientNet_B4_Weights.DEFAULT)
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.4), nn.Linear(in_features, 512), nn.ReLU(),
        nn.Dropout(p=0.2), nn.Linear(512, NUM_CLASSES),
    )
    model.to(device)

    criterion = nn.CrossEntropyLoss()

    def run_phase(name, epochs, trainable_params_fn, learning_rate):
        logger.info(f"=== {name}: {epochs} epochs, lr={learning_rate} ===")
        trainable_params_fn()
        optimizer = optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=learning_rate)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
        
        for epoch in range(epochs):
            model.train()
            total_loss = 0
            correct = 0
            total = 0
            for images, labels in train_loader:
                images, labels = images.to(device), labels.to(device)
                optimizer.zero_grad()
                outputs = model(images)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
                _, predicted = outputs.max(1)
                total += labels.size(0)
                correct += predicted.eq(labels).sum().item()
            scheduler.step()
            
            acc = 100.0 * correct / total
            avg_loss = total_loss / len(train_loader)
            logger.info(f"Epoch {epoch+1}/{epochs}: loss={avg_loss:.4f}, acc={acc:.1f}%")
        
        # Validate
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                _, predicted = outputs.max(1)
                total += labels.size(0)
                correct += predicted.eq(labels).sum().item()
        val_acc = 100.0 * correct / total
        logger.info(f"Validation accuracy: {val_acc:.1f}%")

    # Phase 1: Head only
    def freeze_backbone():
        for param in model.features.parameters():
            param.requires_grad = False
        for param in model.classifier.parameters():
            param.requires_grad = True
    run_phase("Phase 1 — Head Only", epochs_phase1, freeze_backbone, lr)

    # Phase 2: Last 3 blocks
    def unfreeze_last_blocks():
        for param in model.features.parameters():
            param.requires_grad = False
        for layer in list(model.features.children())[-3:]:
            for param in layer.parameters():
                param.requires_grad = True
        for param in model.classifier.parameters():
            param.requires_grad = True
    run_phase("Phase 2 — Last Blocks", epochs_phase2, unfreeze_last_blocks, lr * 0.1)

    # Phase 3: Full fine-tune
    def unfreeze_all():
        for param in model.parameters():
            param.requires_grad = True
    run_phase("Phase 3 — Full Fine-tune", epochs_phase3, unfreeze_all, lr * 0.01)

    # Save
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "model_state_dict": model.state_dict(),
        "num_classes": NUM_CLASSES,
        "class_to_idx": {c: i for i, c in enumerate(MINERAL_CLASSES)},
    }, output)
    logger.info(f"Model saved to {output}")
