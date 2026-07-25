"""
CLIP zero-shot mineral classifier — fallback when EfficientNet is uncertain.
Confidence capped at 65% for photo-only identification.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np

try:
    import torch
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from .data.dataset import MINERAL_CLASSES
from .utils.preprocessing import load_image

logger = logging.getLogger(__name__)

IMAGE_ONLY_MAX_CONFIDENCE = 0.65
DISCLAIMER_SWAHILI = "Hii si uthibitisho wa maabara. Tafadhali thibitisha na mtihani wa kimwili."


@dataclass
class CLIPPrediction:
    mineral: str
    confidence: float
    top_3: List[Tuple[str, float]]
    all_scores: Dict[str, float]
    disclaimers: List[str]
    inference_time_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "mineral": self.mineral,
            "confidence": round(self.confidence, 4),
            "top_3": [{"mineral": m, "confidence": round(c, 4)} for m, c in self.top_3],
            "disclaimers": self.disclaimers,
            "inference_time_ms": round(self.inference_time_ms, 1),
        }


class CLIPMineralClassifier:
    """CLIP zero-shot mineral classifier. Fallback for EfficientNet."""

    def __init__(self, model_name: str = "ViT-B-32", pretrained: str = "openai", device: Optional[str] = None):
        if not HAS_TORCH:
            raise ImportError("PyTorch required")

        try:
            import clip
            self._clip = clip
        except ImportError:
            raise ImportError("openai-clip required: pip install git+https://github.com/openai/CLIP.git")

        self.device = torch.device(device if device else ("cuda" if torch.cuda.is_available() else "cpu"))
        self.model, self.preprocess = self._clip.load(model_name, device=self.device, jit=False)
        self.model.eval()
        self._text_features = self._encode_all_prompts()
        logger.info("CLIP classifier initialized with %d mineral classes", len(MINERAL_CLASSES))

    def _encode_all_prompts(self) -> "torch.Tensor":
        prompts_per_mineral = {
            "gold": ["a photo of native gold, yellow metallic mineral", "gold nugget in rock"],
            "pyrite": ["a photo of pyrite, fool's gold, brassy yellow cubic mineral", "pyrite crystals"],
            "quartz": ["a photo of quartz, clear or white crystalline mineral", "quartz crystal"],
            "copper": ["a photo of native copper, reddish metallic mineral", "copper ore sample"],
        }
        all_features = []
        for mineral in MINERAL_CLASSES:
            prompts = prompts_per_mineral.get(mineral, [f"a photo of {mineral} mineral"])
            text_tokens = self._clip.tokenize(prompts).to(self.device)
            with torch.no_grad():
                features = self.model.encode_text(text_tokens)
                features = features / features.norm(dim=-1, keepdim=True)
                mean_feature = features.mean(dim=0)
                mean_feature = mean_feature / mean_feature.norm()
            all_features.append(mean_feature)
        return torch.stack(all_features)

    def predict(self, image_source: Union[str, Path, "PIL.Image.Image"]) -> CLIPPrediction:
        start_time = time.perf_counter()
        image = load_image(image_source)
        image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            image_features = self.model.encode_image(image_tensor)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            similarities = (image_features @ self._text_features.T).squeeze(0)
            probs = (similarities * 100).softmax(dim=0).cpu().numpy()

        top_indices = np.argsort(probs)[::-1]
        all_scores = {MINERAL_CLASSES[i]: float(probs[i]) for i in range(len(MINERAL_CLASSES))}
        top_3 = [(MINERAL_CLASSES[i], float(probs[i])) for i in top_indices[:3]]
        best_class = MINERAL_CLASSES[top_indices[0]]
        capped_confidence = min(float(probs[top_indices[0]]), IMAGE_ONLY_MAX_CONFIDENCE)
        disclaimers = [DISCLAIMER_SWAHILI]

        # HARD BLOCK: If pyrite is in top-3 and prediction is gold, reclassify as pyrite
        top_3_classes = [m for m, _ in top_3]
        if "pyrite" in top_3_classes and best_class == "gold":
            pyrite_score = all_scores.get("pyrite", 0.0)
            best_class = "pyrite"
            capped_confidence = min(capped_confidence, 0.40)
            disclaimers.append(
                f"BLOCKED: Pyrite detected in top-3 (score: {pyrite_score:.4f}). "
                f"Reclassified as pyrite. Physical testing MANDATORY."
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return CLIPPrediction(
            mineral=best_class, confidence=capped_confidence, top_3=top_3,
            all_scores=all_scores, disclaimers=disclaimers, inference_time_ms=elapsed_ms,
        )
