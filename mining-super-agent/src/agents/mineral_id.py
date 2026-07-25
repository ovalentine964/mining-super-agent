"""
Mineral Identifier Agent — Photo-based mineral identification.

Key design decisions (from council review):
- EfficientNet-B4 as primary (not CLIP — CLIP unreliable for minerals)
- CLIP only for general classification (preliminary)
- Look-alike detection (gold vs pyrite is the $40B question)
- Physical test integration (streak, hardness, specific gravity)
- Confidence cap: 65% for photo-only identification
- ALWAYS recommends physical verification for economic minerals
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .base import (
    AgentResult,
    BaseAgent,
    ToolDefinition,
    calibrate_confidence,
)

logger = logging.getLogger(__name__)

# Look-alike pairs — critical for preventing costly misidentification
LOOK_ALIKES = {
    "gold": {
        "common_fakes": ["pyrite", "chalcopyrite", "copper", "mica", "biotite"],
        "distinguishing_tests": [
            "Streak test: gold → yellow streak; pyrite → greenish-black streak",
            "Hardness: gold → 2.5-3 (soft, scratches with copper coin); pyrite → 6-6.5 (harder than glass)",
            "Specific gravity: gold → 19.3 (very heavy); pyrite → 5.0 (much lighter)",
            "Shape: gold → irregular, nuggety; pyrite → cubic crystals",
            "Malleability: gold → deforms without breaking; pyrite → brittle, crumbles",
        ],
        "photo_reliability": "LOW — gold and pyrite look nearly identical in photos",
    },
    "copper": {
        "common_fakes": ["chalcopyrite", "bornite", "malachite", "limonite"],
        "distinguishing_tests": [
            "Streak test: copper → copper-red streak; chalcopyrite → greenish-black",
            "Hardness: copper → 2.5-3; chalcopyrite → 3.5-4",
            "Green patina: copper develops distinctive green malachite coating",
        ],
        "photo_reliability": "MODERATE — copper has distinctive color but can be confused",
    },
    "diamond": {
        "common_fakes": ["quartz", "cubic zirconia", "moissanite", "topaz"],
        "distinguishing_tests": [
            "Hardness test: diamond scratches everything (10 on Mohs scale)",
            "Thermal conductivity: diamond disperses heat rapidly",
            "Crystal shape: octahedral or dodecahedral",
        ],
        "photo_reliability": "VERY LOW — cannot reliably identify diamonds from photos",
    },
}


class MineralIdAgent(BaseAgent):
    """Mineral identification agent using vision models + physical tests."""

    def __init__(self):
        tools = [
            ToolDefinition(
                name="identify_mineral_photo",
                description="Identify a mineral from a photograph using EfficientNet-B4 model.",
                parameters={
                    "type": "object",
                    "properties": {
                        "image_path": {"type": "string", "description": "Path to the mineral photo"},
                        "context": {"type": "string", "description": "Additional context (location, associated minerals)"},
                    },
                    "required": ["image_path"],
                },
                permissions=["read:vision"],
            ),
            ToolDefinition(
                name="check_look_alikes",
                description="Check if a mineral has common look-alikes and what tests distinguish them.",
                parameters={
                    "type": "object",
                    "properties": {
                        "mineral": {"type": "string", "description": "Mineral name to check"},
                    },
                    "required": ["mineral"],
                },
                permissions=["read:vision"],
            ),
            ToolDefinition(
                name="record_physical_test",
                description="Record results of a physical test (streak, hardness, SG) to refine identification.",
                parameters={
                    "type": "object",
                    "properties": {
                        "mineral_candidate": {"type": "string", "description": "Mineral being tested"},
                        "test_type": {
                            "type": "string",
                            "enum": ["streak", "hardness", "specific_gravity", "magnetism", "acid_test"],
                        },
                        "result": {"type": "string", "description": "Test result"},
                    },
                    "required": ["mineral_candidate", "test_type", "result"],
                },
                permissions=["read:vision"],
            ),
            ToolDefinition(
                name="classify_with_clip",
                description="General mineral classification using CLIP (preliminary only — not reliable for specific ID).",
                parameters={
                    "type": "object",
                    "properties": {
                        "image_path": {"type": "string", "description": "Path to the image"},
                        "categories": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Mineral categories to classify against",
                        },
                    },
                    "required": ["image_path"],
                },
                permissions=["read:vision"],
            ),
        ]

        super().__init__(
            name="MineralId",
            description=(
                "Identifies minerals from photographs and physical test results. "
                "Uses EfficientNet-B4 as primary classifier. "
                "CRITICAL: Photo-only identification is capped at 65% confidence. "
                "Physical verification is ALWAYS recommended for economic minerals."
            ),
            model_id="meta/llama-3.1-8b-instruct",
            permissions={"read:vision", "model:efficientnet", "model:clip"},
            tools=tools,
            system_prompt=self._build_system_prompt(),
        )

    def _build_system_prompt(self) -> str:
        return """You are a mineral identification specialist.

IDENTIFICATION METHOD:
1. PRIMARY: EfficientNet-B4 trained on mineral photo dataset (85-92% accuracy in lab)
2. SECONDARY: CLIP for general category (preliminary only — unreliable for specific ID)
3. TERNARY: Physical test results (streak, hardness, specific gravity)

CRITICAL RULES:
1. Photo-only identification is CAPPED at 65% confidence
   - Even if the model says 95%, report max 65% for photo-only
   - Reason: lighting, angle, weathering, and look-alikes make photos unreliable
2. For ECONOMIC minerals (gold, copper, diamond, coltan):
   - ALWAYS recommend physical verification
   - ALWAYS check look-alikes
   - NEVER give a definitive ID from photos alone
3. Physical tests increase confidence:
   - Streak test: +10-15% confidence
   - Hardness test: +10-15% confidence
   - Specific gravity: +15-20% confidence
   - Multiple consistent tests: up to 85% confidence

LOOK-ALIKE AWARENESS:
- Gold vs Pyrite: The #1 misidentification risk. Nearly identical in photos.
  Gold: soft (2.5), heavy (SG 19.3), yellow streak, malleable
  Pyrite: hard (6.5), light (SG 5.0), greenish-black streak, brittle

- Copper vs Chalcopyrite: Both look metallic/golden
  Copper: copper-red streak, soft, develops green patina
  Chalcopyrite: greenish-black streak, harder, no patina

REPORTING FORMAT:
Always report:
1. Top 3 most likely minerals with confidence scores
2. Look-alike warnings if applicable
3. Recommended physical tests to confirm
4. Whether professional lab analysis is recommended
"""

    async def run(self, task: str, context: Optional[dict[str, Any]] = None) -> AgentResult:
        """Run mineral identification."""
        result = await super().run(task, context)

        # Enforce disclaimers
        result.disclaimers.extend([
            "Photo-only mineral identification is limited to 65% confidence. "
            "Physical testing (streak, hardness, specific gravity) is required for reliable identification.",
            "For any mineral with economic value (gold, copper, diamonds, etc.), "
            "professional laboratory analysis (XRF, XRD, or assay) is MANDATORY before any economic decisions.",
            "This tool is for preliminary screening only. It is NOT a substitute for "
            "professional geological assessment.",
        ])

        # Cap confidence for photo-only
        if result.confidence > 0.65:
            has_physical_tests = any(
                "physical" in str(tc.data).lower() or "streak" in str(tc.data).lower()
                for tc in result.tool_calls
                if tc.success
            )
            if not has_physical_tests:
                result.confidence = 0.65
                result.warnings.append(
                    "Confidence capped at 65% — photo-only identification without physical tests."
                )

        return result


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

async def identify_mineral_photo(
    image_path: str,
    context: str = "",
) -> dict[str, Any]:
    """
    Identify mineral from photo using EfficientNet-B4.
    In production, loads the model and runs inference.
    """
    # Mock — replace with actual EfficientNet-B4 inference
    # Model: timm.create_model('efficientnet_b4', num_classes=N_MINERALS)
    return {
        "image_path": image_path,
        "predictions": [
            {"mineral": "Pyrite", "confidence": 0.72, "model": "EfficientNet-B4"},
            {"mineral": "Gold", "confidence": 0.15, "model": "EfficientNet-B4"},
            {"mineral": "Chalcopyrite", "confidence": 0.08, "model": "EfficientNet-B4"},
        ],
        "look_alike_warning": (
            "⚠️ HIGH RISK: Top prediction (Pyrite) is commonly confused with Gold. "
            "Physical testing is MANDATORY before any conclusion."
        ),
        "cap_applied": True,
        "effective_confidence": 0.65,  # Capped from 0.72
        "recommended_tests": [
            "Streak test: scratch on unglazed porcelain. Pyrite → greenish-black. Gold → yellow.",
            "Hardness test: try to scratch with copper coin. Pyrite resists. Gold scratches.",
            "Weight: gold is 4x heavier than pyrite for the same size.",
        ],
    }


async def check_look_alikes(mineral: str) -> dict[str, Any]:
    """Check if a mineral has known look-alikes."""
    mineral_lower = mineral.lower()
    if mineral_lower in LOOK_ALIKES:
        info = LOOK_ALIKES[mineral_lower]
        return {
            "mineral": mineral,
            "has_look_alikes": True,
            "common_fakes": info["common_fakes"],
            "distinguishing_tests": info["distinguishing_tests"],
            "photo_reliability": info["photo_reliability"],
        }
    return {
        "mineral": mineral,
        "has_look_alikes": False,
        "note": "No common look-alikes recorded for this mineral.",
    }


async def record_physical_test(
    mineral_candidate: str,
    test_type: str,
    result: str,
) -> dict[str, Any]:
    """Record a physical test result and update identification confidence."""
    # Analyze test result against expected values
    consistency = "unknown"
    confidence_boost = 0.0

    if mineral_candidate.lower() == "gold" and test_type == "streak":
        if "yellow" in result.lower():
            consistency = "CONSISTENT with gold"
            confidence_boost = 0.15
        elif "black" in result.lower() or "green" in result.lower():
            consistency = "INCONSISTENT with gold — likely pyrite"
            confidence_boost = -0.30

    elif mineral_candidate.lower() == "gold" and test_type == "hardness":
        if "soft" in result.lower() or "scratched" in result.lower():
            consistency = "CONSISTENT with gold (soft, ~2.5 Mohs)"
            confidence_boost = 0.12
        elif "hard" in result.lower() or "resists" in result.lower():
            consistency = "INCONSISTENT with gold — likely pyrite (~6.5 Mohs)"
            confidence_boost = -0.25

    return {
        "mineral": mineral_candidate,
        "test": test_type,
        "result": result,
        "consistency": consistency,
        "confidence_adjustment": confidence_boost,
        "note": "Physical tests significantly improve identification reliability.",
    }


async def classify_with_clip(
    image_path: str,
    categories: list[str] = None,
) -> dict[str, Any]:
    """
    General classification using CLIP.
    WARNING: CLIP is unreliable for specific mineral identification.
    Use only for general category screening.
    """
    if categories is None:
        categories = ["mineral", "rock", "ore", "metallic", "non-metallic"]

    # Mock — replace with actual CLIP inference
    return {
        "image_path": image_path,
        "categories": categories,
        "predictions": [
            {"category": "mineral", "confidence": 0.85},
            {"category": "metallic", "confidence": 0.72},
            {"category": "ore", "confidence": 0.45},
        ],
        "warning": (
            "CLIP classification is PRELIMINARY ONLY. "
            "It cannot reliably distinguish between similar-looking minerals. "
            "Use EfficientNet-B4 for specific identification."
        ),
    }
