"""
EfficientNet-B4 Mineral Classifier with safety-critical pyrite→gold prevention.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Union

import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torchvision import models
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from .data.dataset import CLASS_TO_IDX, IDX_TO_CLASS, LOOK_ALIKE_PAIRS, MINERAL_CLASSES, NUM_CLASSES
from .utils.preprocessing import assess_quality, get_efficientnet_transforms, load_image

logger = logging.getLogger(__name__)

IMAGE_ONLY_MAX_CONFIDENCE = 0.65
MIN_CONFIDENCE_THRESHOLD = 0.10
PYRITE_IDX = CLASS_TO_IDX["pyrite"]
GOLD_IDX = CLASS_TO_IDX["gold"]
DISCLAIMER_SWAHILI = "Hii si uthibitisho wa maabara. Tafadhali thibitisha na mtihani wa kimwili."
DISCLAIMER_ENGLISH = "This is not laboratory confirmation. Please verify with physical testing."


@dataclass
class MineralPrediction:
    mineral: str
    confidence: float
    top_3: List[Tuple[str, float]]
    disclaimers: List[str]
    quality_issues: List[str]
    is_certain: bool
    requires_expert: bool
    look_alike_warning: Optional[str] = None
    inference_time_ms: float = 0.0

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
        }


class MineralClassifier:
    """EfficientNet-B4 mineral classifier with safety checks."""

    def __init__(self, model_path: Optional[Union[str, Path]] = None, device: Optional[str] = None):
        if not HAS_TORCH:
            raise ImportError("PyTorch required for MineralClassifier")

        self.device = torch.device(device if device else ("cuda" if torch.cuda.is_available() else "cpu"))
        self.model = self._build_model()
        self.model.to(self.device)
        self.model.eval()
        self.transform = get_efficientnet_transforms(training=False)
        self.economic_minerals = {"gold", "copper", "galena", "sphalerite"}

        if model_path:
            self.load(model_path)

    def _build_model(self) -> nn.Module:
        model = models.efficientnet_b4(weights=models.EfficientNet_B4_Weights.DEFAULT)
        in_features = model.classifier[1].in_features
        model.classifier = nn.Sequential(
            nn.Dropout(p=0.4), nn.Linear(in_features, 512), nn.ReLU(),
            nn.Dropout(p=0.2), nn.Linear(512, NUM_CLASSES),
        )
        return model

    def predict(self, image_source: Union[str, Path, "PIL.Image.Image"]) -> MineralPrediction:
        start_time = time.perf_counter()
        image = load_image(image_source)
        quality = assess_quality(image)
        tensor = self.transform(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = self.model(tensor)
            probs = F.softmax(logits, dim=1).squeeze(0).cpu().numpy()

        top_indices = np.argsort(probs)[::-1]
        top_3 = [(IDX_TO_CLASS[i], float(probs[i])) for i in top_indices[:3]]
        best_idx = top_indices[0]
        best_class = IDX_TO_CLASS[best_idx]
        best_confidence = float(probs[best_idx])

        capped_confidence = min(best_confidence, IMAGE_ONLY_MAX_CONFIDENCE)
        disclaimers = [DISCLAIMER_SWAHILI, DISCLAIMER_ENGLISH]
        quality_issues = quality.issues if not quality.is_usable else []
        look_alike_warning = None
        requires_expert = False

        # Pyrite→gold safety
        if best_idx == PYRITE_IDX and best_confidence > 0.3:
            gold_prob = float(probs[GOLD_IDX])
            if gold_prob > 0.05:
                look_alike_warning = (
                    f"WARNING: This sample has characteristics of pyrite (fool's gold). "
                    f"Gold probability: {gold_prob:.1%}. Pyrite: {best_confidence:.1%}. "
                    f"Physical testing is MANDATORY."
                )
                disclaimers.append(look_alike_warning)

        if best_idx == GOLD_IDX:
            pyrite_prob = float(probs[PYRITE_IDX])
            # HARD BLOCK: If pyrite probability > 0.3, NEVER return gold
            if pyrite_prob > 0.3:
                best_class = "pyrite"
                best_idx = PYRITE_IDX
                capped_confidence = min(capped_confidence, 0.40)
                look_alike_warning = (
                    f"BLOCKED: High pyrite probability ({pyrite_prob:.1%}). "
                    f"Reclassified as pyrite. Gold probability was {best_confidence:.1%}. "
                    f"Physical testing (streak, hardness, XRF) is MANDATORY."
                )
                disclaimers.append(look_alike_warning)
            elif pyrite_prob > 0.1:
                look_alike_warning = (
                    f"CAUTION: This may be gold OR pyrite. "
                    f"Gold: {best_confidence:.1%}, Pyrite: {pyrite_prob:.1%}. "
                    f"Mandatory: streak test, hardness test, XRF analysis."
                )
                disclaimers.append(look_alike_warning)
                if pyrite_prob > 0.2:
                    capped_confidence = min(capped_confidence, 0.40)

        # Look-alike pairs
        for pair in LOOK_ALIKE_PAIRS:
            pair_indices = [CLASS_TO_IDX[p] for p in pair]
            if best_idx in pair_indices:
                other_idx = pair_indices[0] if pair_indices[1] == best_idx else pair_indices[1]
                other_prob = float(probs[other_idx])
                if other_prob > 0.15:
                    look_alike_warning = (
                        f"WARNING: {IDX_TO_CLASS[best_idx]} and {IDX_TO_CLASS[other_idx]} "
                        f"are commonly confused. Probabilities: {best_confidence:.1%} vs {other_prob:.1%}."
                    )
                    disclaimers.append(look_alike_warning)

        if best_class in self.economic_minerals:
            requires_expert = True
            disclaimers.append(
                f"ALERT: {best_class.upper()} is an economic mineral. "
                f"Professional geological survey required."
            )

        if capped_confidence < MIN_CONFIDENCE_THRESHOLD:
            disclaimers.append("Confidence too low. Please provide a clearer photo.")

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return MineralPrediction(
            mineral=best_class, confidence=capped_confidence, top_3=top_3,
            disclaimers=disclaimers, quality_issues=quality_issues,
            is_certain=capped_confidence > 0.5, requires_expert=requires_expert,
            look_alike_warning=look_alike_warning, inference_time_ms=elapsed_ms,
        )

    def load(self, path: Union[str, Path]):
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Model not found: {path}")
        checkpoint = torch.load(path, map_location=self.device, weights_only=False)
        if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
            self.model.load_state_dict(checkpoint["model_state_dict"])
        else:
            self.model.load_state_dict(checkpoint)
        self.model.eval()
        logger.info("Model loaded from %s", path)

    def save(self, path: Union[str, Path]):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({"model_state_dict": self.model.state_dict(), "num_classes": NUM_CLASSES}, path)
        logger.info("Model saved to %s", path)
