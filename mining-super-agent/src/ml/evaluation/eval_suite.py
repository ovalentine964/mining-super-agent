"""
Evaluation Suite for Mineral Classifier
=========================================
Test set evaluation, confidence calibration testing,
robustness testing (blur, low light, rotation),
regression testing between versions,
gold vs pyrite discrimination test.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import torch
    import torch.nn.functional as F
except ImportError:
    print("ERROR: PyTorch required")
    sys.exit(1)

try:
    from PIL import Image, ImageEnhance, ImageFilter
except ImportError:
    print("ERROR: Pillow required")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ml.data.dataset import (
    CLASS_TO_IDX,
    IDX_TO_CLASS,
    LOOK_ALIKE_PAIRS,
    MINERAL_CLASSES,
    MineralDataset,
)
from ml.mineral_classifier import (
    GOLD_IDX,
    IMAGE_ONLY_MAX_CONFIDENCE,
    PYRITE_IDX,
    MineralClassifier,
    assert_pyrite_not_gold,
)
from ml.utils.preprocessing import get_efficientnet_transforms

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ── Data Classes ──────────────────────────────────────────────────────────────

@dataclass
class AccuracyResult:
    """Test set accuracy result."""
    overall_accuracy: float
    per_class_accuracy: Dict[str, float]
    per_class_f1: Dict[str, float]
    macro_f1: float
    weighted_f1: float
    total_samples: int
    correct_predictions: int


@dataclass
class CalibrationResult:
    """Confidence calibration test result."""
    expected_calibration_error: float   # ECE
    maximum_calibration_error: float    # MCE
    average_confidence: float
    average_accuracy: float
    bins: List[Dict[str, float]]       # Per-bin stats
    is_well_calibrated: bool            # ECE < 0.05


@dataclass
class RobustnessResult:
    """Robustness test result."""
    blur_results: Dict[str, float]     # blur_level → accuracy
    brightness_results: Dict[str, float]  # brightness → accuracy
    rotation_results: Dict[str, float]    # angle → accuracy
    overall_robustness_score: float    # Average accuracy across all perturbations


@dataclass
class RegressionResult:
    """Regression test result between model versions."""
    version_a: str
    version_b: str
    accuracy_a: float
    accuracy_b: float
    accuracy_delta: float
    per_class_delta: Dict[str, float]
    has_regression: bool               # Any class dropped > 5%
    regression_classes: List[str]


@dataclass
class GoldPyriteResult:
    """Gold vs Pyrite discrimination test result."""
    gold_as_pyrite: int                # Correct: gold classified as pyrite (acceptable)
    pyrite_as_gold: int                # CRITICAL: pyrite classified as gold (UNACCEPTABLE)
    gold_correct: int                  # Gold correctly identified
    pyrite_correct: int                # Pyrite correctly identified
    gold_confidence_when_correct: float
    pyrite_confidence_when_correct: float
    discrimination_score: float        # 0-1, higher is better
    safety_passed: bool                # pyrite_as_gold == 0


@dataclass
class FullEvalReport:
    """Complete evaluation report."""
    accuracy: AccuracyResult
    calibration: Optional[CalibrationResult]
    robustness: Optional[RobustnessResult]
    gold_pyrite: GoldPyriteResult
    timestamp: str
    model_path: str
    passed: bool                       # Overall pass/fail


# ── Evaluator ─────────────────────────────────────────────────────────────────

class MineralEvaluator:
    """
    Comprehensive evaluation suite for the mineral classifier.
    """

    def __init__(
        self,
        model_path: str,
        data_dir: str,
        device: Optional[str] = None,
    ):
        self.device = torch.device(
            device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self.classifier = MineralClassifier(model_path=model_path, device=str(self.device))
        self.data_dir = Path(data_dir)
        self.eval_transform = get_efficientnet_transforms(training=False)

    def run_full_evaluation(
        self,
        splits_path: Optional[str] = None,
        test_indices: Optional[List[int]] = None,
    ) -> FullEvalReport:
        """Run the complete evaluation suite."""
        logger.info("Starting full evaluation suite...")

        # Load test dataset
        test_dataset = MineralDataset(
            self.data_dir,
            transform=self.eval_transform,
            split="test",
            indices=test_indices,
        )
        logger.info("Test set: %d samples", len(test_dataset))

        # 1. Accuracy
        logger.info("Running accuracy evaluation...")
        accuracy = self.evaluate_accuracy(test_dataset)

        # 2. Calibration
        logger.info("Running calibration evaluation...")
        calibration = self.evaluate_calibration(test_dataset)

        # 3. Robustness
        logger.info("Running robustness evaluation...")
        robustness = self.evaluate_robustness(test_dataset)

        # 4. Gold vs Pyrite
        logger.info("Running gold vs pyrite discrimination test...")
        gold_pyrite = self.evaluate_gold_pyrite(test_dataset)

        # Overall pass/fail
        passed = (
            accuracy.overall_accuracy >= 0.70
            and gold_pyrite.safety_passed
            and (calibration is None or calibration.is_well_calibrated)
        )

        report = FullEvalReport(
            accuracy=accuracy,
            calibration=calibration,
            robustness=robustness,
            gold_pyrite=gold_pyrite,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            model_path=str(self.classifier.model.model_path if hasattr(self.classifier.model, 'model_path') else ""),
            passed=passed,
        )

        logger.info("Evaluation complete. Overall: %s", "PASSED ✓" if passed else "FAILED ✗")
        return report

    def evaluate_accuracy(self, dataset: MineralDataset) -> AccuracyResult:
        """Evaluate test set accuracy with per-class metrics."""
        all_preds = []
        all_labels = []

        for i in range(len(dataset)):
            image, label = dataset[i]
            image_tensor = image.unsqueeze(0).to(self.device)

            with torch.no_grad():
                output = self.classifier.model(image_tensor)
                pred = output.argmax(dim=1).item()

            all_preds.append(pred)
            all_labels.append(label)

        all_preds = np.array(all_preds)
        all_labels = np.array(all_labels)

        # Overall accuracy
        correct = np.sum(all_preds == all_labels)
        accuracy = correct / len(all_labels)

        # Per-class metrics
        per_class_acc = {}
        per_class_f1 = {}

        for cls_idx in range(len(MINERAL_CLASSES)):
            cls_mask = all_labels == cls_idx
            if np.sum(cls_mask) == 0:
                per_class_acc[IDX_TO_CLASS[cls_idx]] = 0.0
                per_class_f1[IDX_TO_CLASS[cls_idx]] = 0.0
                continue

            cls_correct = np.sum((all_preds == cls_idx) & (all_labels == cls_idx))
            cls_total = np.sum(cls_mask)
            per_class_acc[IDX_TO_CLASS[cls_idx]] = float(cls_correct / cls_total)

            # F1
            tp = cls_correct
            fp = np.sum((all_preds == cls_idx) & (all_labels != cls_idx))
            fn = np.sum((all_preds != cls_idx) & (all_labels == cls_idx))
            precision = tp / max(tp + fp, 1)
            recall = tp / max(tp + fn, 1)
            f1 = 2 * precision * recall / max(precision + recall, 1e-8)
            per_class_f1[IDX_TO_CLASS[cls_idx]] = float(f1)

        # Macro and weighted F1
        macro_f1 = np.mean(list(per_class_f1.values()))
        support = [np.sum(all_labels == i) for i in range(len(MINERAL_CLASSES))]
        weighted_f1 = np.average(list(per_class_f1.values()), weights=support)

        return AccuracyResult(
            overall_accuracy=float(accuracy),
            per_class_accuracy=per_class_acc,
            per_class_f1=per_class_f1,
            macro_f1=float(macro_f1),
            weighted_f1=float(weighted_f1),
            total_samples=len(all_labels),
            correct_predictions=int(correct),
        )

    def evaluate_calibration(
        self,
        dataset: MineralDataset,
        n_bins: int = 10,
    ) -> CalibrationResult:
        """
        Evaluate confidence calibration using Expected Calibration Error (ECE).
        Well-calibrated: ECE < 0.05
        """
        all_probs = []
        all_labels = []
        all_correct = []

        for i in range(len(dataset)):
            image, label = dataset[i]
            image_tensor = image.unsqueeze(0).to(self.device)

            with torch.no_grad():
                output = self.classifier.model(image_tensor)
                # Apply temperature scaling if calibrated
                if self.classifier._is_calibrated:
                    output = self.classifier.temp_scaling(output)
                probs = F.softmax(output, dim=1).squeeze()

            # Cap confidence for image-only
            max_prob = min(probs.max().item(), IMAGE_ONLY_MAX_CONFIDENCE)
            pred = probs.argmax().item()

            all_probs.append(max_prob)
            all_labels.append(label)
            all_correct.append(pred == label)

        all_probs = np.array(all_probs)
        all_correct = np.array(all_correct, dtype=float)

        # Compute ECE
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        bins = []
        ece = 0.0
        mce = 0.0

        for i in range(n_bins):
            mask = (all_probs > bin_boundaries[i]) & (all_probs <= bin_boundaries[i + 1])
            if np.sum(mask) == 0:
                continue

            bin_confidence = np.mean(all_probs[mask])
            bin_accuracy = np.mean(all_correct[mask])
            bin_size = np.sum(mask)

            bin_gap = abs(bin_accuracy - bin_confidence)
            ece += bin_gap * bin_size / len(all_probs)
            mce = max(mce, bin_gap)

            bins.append({
                "lower": float(bin_boundaries[i]),
                "upper": float(bin_boundaries[i + 1]),
                "confidence": float(bin_confidence),
                "accuracy": float(bin_accuracy),
                "count": int(bin_size),
                "gap": float(bin_gap),
            })

        return CalibrationResult(
            expected_calibration_error=float(ece),
            maximum_calibration_error=float(mce),
            average_confidence=float(np.mean(all_probs)),
            average_accuracy=float(np.mean(all_correct)),
            bins=bins,
            is_well_calibrated=ece < 0.05,
        )

    def evaluate_robustness(
        self,
        dataset: MineralDataset,
        sample_size: int = 100,
    ) -> RobustnessResult:
        """
        Test model robustness to image perturbations:
        - Blur (Gaussian)
        - Brightness changes
        - Rotation
        """
        # Sample a subset for speed
        indices = np.random.choice(len(dataset), min(sample_size, len(dataset)), replace=False)

        def evaluate_subset(transform_fn) -> float:
            correct = 0
            total = 0
            for idx in indices:
                image, label = dataset.samples[idx]
                img = Image.open(image).convert("RGB")
                img = transform_fn(img)
                tensor = self.eval_transform(img).unsqueeze(0).to(self.device)

                with torch.no_grad():
                    output = self.classifier.model(tensor)
                    pred = output.argmax(dim=1).item()

                correct += (pred == label)
                total += 1
            return correct / max(total, 1)

        # Blur tests
        blur_results = {}
        for sigma in [0, 1, 2, 4, 8]:
            fn = lambda img, s=sigma: img.filter(ImageFilter.GaussianBlur(radius=s))
            acc = evaluate_subset(fn)
            blur_results[f"blur_sigma_{sigma}"] = acc
            logger.info("  Blur σ=%d: %.2f%%", sigma, acc * 100)

        # Brightness tests
        brightness_results = {}
        for factor in [0.3, 0.5, 0.7, 1.0, 1.3, 1.5]:
            fn = lambda img, f=factor: ImageEnhance.Brightness(img).enhance(f)
            acc = evaluate_subset(fn)
            brightness_results[f"brightness_{factor}"] = acc
            logger.info("  Brightness %.1f: %.2f%%", factor, acc * 100)

        # Rotation tests
        rotation_results = {}
        for angle in [0, 45, 90, 135, 180, 270]:
            fn = lambda img, a=angle: img.rotate(a, expand=True)
            acc = evaluate_subset(fn)
            rotation_results[f"rotation_{angle}"] = acc
            logger.info("  Rotation %d°: %.2f%%", angle, acc * 100)

        all_accs = list(blur_results.values()) + list(brightness_results.values()) + list(rotation_results.values())
        robustness_score = np.mean(all_accs)

        return RobustnessResult(
            blur_results=blur_results,
            brightness_results=brightness_results,
            rotation_results=rotation_results,
            overall_robustness_score=float(robustness_score),
        )

    def evaluate_gold_pyrite(self, dataset: MineralDataset) -> GoldPyriteResult:
        """
        CRITICAL TEST: Gold vs Pyrite discrimination.
        Pyrite must NEVER be classified as gold.
        """
        gold_correct = 0
        gold_total = 0
        gold_as_pyrite = 0
        gold_confidences = []

        pyrite_correct = 0
        pyrite_total = 0
        pyrite_as_gold = 0  # THE CRITICAL FAILURE
        pyrite_confidences = []

        for i in range(len(dataset)):
            image, label = dataset[i]
            image_tensor = image.unsqueeze(0).to(self.device)

            with torch.no_grad():
                output = self.classifier.model(image_tensor)
                if self.classifier._is_calibrated:
                    output = self.classifier.temp_scaling(output)
                probs = F.softmax(output, dim=1).squeeze().cpu().numpy()

            pred = int(np.argmax(probs))
            confidence = float(probs[pred])

            if label == GOLD_IDX:
                gold_total += 1
                if pred == GOLD_IDX:
                    gold_correct += 1
                    gold_confidences.append(confidence)
                elif pred == PYRITE_IDX:
                    gold_as_pyrite += 1

            elif label == PYRITE_IDX:
                pyrite_total += 1
                if pred == PYRITE_IDX:
                    pyrite_correct += 1
                    pyrite_confidences.append(confidence)
                elif pred == GOLD_IDX:
                    pyrite_as_gold += 1  # CRITICAL FAILURE
                    logger.error(
                        "🚨 CRITICAL: Pyrite sample %d classified as GOLD! "
                        "Gold prob: %.3f, Pyrite prob: %.3f",
                        i, probs[GOLD_IDX], probs[PYRITE_IDX],
                    )

        # Discrimination score
        gold_acc = gold_correct / max(gold_total, 1)
        pyrite_acc = pyrite_correct / max(pyrite_total, 1)
        discrimination = (gold_acc + pyrite_acc) / 2

        result = GoldPyriteResult(
            gold_as_pyrite=gold_as_pyrite,
            pyrite_as_gold=pyrite_as_gold,
            gold_correct=gold_correct,
            pyrite_correct=pyrite_correct,
            gold_confidence_when_correct=float(np.mean(gold_confidences)) if gold_confidences else 0.0,
            pyrite_confidence_when_correct=float(np.mean(pyrite_confidences)) if pyrite_confidences else 0.0,
            discrimination_score=float(discrimination),
            safety_passed=(pyrite_as_gold == 0),
        )

        logger.info(
            "Gold/Pyrite: Gold→Gold=%d/%d, Pyrite→Pyrite=%d/%d, "
            "Pyrite→Gold=%d (must be 0), Score=%.2f%%",
            gold_correct, gold_total, pyrite_correct, pyrite_total,
            pyrite_as_gold, discrimination * 100,
        )

        return result

    def regression_test(
        self,
        other_model_path: str,
        dataset: MineralDataset,
    ) -> RegressionResult:
        """Compare current model against another version."""
        # Evaluate current model
        current_result = self.evaluate_accuracy(dataset)

        # Load and evaluate other model
        other_classifier = MineralClassifier(model_path=other_model_path, device=str(self.device))
        other_preds = []
        other_labels = []

        for i in range(len(dataset)):
            image, label = dataset[i]
            tensor = image.unsqueeze(0).to(self.device)
            with torch.no_grad():
                output = other_classifier.model(tensor)
                pred = output.argmax(dim=1).item()
            other_preds.append(pred)
            other_labels.append(label)

        other_preds = np.array(other_preds)
        other_labels = np.array(other_labels)
        other_accuracy = float(np.sum(other_preds == other_labels) / len(other_labels))

        # Per-class comparison
        per_class_delta = {}
        regression_classes = []
        for cls_idx, cls_name in IDX_TO_CLASS.items():
            mask = np.array(other_labels) == cls_idx
            if np.sum(mask) == 0:
                continue

            curr_acc = current_result.per_class_accuracy.get(cls_name, 0)
            other_acc = float(np.sum(other_preds[mask] == cls_idx) / np.sum(mask))
            delta = curr_acc - other_acc
            per_class_delta[cls_name] = delta

            if delta < -0.05:
                regression_classes.append(cls_name)

        return RegressionResult(
            version_a="current",
            version_b="other",
            accuracy_a=current_result.overall_accuracy,
            accuracy_b=other_accuracy,
            accuracy_delta=current_result.overall_accuracy - other_accuracy,
            per_class_delta=per_class_delta,
            has_regression=len(regression_classes) > 0,
            regression_classes=regression_classes,
        )


def save_eval_report(report: FullEvalReport, output_path: Path):
    """Save evaluation report to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "timestamp": report.timestamp,
        "model_path": report.model_path,
        "passed": report.passed,
        "accuracy": {
            "overall": report.accuracy.overall_accuracy,
            "macro_f1": report.accuracy.macro_f1,
            "weighted_f1": report.accuracy.weighted_f1,
            "per_class": report.accuracy.per_class_accuracy,
        },
        "calibration": {
            "ece": report.calibration.expected_calibration_error,
            "mce": report.calibration.maximum_calibration_error,
            "well_calibrated": report.calibration.is_well_calibrated,
        } if report.calibration else None,
        "robustness": {
            "overall_score": report.robustness.overall_robustness_score,
            "blur": report.robustness.blur_results,
            "brightness": report.robustness.brightness_results,
            "rotation": report.robustness.rotation_results,
        } if report.robustness else None,
        "gold_pyrite": {
            "pyrite_as_gold": report.gold_pyrite.pyrite_as_gold,
            "safety_passed": report.gold_pyrite.safety_passed,
            "discrimination_score": report.gold_pyrite.discrimination_score,
        },
    }

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    logger.info("Report saved to %s", output_path)


def main(args: Optional[List[str]] = None):
    parser = argparse.ArgumentParser(description="Evaluate mineral classifier")
    parser.add_argument("--model-path", type=str, required=True)
    parser.add_argument("--data-dir", type=str, default="data/minerals")
    parser.add_argument("--output", type=str, default="eval_results.json")
    parser.add_argument("--regression", type=str, default=None,
                        help="Path to previous model for regression testing")
    parsed = parser.parse_args(args)

    evaluator = MineralEvaluator(
        model_path=parsed.model_path,
        data_dir=parsed.data_dir,
    )

    report = evaluator.run_full_evaluation()
    save_eval_report(report, Path(parsed.output))

    if parsed.regression:
        logger.info("Running regression test against %s", parsed.regression)
        dataset = MineralDataset(
            parsed.data_dir,
            transform=get_efficientnet_transforms(training=False),
        )
        regression = evaluator.regression_test(parsed.regression, dataset)
        logger.info("Regression test: %s", "PASSED" if not regression.has_regression else "FAILED")
        if regression.regression_classes:
            logger.warning("Regressed classes: %s", regression.regression_classes)

    # Exit with appropriate code
    sys.exit(0 if report.passed else 1)


if __name__ == "__main__":
    main()
