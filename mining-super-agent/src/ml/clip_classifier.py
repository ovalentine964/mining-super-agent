"""
CLIP Zero-Shot Mineral Classifier
===================================
Fallback classifier using pre-trained CLIP for general mineral classification.
Used when EfficientNet is uncertain (below threshold).
Confidence capped at 65% for photo-only identification.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np

try:
    import torch
    import torch.nn.functional as F

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from .data.dataset import MINERAL_CLASSES
from .utils.preprocessing import CLIP_INPUT_SIZE, assess_quality, load_image

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
IMAGE_ONLY_MAX_CONFIDENCE = 0.65
DISCLAIMER_SWAHILI = (
    "Hii si uthibitisho wa maabara. Tafadhali thibitisha na mtihani wa kimwili."
)

# Text prompts for each mineral — multiple prompts per mineral for robustness
MINERAL_PROMPTS: Dict[str, List[str]] = {
    "gold": [
        "a photo of native gold, a yellow metallic mineral",
        "gold nugget or gold vein in rock, shiny yellow metal",
        "a sample of gold ore with visible gold particles",
    ],
    "copper": [
        "a photo of native copper, a reddish metallic mineral",
        "copper ore sample, green patina or reddish metal",
        "a piece of copper mineral with characteristic color",
    ],
    "pyrite": [
        "a photo of pyrite, fool's gold, a brassy yellow cubic mineral",
        "pyrite crystals with metallic luster and cubic crystal form",
        "iron pyrite mineral sample, brass-colored with sharp edges",
    ],
    "chalcopyrite": [
        "a photo of chalcopyrite, a brassy yellow metallic mineral",
        "chalcopyrite ore with iridescent tarnish",
        "a sample of chalcopyrite, golden metallic sulfide mineral",
    ],
    "quartz": [
        "a photo of quartz, a clear or white crystalline mineral",
        "quartz crystal, hexagonal prism shape, glassy luster",
        "a piece of quartz mineral, transparent to translucent",
    ],
    "feldspar": [
        "a photo of feldspar, a white or pink mineral with cleavage",
        "feldspar mineral sample, vitreous luster, blocky crystal",
        "a piece of feldspar, commonly found in granite",
    ],
    "mica": [
        "a photo of mica, a flaky silicate mineral",
        "mica sheets, thin transparent layers that peel apart",
        "a sample of muscovite or biotite mica, perfect basal cleavage",
    ],
    "calcite": [
        "a photo of calcite, a white or clear mineral that fizzes with acid",
        "calcite crystal, rhombohedral shape, vitreous luster",
        "a piece of calcite mineral, double refraction visible",
    ],
    "dolomite": [
        "a photo of dolomite, a pink-tinged carbonate mineral",
        "dolomite crystal, saddle-shaped curved faces",
        "a sample of dolomite rock, similar to limestone",
    ],
    "gypsum": [
        "a photo of gypsum, a soft white mineral",
        "gypsum crystal, selenite form, transparent and flat",
        "a piece of gypsum, very soft, can be scratched with fingernail",
    ],
    "magnetite": [
        "a photo of magnetite, a black magnetic iron oxide mineral",
        "magnetite crystals, octahedral shape, metallic luster",
        "a sample of magnetite, strongly attracted to magnets",
    ],
    "hematite": [
        "a photo of hematite, a dark red to black iron oxide mineral",
        "hematite with metallic luster or red earthy appearance",
        "a piece of hematite, red streak when scratched",
    ],
    "limonite": [
        "a photo of limonite, a yellow-brown iron oxide mineral",
        "limonite, earthy yellow-brown to brown material",
        "a sample of limonite, commonly found as weathering product",
    ],
    "galena": [
        "a photo of galena, a lead sulfide mineral with metallic luster",
        "galena crystals, cubic form, very heavy and metallic gray",
        "a sample of galena, lead ore, high specific gravity",
    ],
    "sphalerite": [
        "a photo of sphalerite, a zinc sulfide mineral",
        "sphalerite with resinous luster, brown to yellow color",
        "a sample of sphalerite, zinc ore, adamantine luster",
    ],
    "fluorite": [
        "a photo of fluorite, a colorful mineral that fluoresces",
        "fluorite crystals, cubic form, purple green or clear",
        "a piece of fluorite, used as flux in steel making",
    ],
    "tourmaline": [
        "a photo of tourmaline, a boron silicate mineral",
        "tourmaline crystal, elongated prismatic, various colors",
        "a sample of tourmaline, striated crystal surface",
    ],
    "garnet": [
        "a photo of garnet, a deep red silicate mineral",
        "garnet crystals, dodecahedral form, glassy luster",
        "a piece of garnet, commonly dark red or brown",
    ],
    "olivine": [
        "a photo of olivine, a green magnesium iron silicate",
        "olivine mineral, peridot gem variety, olive green color",
        "a sample of olivine, found in basalt and mantle rocks",
    ],
    "biotite": [
        "a photo of biotite, a dark brown to black mica mineral",
        "biotite sheets, dark flaky silicate, perfect cleavage",
        "a piece of biotite mica, black to dark brown color",
    ],
}


@dataclass
class CLIPPrediction:
    """CLIP zero-shot prediction result."""
    mineral: str
    confidence: float
    top_3: List[Tuple[str, float]]
    all_scores: Dict[str, float]
    disclaimers: List[str]
    inference_time_ms: float = 0.0
    model_name: str = "clip"

    def to_dict(self) -> dict:
        return {
            "mineral": self.mineral,
            "confidence": round(self.confidence, 4),
            "top_3": [{"mineral": m, "confidence": round(c, 4)} for m, c in self.top_3],
            "all_scores": {k: round(v, 4) for k, v in self.all_scores.items()},
            "disclaimers": self.disclaimers,
            "inference_time_ms": round(self.inference_time_ms, 1),
            "model_name": self.model_name,
        }


class CLIPMineralClassifier:
    """
    CLIP zero-shot mineral classifier.
    Fallback when EfficientNet-B4 is uncertain.
    Confidence is capped at 65% for photo-only identification.
    """

    def __init__(
        self,
        model_name: str = "ViT-B-32",
        pretrained: str = "openai",
        device: Optional[str] = None,
    ):
        if not HAS_TORCH:
            raise ImportError("PyTorch required for CLIPMineralClassifier")

        try:
            import clip
            self._clip = clip
        except ImportError:
            raise ImportError(
                "openai-clip required. Install with: pip install git+https://github.com/openai/CLIP.git"
            )

        self.device = torch.device(
            device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self.model_name = f"clip-{model_name}"

        logger.info("Loading CLIP model: %s (%s)", model_name, pretrained)
        self.model, self.preprocess = self._clip.load(
            model_name, device=self.device, jit=False
        )
        self.model.eval()

        # Precompute text features for all minerals
        self._text_features = self._encode_all_prompts()
        logger.info("CLIP classifier initialized with %d mineral classes", len(MINERAL_CLASSES))

    def _encode_all_prompts(self) -> "torch.Tensor":
        """Encode all mineral text prompts and average per class."""
        all_features = []

        for mineral in MINERAL_CLASSES:
            prompts = MINERAL_PROMPTS.get(mineral, [f"a photo of {mineral} mineral"])
            text_tokens = self._clip.tokenize(prompts).to(self.device)

            with torch.no_grad():
                features = self.model.encode_text(text_tokens)
                features = features / features.norm(dim=-1, keepdim=True)
                # Average across prompts for this mineral
                mean_feature = features.mean(dim=0)
                mean_feature = mean_feature / mean_feature.norm()

            all_features.append(mean_feature)

        return torch.stack(all_features)  # [num_classes, embed_dim]

    def predict(
        self,
        image_source: Union[str, Path, "PIL.Image.Image"],
    ) -> CLIPPrediction:
        """
        Run CLIP zero-shot classification on a single image.
        Confidence capped at 65% for photo-only.
        """
        start_time = time.perf_counter()

        # Load image
        image = load_image(image_source)
        quality = assess_quality(image)

        # Preprocess for CLIP
        image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)

        # Compute similarity
        with torch.no_grad():
            image_features = self.model.encode_image(image_tensor)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)

            # Cosine similarity with all text features
            similarities = (image_features @ self._text_features.T).squeeze(0)

            # Scale to probabilities
            probs = (similarities * 100).softmax(dim=0).cpu().numpy()

        # Build results
        top_indices = np.argsort(probs)[::-1]
        all_scores = {MINERAL_CLASSES[i]: float(probs[i]) for i in range(len(MINERAL_CLASSES))}
        top_3 = [(MINERAL_CLASSES[i], float(probs[i])) for i in top_indices[:3]]

        best_class = MINERAL_CLASSES[top_indices[0]]
        raw_confidence = float(probs[top_indices[0]])

        # CAP confidence at 65% — CLIP cannot be more certain from photos alone
        capped_confidence = min(raw_confidence, IMAGE_ONLY_MAX_CONFIDENCE)

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return CLIPPrediction(
            mineral=best_class,
            confidence=capped_confidence,
            top_3=top_3,
            all_scores=all_scores,
            disclaimers=[DISCLAIMER_SWAHILI],
            inference_time_ms=elapsed_ms,
            model_name=self.model_name,
        )

    def predict_with_custom_prompts(
        self,
        image_source: Union[str, Path, "PIL.Image.Image"],
        custom_prompts: Dict[str, List[str]],
    ) -> CLIPPrediction:
        """
        Predict using custom text prompts (for specialized contexts).
        """
        image = load_image(image_source)
        image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)

        # Encode custom prompts
        text_features_list = []
        labels = list(custom_prompts.keys())

        for prompts in custom_prompts.values():
            text_tokens = self._clip.tokenize(prompts).to(self.device)
            with torch.no_grad():
                features = self.model.encode_text(text_tokens)
                features = features / features.norm(dim=-1, keepdim=True)
                text_features_list.append(features.mean(dim=0))

        text_features = torch.stack(text_features_list)

        with torch.no_grad():
            image_features = self.model.encode_image(image_tensor)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            similarities = (image_features @ text_features.T).squeeze(0)
            probs = (similarities * 100).softmax(dim=0).cpu().numpy()

        top_indices = np.argsort(probs)[::-1]
        all_scores = {labels[i]: float(probs[i]) for i in range(len(labels))}
        top_3 = [(labels[i], float(probs[i])) for i in top_indices[:3]]

        best_class = labels[top_indices[0]]
        capped_confidence = min(float(probs[top_indices[0]]), IMAGE_ONLY_MAX_CONFIDENCE)

        start_time = time.perf_counter()

        return CLIPPrediction(
            mineral=best_class,
            confidence=capped_confidence,
            top_3=top_3,
            all_scores=all_scores,
            disclaimers=[DISCLAIMER_SWAHILI],
            inference_time_ms=0.0,
            model_name=self.model_name,
        )
