"""
Satellite imagery analyzer — Sentinel-2 spectral indices and alteration mapping.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SpectralIndices:
    """Computed spectral indices from Sentinel-2 imagery."""
    ndvi: Optional[np.ndarray] = None
    clay_ratio: Optional[np.ndarray] = None
    iron_oxide: Optional[np.ndarray] = None
    ndsi: Optional[np.ndarray] = None


@dataclass
class AlterationZone:
    """Detected alteration zone."""
    zone_type: str  # "clay", "iron_oxide", "silicification"
    confidence: float
    area_pixels: int
    bbox: tuple  # (min_x, min_y, max_x, max_y)
    geojson: Optional[Dict] = None


def calculate_ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    """Calculate Normalized Difference Vegetation Index."""
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = (nir.astype(float) - red.astype(float)) / (nir.astype(float) + red.astype(float))
        ndvi = np.where(np.isfinite(ndvi), ndvi, 0)
    return np.clip(ndvi, -1, 1)


def calculate_clay_ratio(swir1: np.ndarray, swir2: np.ndarray) -> np.ndarray:
    """Calculate clay mineral ratio (SWIR1/SWIR2)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = swir1.astype(float) / (swir2.astype(float) + 1e-10)
    return np.clip(ratio, 0, 2)


def calculate_iron_oxide_ratio(red: np.ndarray, blue: np.ndarray) -> np.ndarray:
    """Calculate iron oxide ratio (Red/Blue)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = red.astype(float) / (blue.astype(float) + 1e-10)
    return np.clip(ratio, 0, 5)


def detect_alteration_zones(
    bands: Dict[str, np.ndarray],
    threshold_clay: float = 1.2,
    threshold_iron: float = 2.0,
) -> List[AlterationZone]:
    """Detect hydrothermal alteration zones from Sentinel-2 bands."""
    zones = []

    # Clay alteration (SWIR1/SWIR2 > threshold)
    if "swir1" in bands and "swir2" in bands:
        clay = calculate_clay_ratio(bands["swir1"], bands["swir2"])
        clay_mask = clay > threshold_clay
        if clay_mask.any():
            area = int(clay_mask.sum())
            ys, xs = np.where(clay_mask)
            zones.append(AlterationZone(
                zone_type="clay", confidence=min(0.9, area / 10000),
                area_pixels=area,
                bbox=(int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())),
            ))

    # Iron oxide alteration (Red/Blue > threshold)
    if "red" in bands and "blue" in bands:
        iron = calculate_iron_oxide_ratio(bands["red"], bands["blue"])
        iron_mask = iron > threshold_iron
        if iron_mask.any():
            area = int(iron_mask.sum())
            ys, xs = np.where(iron_mask)
            zones.append(AlterationZone(
                zone_type="iron_oxide", confidence=min(0.9, area / 10000),
                area_pixels=area,
                bbox=(int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())),
            ))

    return zones
