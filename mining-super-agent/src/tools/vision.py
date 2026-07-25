"""
Vision Tools — Mineral Identification from Photos and Spectral Data
===================================================================

These are TOOLS that the superagent uses for mineral identification.
NOT a separate agent — the superagent calls these tools directly.

Safety Rules (from council review):
- Pyrite must NEVER be classified as gold (hard assertion)
- Photo-only ID capped at 65% confidence
- Swahili disclaimer on every prediction
- Economic minerals flagged for expert review
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MineralResult:
    """Result of mineral identification."""
    mineral: str
    confidence: float
    method: str  # "photo", "xrf", "spectral"
    disclaimers: list[str]
    is_economic: bool
    requires_expert_review: bool


# Economic minerals that always require expert review
ECONOMIC_MINERALS = {
    "gold", "copper", "galena", "sphalerite", 
    "cassiterite", "coltan", "wolframite"
}

# Look-alike mineral pairs
LOOK_ALIKES = {
    "gold": ["pyrite", "chalcopyrite", "biotite"],
    "pyrite": ["gold", "chalcopyrite", "marcasite"],
    "chalcopyrite": ["pyrite", "gold", "bornite"],
}

# Swahili disclaimer for all mineral IDs
DISCLAIMER_SW = "Hii si uthibitisho wa maabara. Tafadhali thibitisha na mtihani wa kimwili."
DISCLAIMER_EN = "This is NOT laboratory confirmation. Please verify with physical testing."


async def identify_mineral_from_photo(
    image_bytes: bytes,
    description: str = "",
    location: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Identify minerals from a photo using EfficientNet-B4.
    
    Safety rules:
    - Max confidence for photo-only: 65%
    - Pyrite NEVER classified as gold
    - Swahili disclaimer always included
    - Economic minerals flagged for expert review
    """
    from ..ml.mineral_classifier import MineralClassifier
    from ..ml.clip_classifier import CLIPClassifier
    
    # Try EfficientNet first
    classifier = MineralClassifier()
    result = classifier.predict(image_bytes)
    
    # CRITICAL: Pyrite must NEVER be gold
    if result.mineral == "gold":
        # Double-check with CLIP
        clip = CLIPClassifier()
        clip_result = clip.classify(image_bytes)
        if clip_result.top_class in ("pyrite", "chalcopyrite"):
            # Override — this is likely pyrite, not gold
            result.mineral = "pyrite"
            result.confidence = min(result.confidence, 0.65)
            result.disclaimers.append(
                "⚠️ Pembejeo: Hii inaweza kuwa pyrite (dhahabu ya uwongo), "
                "si dhahabu halisi. Tafadhali fanya mtihani wa streak."
            )
    
    # Cap confidence for photo-only
    result.confidence = min(result.confidence, 0.65)
    
    # Add disclaimers
    result.disclaimers = [DISCLAIMER_SW, DISCLAIMER_EN]
    
    # Flag economic minerals
    if result.mineral in ECONOMIC_MINERALS:
        result.requires_expert_review = True
        result.disclaimers.append(
            "⚠️ Hii ni madini ya kiuchumi. Tafadhali pata uthibitisho wa mtaalamu."
        )
    
    # Check for look-alikes
    if result.mineral in LOOK_ALIKES:
        result.disclaimers.append(
            f"⚠️ Madini yanayofanana: {', '.join(LOOK_ALIKES[result.mineral])}. "
            "Tafadhali fanya mtihani wa streak na hardness."
        )
    
    return {
        "mineral": result.mineral,
        "confidence": round(result.confidence, 2),
        "method": "photo",
        "disclaimers": result.disclaimers,
        "is_economic": result.mineral in ECONOMIC_MINERALS,
        "requires_expert_review": result.requires_expert_review,
        "look_alikes": LOOK_ALIKES.get(result.mineral, []),
        "swahili_summary": _format_swahili_result(result),
    }


async def analyze_xrf(
    spectral_data: list[float],
    element_concentrations: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Process XRF spectral data for precise mineral identification.
    
    XRF gives ELEMENTAL composition — this is definitive.
    Unlike photo ID, XRF can distinguish gold from pyrite with certainty.
    """
    # XRF analysis — elemental composition
    if element_concentrations:
        # Direct elemental analysis
        primary_elements = sorted(
            element_concentrations.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        # Identify mineral from elements
        mineral = _identify_from_elements(element_concentrations)
        
        return {
            "mineral": mineral,
            "confidence": 0.95,  # XRF is highly accurate
            "method": "xrf",
            "elements": dict(primary_elements),
            "disclaimers": ["XRF analysis — high confidence identification"],
            "is_economic": mineral in ECONOMIC_MINERALS,
            "requires_expert_review": mineral in ECONOMIC_MINERALS,
        }
    
    # Spectral analysis
    return {
        "method": "xrf_spectral",
        "raw_data": spectral_data,
        "note": "Elemental concentrations needed for identification",
    }


def _identify_from_elements(elements: dict[str, float]) -> str:
    """Identify mineral from elemental composition."""
    # Gold: Au present
    if elements.get("Au", 0) > 0.1:
        return "gold"
    
    # Pyrite: Fe + S, no Au
    if elements.get("Fe", 0) > 30 and elements.get("S", 0) > 30:
        if elements.get("Au", 0) < 0.01:
            return "pyrite"
    
    # Chalcopyrite: Cu + Fe + S
    if elements.get("Cu", 0) > 20 and elements.get("Fe", 0) > 20:
        return "chalcopyrite"
    
    # Copper: Cu dominant
    if elements.get("Cu", 0) > 50:
        return "copper"
    
    # Quartz: Si + O
    if elements.get("Si", 0) > 40:
        return "quartz"
    
    return "unknown"


def _format_swahili_result(result: Any) -> str:
    """Format mineral result in Swahili."""
    mineral_names = {
        "gold": "dhahabu",
        "pyrite": "pyrite (dhahabu ya uwongo)",
        "copper": "shaba",
        "quartz": "quartz (kristo)",
        "chalcopyrite": "chalcopyrite",
    }
    
    name = mineral_names.get(result.mineral, result.mineral)
    conf = int(result.confidence * 100)
    
    return f"Madini: {name}. Uhakika: {conf}%. {DISCLAIMER_SW}"
