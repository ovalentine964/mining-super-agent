"""
Evaluation suite for mineral classifier — metrics, confusion matrix, per-class analysis.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np

try:
    import torch
    from torch.utils.data import DataLoader
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from ..data.dataset import MINERAL_CLASSES, IDX_TO_CLASS, LOOK_ALIKE_PAIRS

logger = logging.getLogger(__name__)


def evaluate(model, dataset, device: str = "cpu", batch_size: int = 32) -> dict:
    """Run full evaluation on a dataset."""
    if not HAS_TORCH:
        raise ImportError("torch required")

    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)
    model.eval()
    model.to(device)

    all_preds = []
    all_labels = []
    all_probs = []

    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            outputs = model(images)
            probs = torch.softmax(outputs, dim=1)
            _, preds = outputs.max(1)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.numpy())
            all_probs.extend(probs.cpu().numpy())

    preds = np.array(all_preds)
    labels = np.array(all_labels)
    probs = np.array(all_probs)

    # Overall accuracy
    accuracy = float((preds == labels).mean())

    # Per-class metrics
    per_class = {}
    for idx, name in IDX_TO_CLASS.items():
        mask = labels == idx
        if mask.sum() == 0:
            continue
        tp = ((preds == idx) & (labels == idx)).sum()
        fp = ((preds == idx) & (labels != idx)).sum()
        fn = ((preds != idx) & (labels == idx)).sum()
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        
        per_class[name] = {
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "support": int(mask.sum()),
            "accuracy": float((preds[mask] == idx).mean()),
        }

    # Look-alike confusion analysis
    look_alike_errors = {}
    for pair in LOOK_ALIKE_PAIRS:
        idx_a = MINERAL_CLASSES.index(pair[0]) if pair[0] in MINERAL_CLASSES else -1
        idx_b = MINERAL_CLASSES.index(pair[1]) if pair[1] in MINERAL_CLASSES else -1
        if idx_a < 0 or idx_b < 0:
            continue
        
        a_as_b = ((preds == idx_b) & (labels == idx_a)).sum()
        b_as_a = ((preds == idx_a) & (labels == idx_b)).sum()
        total = ((labels == idx_a) | (labels == idx_b)).sum()
        
        if total > 0:
            look_alike_errors[f"{pair[0]}↔{pair[1]}"] = {
                f"{pair[0]}_as_{pair[1]}": int(a_as_b),
                f"{pair[1]}_as_{pair[0]}": int(b_as_a),
                "total_confused": int(a_as_b + b_as_a),
                "confusion_rate": float((a_as_b + b_as_a) / total),
            }

    # Confidence calibration (ECE)
    ece = _expected_calibration_error(probs, labels, n_bins=15)

    return {
        "accuracy": accuracy,
        "per_class": per_class,
        "look_alike_errors": look_alike_errors,
        "expected_calibration_error": ece,
        "total_samples": len(labels),
    }


def _expected_calibration_error(probs: np.ndarray, labels: np.ndarray, n_bins: int = 15) -> float:
    """Compute Expected Calibration Error (ECE)."""
    confidences = probs.max(axis=1)
    predictions = probs.argmax(axis=1)
    accuracies = (predictions == labels).astype(float)
    
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    
    for i in range(n_bins):
        mask = (confidences > bin_boundaries[i]) & (confidences <= bin_boundaries[i + 1])
        if mask.sum() == 0:
            continue
        bin_acc = accuracies[mask].mean()
        bin_conf = confidences[mask].mean()
        ece += mask.sum() * abs(bin_acc - bin_conf)
    
    return float(ece / len(labels))


def print_report(eval_result: dict):
    """Print a formatted evaluation report."""
    print(f"\n{'='*60}")
    print(f"MINERAL CLASSIFIER EVALUATION REPORT")
    print(f"{'='*60}")
    print(f"Overall Accuracy: {eval_result['accuracy']:.1%}")
    print(f"Total Samples: {eval_result['total_samples']}")
    print(f"ECE: {eval_result['expected_calibration_error']:.4f}")
    
    print(f"\n{'─'*60}")
    print(f"{'Mineral':<15} {'Prec':>6} {'Rec':>6} {'F1':>6} {'Support':>8}")
    print(f"{'─'*60}")
    for name, m in sorted(eval_result["per_class"].items()):
        print(f"{name:<15} {m['precision']:>6.1%} {m['recall']:>6.1%} {m['f1']:>6.1%} {m['support']:>8}")
    
    if eval_result["look_alike_errors"]:
        print(f"\n{'─'*60}")
        print("LOOK-ALIKE CONFUSION:")
        for pair, data in eval_result["look_alike_errors"].items():
            print(f"  {pair}: {data['total_confused']} confused ({data['confusion_rate']:.1%})")
