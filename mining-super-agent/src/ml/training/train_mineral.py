"""
Mineral Classifier Training Script
====================================
EfficientNet-B4 fine-tuning with 3-phase transfer learning:
  Phase 1: Frozen backbone, train classifier head only
  Phase 2: Unfreeze last 3 blocks, fine-tune with lower LR
  Phase 3: Full unfreeze, train entire network with very low LR

Data augmentation, validation split, per-class metrics,
confusion matrix for confusable minerals.
CPU-optimized for Oracle Cloud free tier.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.optim.lr_scheduler import CosineAnnealingLR, StepLR
    from torch.utils.data import DataLoader
except ImportError:
    print("ERROR: PyTorch required. Install with: pip install torch torchvision")
    sys.exit(1)

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ml.data.dataset import (
    CLASS_TO_IDX,
    IDX_TO_CLASS,
    LOOK_ALIKE_PAIRS,
    MINERAL_CLASSES,
    MineralDataset,
    create_splits,
    save_splits,
)
from ml.mineral_classifier import MineralClassifier, PYRITE_IDX, GOLD_IDX
from ml.utils.preprocessing import get_efficientnet_transforms

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ── Configuration ─────────────────────────────────────────────────────────────
@dataclass
class TrainingConfig:
    """Training hyperparameters."""
    data_dir: str = "data/minerals"
    output_dir: str = "models/mineral_classifier"
    batch_size: int = 16           # Small for CPU
    num_workers: int = 0           # CPU: no multiprocessing
    seed: int = 42

    # Phase 1: Frozen backbone
    phase1_epochs: int = 10
    phase1_lr: float = 1e-3

    # Phase 2: Partial unfreeze (last 3 blocks)
    phase2_epochs: int = 15
    phase2_lr: float = 1e-4

    # Phase 3: Full unfreeze
    phase3_epochs: int = 10
    phase3_lr: float = 1e-5

    # General
    weight_decay: float = 1e-4
    label_smoothing: float = 0.1
    patience: int = 5              # Early stopping patience
    min_delta: float = 0.001       # Minimum improvement

    # Calibration
    calibrate: bool = True

from dataclasses import dataclass


def set_seed(seed: int):
    """Set random seeds for reproducibility."""
    torch.manual_seed(seed)
    np.random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def get_class_weights(dataset: MineralDataset) -> torch.Tensor:
    """Compute class weights for imbalanced dataset."""
    labels = [label for _, label in dataset.samples]
    counter = Counter(labels)
    total = len(labels)
    weights = torch.zeros(len(MINERAL_CLASSES))

    for cls_idx, count in counter.items():
        weights[cls_idx] = total / (len(counter) * max(count, 1))

    return weights


def train_one_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    optimizer: optim.Optimizer,
    device: torch.device,
    epoch: int,
) -> Dict[str, float]:
    """Train for one epoch."""
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    all_preds = []
    all_labels = []

    for batch_idx, (images, labels) in enumerate(dataloader):
        images, labels = images.to(device), labels.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()

        # Gradient clipping
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

        optimizer.step()

        running_loss += loss.item() * images.size(0)
        _, predicted = outputs.max(1)
        total += labels.size(0)
        correct += predicted.eq(labels).sum().item()

        all_preds.extend(predicted.cpu().numpy())
        all_labels.extend(labels.cpu().numpy())

        if (batch_idx + 1) % 20 == 0:
            logger.info(
                "  Batch %d/%d — Loss: %.4f, Acc: %.2f%%",
                batch_idx + 1, len(dataloader),
                loss.item(),
                100.0 * predicted.eq(labels).sum().item() / images.size(0),
            )

    epoch_loss = running_loss / max(total, 1)
    epoch_acc = correct / max(total, 1)

    return {
        "loss": epoch_loss,
        "accuracy": epoch_acc,
        "predictions": np.array(all_preds),
        "labels": np.array(all_labels),
    }


@torch.no_grad()
def evaluate(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> Dict[str, float]:
    """Evaluate model on validation/test set."""
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0
    all_preds = []
    all_labels = []
    all_probs = []

    for images, labels in dataloader:
        images, labels = images.to(device), labels.to(device)

        outputs = model(images)
        loss = criterion(outputs, labels)

        probs = torch.softmax(outputs, dim=1)
        _, predicted = outputs.max(1)

        running_loss += loss.item() * images.size(0)
        total += labels.size(0)
        correct += predicted.eq(labels).sum().item()

        all_preds.extend(predicted.cpu().numpy())
        all_labels.extend(labels.cpu().numpy())
        all_probs.extend(probs.cpu().numpy())

    return {
        "loss": running_loss / max(total, 1),
        "accuracy": correct / max(total, 1),
        "predictions": np.array(all_preds),
        "labels": np.array(all_labels),
        "probabilities": np.array(all_probs),
    }


def compute_per_class_metrics(
    predictions: np.ndarray,
    labels: np.ndarray,
) -> Dict[str, Dict[str, float]]:
    """Compute precision, recall, F1 for each class."""
    metrics = {}

    for cls_idx in range(len(MINERAL_CLASSES)):
        tp = np.sum((predictions == cls_idx) & (labels == cls_idx))
        fp = np.sum((predictions == cls_idx) & (labels != cls_idx))
        fn = np.sum((predictions != cls_idx) & (labels == cls_idx))

        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-8)

        cls_name = IDX_TO_CLASS[cls_idx]
        metrics[cls_name] = {
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "support": int(np.sum(labels == cls_idx)),
        }

    return metrics


def compute_confusion_matrix(
    predictions: np.ndarray,
    labels: np.ndarray,
) -> np.ndarray:
    """Compute confusion matrix."""
    n = len(MINERAL_CLASSES)
    matrix = np.zeros((n, n), dtype=int)
    for pred, label in zip(predictions, labels):
        matrix[label][pred] += 1
    return matrix


def save_confusion_report(
    confusion_matrix: np.ndarray,
    per_class_metrics: Dict[str, Dict[str, float]],
    output_dir: Path,
):
    """Save confusion matrix and metrics report."""
    # Save confusion matrix
    np.save(output_dir / "confusion_matrix.npy", confusion_matrix)

    # Save human-readable report
    report_lines = [
        "=" * 70,
        "MINERAL CLASSIFIER — EVALUATION REPORT",
        "=" * 70,
        "",
        "Per-Class Metrics:",
        "-" * 50,
    ]

    for cls_name in MINERAL_CLASSES:
        m = per_class_metrics.get(cls_name, {})
        report_lines.append(
            f"  {cls_name:20s}  P={m.get('precision', 0):.3f}  "
            f"R={m.get('recall', 0):.3f}  F1={m.get('f1', 0):.3f}  "
            f"n={m.get('support', 0)}"
        )

    # Highlight confusable pairs
    report_lines.extend(["", "Confusable Mineral Pairs:", "-" * 50])
    for pair in LOOK_ALIKE_PAIRS:
        a, b = pair
        a_idx, b_idx = CLASS_TO_IDX[a], CLASS_TO_IDX[b]
        a_as_b = confusion_matrix[a_idx][b_idx]
        b_as_a = confusion_matrix[b_idx][a_idx]
        report_lines.append(
            f"  {a:15s} → {b:15s}: {a_as_b} misclassifications"
        )
        report_lines.append(
            f"  {b:15s} → {a:15s}: {b_as_a} misclassifications"
        )

    # CRITICAL: Check gold vs pyrite confusion
    gold_as_pyrite = confusion_matrix[GOLD_IDX][PYRITE_IDX]
    pyrite_as_gold = confusion_matrix[PYRITE_IDX][GOLD_IDX]
    report_lines.extend([
        "",
        "⚠️  CRITICAL: Gold vs Pyrite Discrimination:",
        "-" * 50,
        f"  Gold classified as Pyrite: {gold_as_pyrite}",
        f"  Pyrite classified as Gold: {pyrite_as_gold}",
    ])

    if pyrite_as_gold > 0:
        report_lines.append(
            "  🚨 ALERT: Pyrite misclassified as gold! Model must be retrained!"
        )

    report_path = output_dir / "evaluation_report.txt"
    report_path.write_text("\n".join(report_lines))
    logger.info("Report saved to %s", report_path)


def calibrate_temperature(
    model: nn.Module,
    val_loader: DataLoader,
    device: torch.device,
) -> float:
    """Calibrate temperature scaling on validation set."""
    model.eval()
    all_logits = []
    all_labels = []

    with torch.no_grad():
        for images, labels in val_loader:
            images = images.to(device)
            logits = model(images)
            all_logits.append(logits.cpu())
            all_labels.append(labels)

    logits = torch.cat(all_logits)
    labels = torch.cat(all_labels)

    # Temperature scaling
    from ml.mineral_classifier import TemperatureScaling
    temp_scaling = TemperatureScaling()
    temp_scaling.calibrate(logits, labels)

    temperature = temp_scaling.temperature.item()
    logger.info("Calibrated temperature: %.4f", temperature)
    return temperature


def main(args: Optional[List[str]] = None):
    """Main training function."""
    parser = argparse.ArgumentParser(description="Train mineral classifier")
    parser.add_argument("--data-dir", type=str, default="data/minerals")
    parser.add_argument("--output-dir", type=str, default="models/mineral_classifier")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--phase1-epochs", type=int, default=10)
    parser.add_argument("--phase2-epochs", type=int, default=15)
    parser.add_argument("--phase3-epochs", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-calibrate", action="store_true")
    parsed = parser.parse_args(args)

    config = TrainingConfig(
        data_dir=parsed.data_dir,
        output_dir=parsed.output_dir,
        batch_size=parsed.batch_size,
        phase1_epochs=parsed.phase1_epochs,
        phase2_epochs=parsed.phase2_epochs,
        phase3_epochs=parsed.phase3_epochs,
        seed=parsed.seed,
        calibrate=not parsed.no_calibrate,
    )

    set_seed(config.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Training on device: %s", device)

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Dataset ──
    logger.info("Loading dataset from %s", config.data_dir)
    splits = create_splits(config.data_dir, seed=config.seed)
    save_splits(splits, output_dir / "splits.json")

    train_transform = get_efficientnet_transforms(training=True)
    eval_transform = get_efficientnet_transforms(training=False)

    train_dataset = MineralDataset(
        config.data_dir, transform=train_transform,
        split="train", indices=splits["train"],
    )
    val_dataset = MineralDataset(
        config.data_dir, transform=eval_transform,
        split="val", indices=splits["val"],
    )
    test_dataset = MineralDataset(
        config.data_dir, transform=eval_transform,
        split="test", indices=splits["test"],
    )

    logger.info("Train: %d, Val: %d, Test: %d",
                len(train_dataset), len(val_dataset), len(test_dataset))

    # Class weights for imbalanced data
    class_weights = get_class_weights(train_dataset).to(device)

    train_loader = DataLoader(
        train_dataset, batch_size=config.batch_size,
        shuffle=True, num_workers=config.num_workers,
        pin_memory=False, drop_last=True,
    )
    val_loader = DataLoader(
        val_dataset, batch_size=config.batch_size,
        shuffle=False, num_workers=config.num_workers,
    )
    test_loader = DataLoader(
        test_dataset, batch_size=config.batch_size,
        shuffle=False, num_workers=config.num_workers,
    )

    # ── Model ──
    classifier = MineralClassifier(device=str(device))
    model = classifier.model

    # Loss with label smoothing
    criterion = nn.CrossEntropyLoss(
        weight=class_weights,
        label_smoothing=config.label_smoothing,
    )

    best_val_acc = 0.0
    best_val_loss = float("inf")
    patience_counter = 0

    # ── Phase 1: Frozen backbone ──
    logger.info("=" * 60)
    logger.info("PHASE 1: Training classifier head (backbone frozen)")
    logger.info("=" * 60)
    classifier.freeze_backbone(True)

    optimizer = optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=config.phase1_lr,
        weight_decay=config.weight_decay,
    )
    scheduler = CosineAnnealingLR(optimizer, T_max=config.phase1_epochs)

    for epoch in range(config.phase1_epochs):
        logger.info("Phase 1 — Epoch %d/%d", epoch + 1, config.phase1_epochs)
        train_metrics = train_one_epoch(model, train_loader, criterion, optimizer, device, epoch)
        val_metrics = evaluate(model, val_loader, criterion, device)
        scheduler.step()

        logger.info(
            "  Train Loss: %.4f, Acc: %.2f%% | Val Loss: %.4f, Acc: %.2f%%",
            train_metrics["loss"], train_metrics["accuracy"] * 100,
            val_metrics["loss"], val_metrics["accuracy"] * 100,
        )

        if val_metrics["accuracy"] > best_val_acc + config.min_delta:
            best_val_acc = val_metrics["accuracy"]
            best_val_loss = val_metrics["loss"]
            patience_counter = 0
            classifier.save(output_dir / "best_model.pt")
        else:
            patience_counter += 1

    # ── Phase 2: Partial unfreeze ──
    logger.info("=" * 60)
    logger.info("PHASE 2: Fine-tuning last 3 blocks")
    logger.info("=" * 60)
    classifier.unfreeze_last_layers(3)

    optimizer = optim.AdamW(
        [
            {"params": [p for n, p in model.features.named_parameters() if p.requires_grad],
             "lr": config.phase2_lr * 0.1},
            {"params": model.classifier.parameters(), "lr": config.phase2_lr},
        ],
        weight_decay=config.weight_decay,
    )
    scheduler = CosineAnnealingLR(optimizer, T_max=config.phase2_epochs)

    patience_counter = 0
    for epoch in range(config.phase2_epochs):
        logger.info("Phase 2 — Epoch %d/%d", epoch + 1, config.phase2_epochs)
        train_metrics = train_one_epoch(model, train_loader, criterion, optimizer, device, epoch)
        val_metrics = evaluate(model, val_loader, criterion, device)
        scheduler.step()

        logger.info(
            "  Train Loss: %.4f, Acc: %.2f%% | Val Loss: %.4f, Acc: %.2f%%",
            train_metrics["loss"], train_metrics["accuracy"] * 100,
            val_metrics["loss"], val_metrics["accuracy"] * 100,
        )

        if val_metrics["accuracy"] > best_val_acc + config.min_delta:
            best_val_acc = val_metrics["accuracy"]
            best_val_loss = val_metrics["loss"]
            patience_counter = 0
            classifier.save(output_dir / "best_model.pt")
        else:
            patience_counter += 1
            if patience_counter >= config.patience:
                logger.info("Early stopping in Phase 2")
                break

    # ── Phase 3: Full unfreeze ──
    logger.info("=" * 60)
    logger.info("PHASE 3: Full fine-tuning")
    logger.info("=" * 60)
    classifier.freeze_backbone(False)

    optimizer = optim.AdamW(
        [
            {"params": model.features.parameters(), "lr": config.phase3_lr * 0.1},
            {"params": model.classifier.parameters(), "lr": config.phase3_lr},
        ],
        weight_decay=config.weight_decay,
    )
    scheduler = CosineAnnealingLR(optimizer, T_max=config.phase3_epochs)

    patience_counter = 0
    for epoch in range(config.phase3_epochs):
        logger.info("Phase 3 — Epoch %d/%d", epoch + 1, config.phase3_epochs)
        train_metrics = train_one_epoch(model, train_loader, criterion, optimizer, device, epoch)
        val_metrics = evaluate(model, val_loader, criterion, device)
        scheduler.step()

        logger.info(
            "  Train Loss: %.4f, Acc: %.2f%% | Val Loss: %.4f, Acc: %.2f%%",
            train_metrics["loss"], train_metrics["accuracy"] * 100,
            val_metrics["loss"], val_metrics["accuracy"] * 100,
        )

        if val_metrics["accuracy"] > best_val_acc + config.min_delta:
            best_val_acc = val_metrics["accuracy"]
            best_val_loss = val_metrics["loss"]
            patience_counter = 0
            classifier.save(output_dir / "best_model.pt")
        else:
            patience_counter += 1
            if patience_counter >= config.patience:
                logger.info("Early stopping in Phase 3")
                break

    # ── Final Evaluation ──
    logger.info("=" * 60)
    logger.info("FINAL EVALUATION ON TEST SET")
    logger.info("=" * 60)

    # Load best model
    classifier.load(output_dir / "best_model.pt")
    test_metrics = evaluate(classifier.model, test_loader, criterion, device)

    per_class = compute_per_class_metrics(test_metrics["predictions"], test_metrics["labels"])
    confusion = compute_confusion_matrix(test_metrics["predictions"], test_metrics["labels"])

    save_confusion_report(confusion, per_class, output_dir)

    logger.info("Test Accuracy: %.2f%%", test_metrics["accuracy"] * 100)
    logger.info("Test Loss: %.4f", test_metrics["loss"])

    # ── Calibration ──
    if config.calibrate:
        logger.info("Calibrating temperature scaling...")
        temperature = calibrate_temperature(classifier.model, val_loader, device)
        classifier.temp_scaling.temperature.data = torch.tensor([temperature]).to(device)
        classifier._is_calibrated = True
        classifier.save(output_dir / "best_model.pt")

    # ── Save training metadata ──
    metadata = {
        "model": "efficientnet-b4",
        "num_classes": len(MINERAL_CLASSES),
        "classes": MINERAL_CLASSES,
        "training_date": datetime.now(timezone.utc).isoformat(),
        "test_accuracy": float(test_metrics["accuracy"]),
        "test_loss": float(test_metrics["loss"]),
        "best_val_accuracy": float(best_val_acc),
        "calibrated": config.calibrate,
        "config": {
            "batch_size": config.batch_size,
            "phase1_epochs": config.phase1_epochs,
            "phase2_epochs": config.phase2_epochs,
            "phase3_epochs": config.phase3_epochs,
            "label_smoothing": config.label_smoothing,
        },
    }
    with open(output_dir / "training_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info("Training complete! Model saved to %s", output_dir)


if __name__ == "__main__":
    main()
