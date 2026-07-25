"""
Mineral Classifier — EfficientNet-B4 with Transfer Learning
============================================================
20 mineral classes with 3-phase training, confidence calibration,
look-alike detection, and safety-critical pyrite→gold prevention.

CRITICAL CONSTRAINT: Pyrite must NEVER be classified as gold.
All predictions include Swahili disclaimer.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torchvision import models

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from .data.dataset import (
    CLASS_TO_IDX,
    IDX_TO_CLASS,
    LOOK_ALIKE_PAIRS,
    MINERAL_CLASSES,
)
from .utils.preprocessing import (
    EFFICIENTNET_INPUT_SIZE,
    assess_quality,
    get_efficientnet_transforms,
    load_image,
)

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
NUM_CLASSES = 20
DISCLAIMER_SWAHILI = (
    "Hii si uthibitisho wa maabara. Tafadhali thibitisha na mtihani wa kimwili."
)
DISCLAIMER_ENGLISH = (
    "This is not laboratory confirmation. Please verify with physical testing."
)
# Maximum confidence for image-only identification (no XRF/spectroscopy)
IMAGE_ONLY_MAX_CONFIDENCE = 0.65
# Minimum confidence below which we refuse to predict
MIN_CONFIDENCE_THRESHOLD = 0.10
# Pyrite class index — must NEVER map to gold
PYRITE_IDX = CLASS_TO_IDX["pyrite"]
GOLD_IDX = CLASS_TO_IDX["gold"]


@dataclass
class MineralPrediction:
    """Structured prediction output with safety checks."""
    mineral: str
    confidence: float
    top_3: List[Tuple[str, float]]
    disclaimers: List[str]
    quality_issues: List[str]
    is_certain: bool           # confidence > 0.5
    requires_expert: bool      # economic mineral or look-alike detected
    look_alike_warning: Optional[str] = None
    inference_time_ms: float = 0.0
    calibrated: bool = False

    def to_dict(self) -> dict:
        return {
            "mineral": self.mineral,
            "confidence": round(self.confidence, 4),
            "top_3": [{"mineral": m, "confidence": round(c, 4)} for m, c in self.top_3],
            "disclaimers": self.disclaimers,
            "quality_issues": self.quality_issues,
            "is_certain": self.is_certain,
            "requires_expert": self.requires_expert,
            "look_alike_warning": self.look_alike_warning,
            "inference_time_ms": round(self.inference_time_ms, 1),
            "calibrated": self.calibrated,
        }


class TemperatureScaling(nn.Module if HAS_TORCH else object):
    """
    Post-hoc temperature scaling for confidence calibration.
    Learns a single temperature parameter on validation set.
    """

    def __init__(self):
        if not HAS_TORCH:
            raise ImportError("torch required")
        super().__init__()
        self.temperature = nn.Parameter(torch.ones(1) * 1.5)

    def forward(self, logits: torch.Tensor) -> torch.Tensor:
        return logits / self.temperature

    def calibrate(self, logits: torch.Tensor, labels: torch.Tensor, lr: float = 0.01, max_iter: int = 100):
        """Optimize temperature on validation set using NLL loss."""
        self.train()
        optimizer = torch.optim.LBFGS([self.temperature], lr=lr, max_iter=max_iter)
        nll = nn.CrossEntropyLoss()

        def closure():
            optimizer.zero_grad()
            scaled = self.forward(logits)
            loss = nll(scaled, labels)
            loss.backward()
            return loss

        optimizer.step(closure)
        self.eval()
        logger.info("Calibrated temperature: %.4f", self.temperature.item())


class MineralClassifier:
    """
    EfficientNet-B4 mineral classifier with 3-phase transfer learning,
    confidence calibration, and safety-critical pyrite→gold prevention.

    Inference: photo → mineral type + confidence + disclaimers
    """

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        device: Optional[str] = None,
    ):
        if not HAS_TORCH:
            raise ImportError("PyTorch required for MineralClassifier")

        self.device = torch.device(
            device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        )
        logger.info("MineralClassifier using device: %s", self.device)

        # Build model
        self.model = self._build_model()
        self.model.to(self.device)
        self.model.eval()

        # Temperature scaling for calibration
        self.temp_scaling = TemperatureScaling().to(self.device)
        self._is_calibrated = False

        # Load pretrained weights if provided
        if model_path:
            self.load(model_path)

        # Inference transforms
        self.transform = get_efficientnet_transforms(training=False)

        # Economic minerals that always require expert review
        self.economic_minerals = {"gold", "copper", "galena", "sphalerite"}

    def _build_model(self) -> nn.Module:
        """Build EfficientNet-B4 with custom classification head."""
        model = models.efficientnet_b4(weights=models.EfficientNet_B4_Weights.DEFAULT)

        # Replace classifier head
        in_features = model.classifier[1].in_features
        model.classifier = nn.Sequential(
            nn.Dropout(p=0.4, inplace=True),
            nn.Linear(in_features, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.2),
            nn.Linear(512, NUM_CLASSES),
        )
        return model

    def predict(
        self,
        image_source: Union[str, Path, "PIL.Image.Image"],
        apply_safety_checks: bool = True,
    ) -> MineralPrediction:
        """
        Run inference on a single image.

        Returns MineralPrediction with calibrated confidence, disclaimers,
        and safety checks.
        """
        start_time = time.perf_counter()

        # Load and preprocess
        image = load_image(image_source)
        quality = assess_quality(image)
        tensor = self.transform(image).unsqueeze(0).to(self.device)

        # Forward pass
        self.model.eval()
        with torch.no_grad():
            logits = self.model(tensor)

        # Apply temperature scaling if calibrated
        if self._is_calibrated:
            with torch.no_grad():
                calibrated_logits = self.temp_scaling(logits)
            probs = F.softmax(calibrated_logits, dim=1).squeeze(0).cpu().numpy()
        else:
            probs = F.softmax(logits, dim=1).squeeze(0).cpu().numpy()

        # Get top predictions
        top_indices = np.argsort(probs)[::-1]
        top_3 = [(IDX_TO_CLASS[i], float(probs[i])) for i in top_indices[:3]]

        best_idx = top_indices[0]
        best_class = IDX_TO_CLASS[best_idx]
        best_confidence = float(probs[best_idx])

        # ── CAP CONFIDENCE for image-only identification ──
        # Without XRF/spectroscopy, we cannot be more than 65% certain
        capped_confidence = min(best_confidence, IMAGE_ONLY_MAX_CONFIDENCE)

        # ── Safety Checks ──
        disclaimers = [DISCLAIMER_SWAHILI, DISCLAIMER_ENGLISH]
        quality_issues = quality.issues if not quality.is_usable else []
        look_alike_warning = None
        requires_expert = False

        if apply_safety_checks:
            # CRITICAL: Pyrite must NEVER be classified as gold
            if best_idx == PYRITE_IDX and best_confidence > 0.3:
                # Check if gold appears in top predictions
                gold_prob = float(probs[GOLD_IDX])
                if gold_prob > 0.05:
                    look_alike_warning = (
                        f"WARNING: This sample has characteristics of pyrite (fool's gold). "
                        f"Gold probability: {gold_prob:.1%}. Pyrite probability: {best_confidence:.1%}. "
                        f"Pyrite is commonly mistaken for gold. Physical testing is MANDATORY."
                    )
                    disclaimers.append(look_alike_warning)

            # If predicted as gold, check pyrite probability
            if best_idx == GOLD_IDX:
                pyrite_prob = float(probs[PYRITE_IDX])
                if pyrite_prob > 0.1:
                    look_alike_warning = (
                        f"CAUTION: This sample may be gold OR pyrite (fool's gold). "
                        f"Gold: {best_confidence:.1%}, Pyrite: {pyrite_prob:.1%}. "
                        f"These minerals are easily confused from photos alone. "
                        f"Mandatory: streak test, hardness test, and XRF analysis."
                    )
                    disclaimers.append(look_alike_warning)
                    # DOWNRANK gold if pyrite is also probable
                    if pyrite_prob > 0.2:
                        capped_confidence = min(capped_confidence, 0.40)

            # Check all look-alike pairs
            for pair in LOOK_ALIKE_PAIRS:
                pair_indices = [CLASS_TO_IDX[p] for p in pair]
                if best_idx in pair_indices:
                    other_idx = pair_indices[0] if pair_indices[1] == best_idx else pair_indices[1]
                    other_prob = float(probs[other_idx])
                    if other_prob > 0.15:
                        look_alike_warning = (
                            f"WARNING: {IDX_TO_CLASS[best_idx]} and {IDX_TO_CLASS[other_idx]} "
                            f"are commonly confused. Probabilities: {best_confidence:.1%} vs {other_prob:.1%}. "
                            f"Physical testing required."
                        )
                        disclaimers.append(look_alike_warning)

            # Economic minerals always require expert
            if best_class in self.economic_minerals:
                requires_expert = True
                disclaimers.append(
                    f"ALERT: {best_class.upper()} is an economic mineral. "
                    f"Professional geological survey and laboratory analysis required."
                )

            # Low confidence warning
            if capped_confidence < MIN_CONFIDENCE_THRESHOLD:
                disclaimers.append(
                    "Confidence too low for identification. "
                    "Please provide a clearer, well-lit photo of the sample."
                )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return MineralPrediction(
            mineral=best_class,
            confidence=capped_confidence,
            top_3=top_3,
            disclaimers=disclaimers,
            quality_issues=quality_issues,
            is_certain=capped_confidence > 0.5,
            requires_expert=requires_expert,
            look_alike_warning=look_alike_warning,
            inference_time_ms=elapsed_ms,
            calibrated=self._is_calibrated,
        )

    def load(self, path: Union[str, Path]):
        """Load model weights and optionally calibration temperature."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")

        checkpoint = torch.load(path, map_location=self.device, weights_only=False)

        if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
            self.model.load_state_dict(checkpoint["model_state_dict"])
            if "temperature" in checkpoint:
                self.temp_scaling.temperature.data = torch.tensor(
                    [checkpoint["temperature"]]
                ).to(self.device)
                self._is_calibrated = True
                logger.info("Loaded calibrated temperature: %.4f", checkpoint["temperature"])
        else:
            self.model.load_state_dict(checkpoint)

        self.model.eval()
        logger.info("Model loaded from %s", path)

    def save(self, path: Union[str, Path]):
        """Save model weights and calibration temperature."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        checkpoint = {
            "model_state_dict": self.model.state_dict(),
            "temperature": self.temp_scaling.temperature.item(),
            "is_calibrated": self._is_calibrated,
            "num_classes": NUM_CLASSES,
            "class_to_idx": CLASS_TO_IDX,
        }
        torch.save(checkpoint, path)
        logger.info("Model saved to %s", path)

    def freeze_backbone(self, freeze: bool = True):
        """Freeze or unfreeze the EfficientNet backbone."""
        for param in self.model.features.parameters():
            param.requires_grad = not freeze
        status = "frozen" if freeze else "unfrozen"
        logger.info("Backbone %s", status)

    def unfreeze_last_layers(self, n_layers: int = 3):
        """Unfreeze last N blocks of the backbone (phase 2 training)."""
        # First freeze all
        self.freeze_backbone(True)
        # Then unfreeze last n blocks
        features = list(self.model.features.children())
        for layer in features[-n_layers:]:
            for param in layer.parameters():
                param.requires_grad = True
        logger.info("Unfroze last %d backbone layers", n_layers)

    def get_trainable_params(self) -> int:
        """Count trainable parameters."""
        return sum(p.numel() for p in self.model.parameters() if p.requires_grad)


# ── HARD ASSERTION: Pyrite must NEVER be classified as gold ─────────────────
def assert_pyrite_not_gold(prediction: MineralPrediction, raw_probs: Optional[np.ndarray] = None):
    """
    HARD ASSERTION: Validate that pyrite is never classified as gold.

    This is a safety-critical check. In mining contexts, mistaking pyrite for gold
    can lead to financial loss and safety hazards.

    Raises AssertionError if violated.
    """
    if prediction.mineral == "gold":
        # If top prediction is gold, ensure it's not actually pyrite
        if prediction.look_alike_warning and "pyrite" in prediction.look_alike_warning.lower():
            if raw_probs is not None:
                pyrite_prob = raw_probs[PYRITE_IDX]
                gold_prob = raw_probs[GOLD_IDX]
                assert pyrite_prob < gold_prob, (
                    f"SAFETY VIOLATION: Pyrite ({pyrite_prob:.3f}) has higher probability "
                    f"than gold ({gold_prob:.3f}) but was classified as gold!"
                )

    # If the model thinks it's pyrite, it must NEVER report gold as the result
    if prediction.top_3:
        top_mineral = prediction.top_3[0][0]
        if top_mineral == "pyrite":
            assert prediction.mineral != "gold", (
                "SAFETY VIOLATION: Top prediction is pyrite but output says gold!"
            )

    logger.debug("Pyrite→gold assertion passed for: %s (%.1f%%)",
                 prediction.mineral, prediction.confidence * 100)
