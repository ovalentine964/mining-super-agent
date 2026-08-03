"""Base utilities for the agent system — confidence calibration, tool definitions."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConfidenceLevel(Enum):
    """Standardized confidence levels for agent outputs."""
    VERY_LOW = "very_low"      # < 0.3
    LOW = "low"                # 0.3 - 0.5
    MEDIUM = "medium"          # 0.5 - 0.7
    HIGH = "high"              # 0.7 - 0.9
    VERY_HIGH = "very_high"    # > 0.9


@dataclass
class ToolDefinition:
    """Defines a tool available to an agent."""
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    required: list[str] = field(default_factory=list)


def calibrate_confidence(
    raw_confidence: float,
    evidence_count: int = 0,
    source_reliability: float = 0.5,
    method_limitation: float = 0.0,
) -> float:
    """
    Calibrate a raw confidence score using multiple factors.

    Returns a value between 0.05 and 0.95 (never 0 or 1).
    
    Council requirement: "Image-based mineral ID capped at 65% confidence"
    is enforced elsewhere. This is the general calibration function.
    """
    # Clamp raw input
    raw = max(0.0, min(1.0, raw_confidence))

    # Evidence factor: more evidence = more confidence, but diminishing returns
    # 0 evidence → 0.5x, 5 evidence → 0.85x, 20+ evidence → ~1.0x
    evidence_factor = 1.0 - (0.5 / (1.0 + evidence_count * 0.3))

    # Source reliability directly scales confidence
    reliability_factor = max(0.1, source_reliability)

    # Method limitation reduces confidence
    limitation_penalty = max(0.0, method_limitation)

    # Combine factors
    calibrated = raw * evidence_factor * reliability_factor * (1.0 - limitation_penalty)

    # Apply sigmoid-like smoothing to avoid extremes
    # This ensures we never return exactly 0 or 1
    smoothed = 0.05 + 0.9 * (1 / (1 + math.exp(-5 * (calibrated - 0.5))))

    return max(0.05, min(0.95, smoothed))


def get_confidence_level(score: float) -> ConfidenceLevel:
    """Map a numeric confidence score to a ConfidenceLevel enum."""
    if score < 0.3:
        return ConfidenceLevel.VERY_LOW
    elif score < 0.5:
        return ConfidenceLevel.LOW
    elif score < 0.7:
        return ConfidenceLevel.MEDIUM
    elif score < 0.9:
        return ConfidenceLevel.HIGH
    else:
        return ConfidenceLevel.VERY_HIGH
