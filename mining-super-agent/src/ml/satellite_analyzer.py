"""
Satellite Image Analyzer
=========================
Sentinel-2 band math, NDVI, clay indices, iron oxide indices,
alteration mapping, cloud cover detection, multi-temporal analysis.

Uses freely available Sentinel-2 data via Planetary Computer or local files.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)


# ── Sentinel-2 Band Definitions ───────────────────────────────────────────────
class S2Band(Enum):
    """Sentinel-2 spectral bands."""
    B02 = "blue"        # 490 nm
    B03 = "green"       # 560 nm
    B04 = "red"         # 665 nm
    B05 = "rededge1"    # 705 nm
    B06 = "rededge2"    # 740 nm
    B07 = "rededge3"    # 783 nm
    B08 = "nir"         # 842 nm
    B8A = "nir_narrow"  # 865 nm
    B11 = "swir1"       # 1610 nm
    B12 = "swir2"       # 2190 nm


@dataclass
class SatelliteScene:
    """A single Sentinel-2 scene with all bands."""
    bands: Dict[str, np.ndarray]  # band_name → 2D array (reflectance 0-1)
    metadata: Dict[str, Any]
    cloud_mask: Optional[np.ndarray] = None
    date: Optional[datetime] = None
    bbox: Optional[Tuple[float, float, float, float]] = None  # (min_lon, min_lat, max_lon, max_lat)

    def get_band(self, band: S2Band) -> np.ndarray:
        """Get band array by enum."""
        key = band.value
        if key not in self.bands:
            # Try name alias
            for k, v in self.bands.items():
                if band.name.lower() in k.lower() or band.value.lower() in k.lower():
                    return v
            raise KeyError(f"Band {band.name} not found in scene")
        return self.bands[key]


@dataclass
class AlterationMap:
    """Results of alteration mapping."""
    clay_minerals: np.ndarray      # Clay alteration index
    iron_oxide: np.ndarray         # Iron oxide index
    ferrous_minerals: np.ndarray   # Ferrous iron index
    ndvi: np.ndarray               # Vegetation index
    ndsi: np.ndarray               # Snow index
    alteration_zones: np.ndarray   # Classified alteration zones
    summary: Dict[str, float]      # Percentage of each alteration type


@dataclass
class SatelliteAnalysis:
    """Complete satellite analysis result."""
    indices: Dict[str, np.ndarray]
    alteration_map: Optional[AlterationMap]
    cloud_coverage_pct: float
    usable: bool
    recommendations: List[str]
    metadata: Dict[str, Any]


class SatelliteAnalyzer:
    """
    Analyze Sentinel-2 satellite imagery for mineral exploration.

    Computes spectral indices for alteration mapping:
    - NDVI (vegetation stress → possible mineralization)
    - Clay indices (argillic alteration)
    - Iron oxide indices (gossan/oxidation)
    - Ferrous mineral indices

    CPU-only, works with local GeoTIFF files.
    """

    # Spectral index thresholds
    NDVI_THRESHOLDS = {"bare": 0.1, "sparse": 0.3, "moderate": 0.5, "dense": 0.7}
    CLAY_THRESHOLD = 0.15     # Above this = clay alteration present
    IRON_THRESHOLD = 0.3      # Above this = iron oxide enrichment
    CLOUD_THRESHOLD = 0.2     # Max acceptable cloud coverage

    def __init__(self):
        logger.info("SatelliteAnalyzer initialized (CPU mode)")

    def analyze_scene(self, scene: SatelliteScene) -> SatelliteAnalysis:
        """
        Run full analysis on a single Sentinel-2 scene.
        Returns all spectral indices, alteration map, and recommendations.
        """
        recommendations = []
        indices = {}

        # ── Compute spectral indices ──
        try:
            indices["ndvi"] = self.compute_ndvi(scene)
            indices["clay_ratio"] = self.compute_clay_index(scene)
            indices["iron_oxide"] = self.compute_iron_oxide_index(scene)
            indices["ferrous_index"] = self.compute_ferrous_index(scene)
            indices["ndsi"] = self.compute_ndsi(scene)
        except KeyError as exc:
            logger.error("Missing band for index computation: %s", exc)
            recommendations.append(f"Missing spectral band: {exc}")
            return SatelliteAnalysis(
                indices=indices,
                alteration_map=None,
                cloud_coverage_pct=100.0,
                usable=False,
                recommendations=recommendations,
                metadata=scene.metadata,
            )

        # ── Cloud cover detection ──
        cloud_pct = self.detect_cloud_coverage(scene)
        if cloud_pct > self.CLOUD_THRESHOLD * 100:
            recommendations.append(
                f"High cloud coverage ({cloud_pct:.1f}%). "
                f"Results may be unreliable. Consider a clearer scene."
            )

        # ── Alteration mapping ──
        alteration_map = self.map_alterations(scene, indices)

        # ── Generate recommendations ──
        if alteration_map.summary.get("clay_pct", 0) > 10:
            recommendations.append(
                f"Significant clay alteration detected ({alteration_map.summary['clay_pct']:.1f}%). "
                f"This may indicate hydrothermal alteration associated with mineralization."
            )

        if alteration_map.summary.get("iron_oxide_pct", 0) > 15:
            recommendations.append(
                f"Iron oxide enrichment detected ({alteration_map.summary['iron_oxide_pct']:.1f}%). "
                f"Possible gossan — surface expression of sulfide mineralization."
            )

        if np.mean(indices["ndvi"]) < 0.1:
            recommendations.append(
                "Very low vegetation cover — bare rock exposure is high. "
                "Good conditions for spectral mineral mapping."
            )

        usable = cloud_pct <= self.CLOUD_THRESHOLD * 100

        return SatelliteAnalysis(
            indices=indices,
            alteration_map=alteration_map,
            cloud_coverage_pct=cloud_pct,
            usable=usable,
            recommendations=recommendations,
            metadata=scene.metadata,
        )

    def compute_ndvi(self, scene: SatelliteScene) -> np.ndarray:
        """
        Normalized Difference Vegetation Index.
        NDVI = (NIR - RED) / (NIR + RED)
        Low NDVI in vegetated areas may indicate mineralization stress.
        """
        nir = scene.get_band(S2Band.B08).astype(np.float64)
        red = scene.get_band(S2Band.B04).astype(np.float64)
        return self._normalized_difference(nir, red)

    def compute_clay_index(self, scene: SatelliteScene) -> np.ndarray:
        """
        Clay Mineral Index (CMR).
        CMR = SWIR1 / SWIR2
        High values indicate clay minerals (kaolinite, illite, montmorillonite).
        Associated with argillic alteration — common in porphyry copper systems.
        """
        swir1 = scene.get_band(S2Band.B11).astype(np.float64)
        swir2 = scene.get_band(S2Band.B12).astype(np.float64)
        # Avoid division by zero
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.where(swir2 > 0.01, swir1 / swir2, 0.0)
        return ratio

    def compute_iron_oxide_index(self, scene: SatelliteScene) -> np.ndarray:
        """
        Iron Oxide Index (IOI).
        IOI = RED / BLUE
        High values indicate iron oxide enrichment (hematite, goethite, limonite).
        Gossans are surface expressions of sulfide mineralization.
        """
        red = scene.get_band(S2Band.B04).astype(np.float64)
        blue = scene.get_band(S2Band.B02).astype(np.float64)
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.where(blue > 0.01, red / blue, 0.0)
        return ratio

    def compute_ferrous_index(self, scene: SatelliteScene) -> np.ndarray:
        """
        Ferrous Iron Index (FII).
        FII = NIR / RED_EDGE1
        Detects ferrous (Fe²⁺) minerals like magnetite and pyroxene.
        """
        nir = scene.get_band(S2Band.B08).astype(np.float64)
        red_edge = scene.get_band(S2Band.B05).astype(np.float64)
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.where(red_edge > 0.01, nir / red_edge, 0.0)
        return ratio

    def compute_ndsi(self, scene: SatelliteScene) -> np.ndarray:
        """
        Normalized Difference Snow Index.
        NDSI = (GREEN - SWIR1) / (GREEN + SWIR1)
        Used to mask snow/ice which can confuse mineral detection.
        """
        green = scene.get_band(S2Band.B03).astype(np.float64)
        swir1 = scene.get_band(S2Band.B11).astype(np.float64)
        return self._normalized_difference(green, swir1)

    def detect_cloud_coverage(self, scene: SatelliteScene) -> float:
        """
        Estimate cloud coverage percentage.
        Uses the BQA/CLD band if available, otherwise estimates from spectral ratios.
        Returns: 0-100 percentage.
        """
        # If cloud mask is provided
        if scene.cloud_mask is not None:
            return float(np.mean(scene.cloud_mask > 0) * 100)

        # Estimate from spectral properties
        # Clouds are bright in visible and SWIR
        try:
            blue = scene.get_band(S2Band.B02).astype(np.float64)
            swir = scene.get_band(S2Band.B11).astype(np.float64)
            nir = scene.get_band(S2Band.B08).astype(np.float64)

            # Clouds: high reflectance in visible + SWIR, low NDVI
            bright = (blue > 0.3) & (swir > 0.2)
            ndvi = self._normalized_difference(nir, scene.get_band(S2Band.B04).astype(np.float64))
            cloud_like = bright & (ndvi < 0.1)

            return float(np.mean(cloud_like) * 100)
        except Exception:
            logger.warning("Cloud detection failed, returning 0")
            return 0.0

    def map_alterations(
        self,
        scene: SatelliteScene,
        indices: Dict[str, np.ndarray],
    ) -> AlterationMap:
        """
        Create alteration map from spectral indices.
        Classifies pixels into alteration zones:
        - Argillic (clay-rich)
        - Iron oxide (gossan)
        - Ferrous (magnetite-bearing)
        - Vegetated
        - Bare rock
        - Snow/Ice
        """
        ndvi = indices.get("ndvi", np.zeros((1, 1)))
        clay = indices.get("clay_ratio", np.zeros((1, 1)))
        iron = indices.get("iron_oxide", np.zeros((1, 1)))
        ferrous = indices.get("ferrous_index", np.zeros((1, 1)))
        ndsi = indices.get("ndsi", np.zeros((1, 1)))

        h, w = ndvi.shape
        zones = np.zeros((h, w), dtype=np.uint8)

        # Classification priority (higher number overrides lower)
        # 0 = unclassified
        zones[ndsi > 0.4] = 6                              # Snow/Ice
        zones[(ndvi > 0.3)] = 5                              # Vegetated
        zones[(clay > self.CLAY_THRESHOLD)] = 1              # Argillic alteration
        zones[(iron > self.IRON_THRESHOLD)] = 2              # Iron oxide (gossan)
        zones[(ferrous > 1.5)] = 3                           # Ferrous minerals
        zones[(ndvi < 0.1) & (clay < 0.1) & (iron < 0.2)] = 4  # Bare rock

        # Summary statistics
        total_pixels = h * w
        summary = {
            "clay_pct": float(np.sum(zones == 1) / total_pixels * 100),
            "iron_oxide_pct": float(np.sum(zones == 2) / total_pixels * 100),
            "ferrous_pct": float(np.sum(zones == 3) / total_pixels * 100),
            "bare_rock_pct": float(np.sum(zones == 4) / total_pixels * 100),
            "vegetated_pct": float(np.sum(zones == 5) / total_pixels * 100),
            "snow_ice_pct": float(np.sum(zones == 6) / total_pixels * 100),
        }

        return AlterationMap(
            clay_minerals=clay,
            iron_oxide=iron,
            ferrous_minerals=ferrous,
            ndvi=ndvi,
            ndsi=ndsi,
            alteration_zones=zones,
            summary=summary,
        )

    def multi_temporal_analysis(
        self,
        scenes: List[SatelliteScene],
    ) -> Dict[str, Any]:
        """
        Analyze changes across multiple scenes over time.
        Detects vegetation stress, seasonal changes, and potential new exposures.
        """
        if len(scenes) < 2:
            return {"error": "Need at least 2 scenes for temporal analysis"}

        # Sort by date
        scenes = sorted(scenes, key=lambda s: s.date or datetime.min)

        # Compute indices for each scene
        all_ndvi = []
        all_iron = []
        dates = []

        for scene in scenes:
            try:
                ndvi = self.compute_ndvi(scene)
                iron = self.compute_iron_oxide_index(scene)
                all_ndvi.append(ndvi)
                all_iron.append(iron)
                dates.append(scene.date.isoformat() if scene.date else "unknown")
            except Exception as exc:
                logger.warning("Failed to process scene: %s", exc)

        if len(all_ndvi) < 2:
            return {"error": "Not enough valid scenes"}

        # Compute changes
        ndvi_change = all_ndvi[-1] - all_ndvi[0]
        iron_change = all_iron[-1] - all_iron[0]

        # Vegetation stress detection
        stress_mask = (all_ndvi[0] > 0.3) & (ndvi_change < -0.15)
        stress_pct = float(np.mean(stress_mask) * 100)

        # New iron exposure
        new_iron = (all_iron[-1] > self.IRON_THRESHOLD) & (all_iron[0] < self.IRON_THRESHOLD)
        new_iron_pct = float(np.mean(new_iron) * 100)

        recommendations = []
        if stress_pct > 5:
            recommendations.append(
                f"Vegetation stress detected ({stress_pct:.1f}% of area). "
                f"This may indicate mineralization — heavy metals can inhibit plant growth."
            )
        if new_iron_pct > 3:
            recommendations.append(
                f"New iron oxide exposure detected ({new_iron_pct:.1f}%). "
                f"Possible recent weathering or land disturbance revealing gossan."
            )

        return {
            "dates": dates,
            "ndvi_mean_change": float(np.mean(ndvi_change)),
            "iron_mean_change": float(np.mean(iron_change)),
            "vegetation_stress_pct": stress_pct,
            "new_iron_exposure_pct": new_iron_pct,
            "recommendations": recommendations,
        }

    @staticmethod
    def _normalized_difference(band_a: np.ndarray, band_b: np.ndarray) -> np.ndarray:
        """Compute normalized difference: (A - B) / (A + B)."""
        with np.errstate(divide="ignore", invalid="ignore"):
            result = np.where(
                (band_a + band_b) > 0.01,
                (band_a - band_b) / (band_a + band_b),
                0.0,
            )
        return np.clip(result, -1.0, 1.0)


def load_sentinel2_geotiff(directory: Union[str, Path]) -> SatelliteScene:
    """
    Load Sentinel-2 bands from GeoTIFF files in a directory.
    Expects files named like: B02.tif, B03.tif, B04.tif, etc.
    """
    try:
        import rasterio
    except ImportError:
        raise ImportError("rasterio required for GeoTIFF loading: pip install rasterio")

    directory = Path(directory)
    bands = {}

    band_files = {
        "B02": "blue", "B03": "green", "B04": "red",
        "B05": "rededge1", "B06": "rededge2", "B07": "rededge3",
        "B08": "nir", "B8A": "nir_narrow",
        "B11": "swir1", "B12": "swir2",
    }

    for band_name, band_key in band_files.items():
        for pattern in [f"{band_name}.tif", f"{band_name}_*.tif", f"*_{band_name}_*.tif"]:
            matches = list(directory.glob(pattern))
            if matches:
                with rasterio.open(matches[0]) as src:
                    bands[band_key] = src.read(1).astype(np.float64) / 10000.0
                break

    if not bands:
        raise FileNotFoundError(f"No Sentinel-2 band files found in {directory}")

    return SatelliteScene(
        bands=bands,
        metadata={"source": "geotiff", "directory": str(directory)},
    )
