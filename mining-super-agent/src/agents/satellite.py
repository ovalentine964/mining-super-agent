"""
Satellite Analyst Agent — Remote sensing and alteration mapping.

Capabilities:
- Sentinel-2 multispectral analysis
- Alteration mapping (clay minerals, iron oxide, silica)
- Spectral indices (NDVI, clay ratio, iron oxide ratio)
- Cloud cover detection and filtering
- Multi-source cascade: Sentinel-2 → Landsat → cached data

Uses Llama 3.1 405B for spectral interpretation.
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


class SatelliteAgent(BaseAgent):
    """Satellite imagery analyst for alteration mapping and land analysis."""

    def __init__(self):
        tools = [
            ToolDefinition(
                name="query_sentinel2",
                description="Query and download Sentinel-2 satellite imagery for a given area and date range.",
                parameters={
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "number", "description": "Center latitude"},
                        "longitude": {"type": "number", "description": "Center longitude"},
                        "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                        "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                        "cloud_cover_max": {
                            "type": "number",
                            "default": 20,
                            "description": "Maximum cloud cover percentage",
                        },
                        "buffer_km": {"type": "number", "default": 5, "description": "Buffer around center point in km"},
                    },
                    "required": ["latitude", "longitude", "start_date", "end_date"],
                },
                permissions=["read:satellite", "api:planetary_computer"],
            ),
            ToolDefinition(
                name="calculate_spectral_indices",
                description="Calculate spectral indices from satellite imagery (NDVI, clay, iron oxide, etc.).",
                parameters={
                    "type": "object",
                    "properties": {
                        "imagery_id": {"type": "string", "description": "ID of the satellite imagery to analyze"},
                        "indices": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["NDVI", "clay_ratio", "iron_oxide", "silica", "NDWI", "NDBI"],
                            },
                            "description": "Which indices to calculate",
                            "default": ["NDVI", "clay_ratio", "iron_oxide"],
                        },
                        "output_format": {"type": "string", "enum": ["raster", "statistics", "map"], "default": "statistics"},
                    },
                    "required": ["imagery_id"],
                },
                permissions=["read:satellite", "compute:satellite"],
            ),
            ToolDefinition(
                name="detect_alteration_zones",
                description="Detect hydrothermal alteration zones from multispectral data.",
                parameters={
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "number"},
                        "longitude": {"type": "number"},
                        "date_range": {
                            "type": "object",
                            "properties": {
                                "start": {"type": "string"},
                                "end": {"type": "string"},
                            },
                        },
                        "alteration_types": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["argillic", "propylitic", "phyllic", "silicification", "iron_oxide"],
                            },
                            "default": ["argillic", "propylitic", "iron_oxide"],
                        },
                    },
                    "required": ["latitude", "longitude"],
                },
                permissions=["read:satellite", "compute:satellite"],
            ),
            ToolDefinition(
                name="check_cloud_cover",
                description="Check cloud cover for a specific date and location before downloading imagery.",
                parameters={
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "number"},
                        "longitude": {"type": "number"},
                        "date": {"type": "string", "description": "Date to check (YYYY-MM-DD)"},
                    },
                    "required": ["latitude", "longitude", "date"],
                },
                permissions=["api:planetary_computer"],
            ),
            ToolDefinition(
                name="query_planetary_computer",
                description="Query Microsoft Planetary Computer for multi-source satellite data.",
                parameters={
                    "type": "object",
                    "properties": {
                        "collection": {
                            "type": "string",
                            "enum": ["sentinel-2-l2a", "landsat-c2-l2", "aster-l1t"],
                            "default": "sentinel-2-l2a",
                        },
                        "latitude": {"type": "number"},
                        "longitude": {"type": "number"},
                        "start_date": {"type": "string"},
                        "end_date": {"type": "string"},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["latitude", "longitude", "start_date", "end_date"],
                },
                permissions=["api:planetary_computer"],
            ),
        ]

        super().__init__(
            name="Satellite",
            description=(
                "Satellite imagery analyst specializing in alteration mapping for mineral exploration. "
                "Analyzes Sentinel-2 multispectral data to detect hydrothermal alteration "
                "(clay minerals, iron oxides, silicification) that indicate mineralization."
            ),
            model_id="meta/llama-3.1-405b-instruct",
            permissions={"read:satellite", "compute:satellite", "api:planetary_computer", "api:gee"},
            tools=tools,
            system_prompt=self._build_system_prompt(),
            timeout_seconds=180.0,
        )

    def _build_system_prompt(self) -> str:
        return """You are a remote sensing specialist analyzing satellite imagery for mineral exploration
in Kenya's Migori Greenstone Belt.

ALTERATION MAPPING KNOWLEDGE:
Hydrothermal alteration associated with mineralization creates detectable spectral signatures:

1. ARGILLIC ALTERATION (Clay minerals — kaolinite, montmorillonite, illite):
   - Strong absorption at 2200nm (SWIR band)
   - Useful indices: Clay Ratio = Band 11 / Band 12
   - Associated with: Gold, copper, porphyry systems

2. PROPYLITIC ALTERATION (Chlorite, epidote, calcite):
   - Absorption near 2200nm and 2300nm
   - Weaker signal than argillic
   - Associated with: Gold, VMS deposits

3. IRON OXIDE ALTERATION (Hematite, goethite, jarosite):
   - Strong absorption at 900nm, high reflectance in red
   - Useful indices: Iron Oxide Ratio = Band 4 / Band 2
   - Associated with: Gold, copper supergene enrichment

4. SILICIFICATION:
   - High reflectance in SWIR
   - Associated with: Gold-bearing quartz veins

SPECTRAL INDICES:
- NDVI = (NIR - Red) / (NIR + Red) — vegetation health
- Clay Ratio = SWIR1 / SWIR2 — clay mineral abundance
- Iron Oxide Ratio = Red / Blue — iron oxide abundance
- Ferrous Ratio = SWIR1 / NIR — ferrous iron minerals

SENTINEL-2 BANDS:
- Band 2: Blue (490nm)
- Band 3: Green (560nm)
- Band 4: Red (665nm)
- Band 8: NIR (842nm)
- Band 11: SWIR1 (1610nm)
- Band 12: SWIR2 (2190nm)

ANALYSIS APPROACH:
1. Check cloud cover — skip images >20% cloud
2. Download least-cloudy image for the date range
3. Calculate spectral indices
4. Identify anomalous zones (statistical outliers)
5. Cross-reference with geological maps
6. Report with confidence based on data quality

CONFIDENCE RULES:
- Single date, clear sky: max 65% confidence
- Multi-date composite, clear: max 75% confidence
- Altered zones detected + geological correlation: max 80% confidence
- Always note cloud contamination risk
- Seasonal vegetation can mask alteration signals
"""

    async def run(self, task: str, context: Optional[dict[str, Any]] = None) -> AgentResult:
        """Run satellite analysis."""
        enhanced_context = {
            **(context or {}),
            "domain": "remote_sensing",
            "data_sources": ["Sentinel-2 L2A", "Microsoft Planetary Computer"],
            "analysis_types": ["alteration_mapping", "spectral_indices", "cloud_filtering"],
        }

        result = await super().run(task, enhanced_context)

        result.disclaimers.extend([
            "Satellite analysis is affected by cloud cover, vegetation, and seasonal variations. "
            "Ground truthing is essential to confirm any remote sensing interpretation.",
            "Alteration mapping from satellite data provides indicators, not confirmations. "
            "Geochemical sampling is required to validate findings.",
        ])

        return result


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

async def query_sentinel2(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    cloud_cover_max: float = 20,
    buffer_km: float = 5,
) -> dict[str, Any]:
    """Query Sentinel-2 imagery via Planetary Computer STAC API."""
    # Mock — replace with actual pystac-client + planetary computer calls
    return {
        "query": {
            "center": {"lat": latitude, "lon": longitude},
            "date_range": {"start": start_date, "end": end_date},
            "cloud_max": cloud_cover_max,
        },
        "imagery_found": 3,
        "images": [
            {
                "id": "S2A_MSIL2A_20260701T073621_N0510_R092_T36MVD_20260701T102543",
                "date": "2026-07-01",
                "cloud_cover": 5.2,
                "resolution_m": 10,
                "bands_available": ["B02", "B03", "B04", "B08", "B11", "B12"],
                "source": "Sentinel-2 L2A via Planetary Computer",
            },
            {
                "id": "S2A_MSIL2A_20260621T073621_N0510_R092_T36MVD_20260621T101234",
                "date": "2026-06-21",
                "cloud_cover": 12.8,
                "resolution_m": 10,
                "bands_available": ["B02", "B03", "B04", "B08", "B11", "B12"],
                "source": "Sentinel-2 L2A via Planetary Computer",
            },
        ],
        "recommended": "S2A_..._20260701 (lowest cloud cover)",
    }


async def calculate_spectral_indices(
    imagery_id: str,
    indices: list[str] = None,
    output_format: str = "statistics",
) -> dict[str, Any]:
    """Calculate spectral indices from satellite imagery."""
    if indices is None:
        indices = ["NDVI", "clay_ratio", "iron_oxide"]

    # Mock — replace with actual rasterio + numpy calculations
    results = {
        "imagery_id": imagery_id,
        "output_format": output_format,
        "indices": {},
    }

    for idx in indices:
        if idx == "NDVI":
            results["indices"]["NDVI"] = {
                "mean": 0.45,
                "std": 0.18,
                "min": -0.1,
                "max": 0.85,
                "interpretation": "Moderate vegetation. Low NDVI areas may indicate bare rock or water.",
            }
        elif idx == "clay_ratio":
            results["indices"]["clay_ratio"] = {
                "mean": 1.05,
                "std": 0.12,
                "anomalous_zones": 2,
                "interpretation": "Two zones with elevated clay ratio — potential argillic alteration.",
            }
        elif idx == "iron_oxide":
            results["indices"]["iron_oxide"] = {
                "mean": 1.8,
                "std": 0.35,
                "anomalous_zones": 1,
                "interpretation": "One zone with elevated iron oxide — possible gossan or supergene enrichment.",
            }

    return results


async def detect_alteration_zones(
    latitude: float,
    longitude: float,
    date_range: dict = None,
    alteration_types: list[str] = None,
) -> dict[str, Any]:
    """Detect hydrothal alteration zones from multispectral data."""
    if alteration_types is None:
        alteration_types = ["argillic", "propylitic", "iron_oxide"]

    # Mock — replace with actual spectral analysis
    return {
        "location": {"lat": latitude, "lon": longitude},
        "alteration_zones": [
            {
                "type": "argillic",
                "detected": True,
                "area_km2": 0.8,
                "center": {"lat": latitude + 0.005, "lon": longitude + 0.003},
                "strength": "moderate",
                "confidence": 0.60,
                "interpretation": "Kaolinite/montmorillonite alteration — potential porphyry or epithermal system",
            },
            {
                "type": "iron_oxide",
                "detected": True,
                "area_km2": 0.3,
                "center": {"lat": latitude - 0.002, "lon": longitude + 0.001},
                "strength": "strong",
                "confidence": 0.65,
                "interpretation": "Iron oxide gossan — possible sulfide oxidation above mineralization",
            },
        ],
        "overall_confidence": 0.55,
        "recommendations": [
            "Ground truth with field visit to anomalous zones",
            "Collect rock chip samples for geochemical analysis",
            "Check for coincident geophysical anomalies",
        ],
    }


async def check_cloud_cover(
    latitude: float,
    longitude: float,
    date: str,
) -> dict[str, Any]:
    """Check cloud cover for a specific date/location."""
    # Mock — replace with actual API call
    return {
        "date": date,
        "location": {"lat": latitude, "lon": longitude},
        "cloud_cover_pct": 8.5,
        "assessment": "GOOD — below 20% threshold",
        "usable": True,
    }


async def query_planetary_computer(
    collection: str,
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    limit: int = 10,
) -> dict[str, Any]:
    """Query Microsoft Planetary Computer STAC catalog."""
    # Mock — replace with actual pystac-client
    return {
        "collection": collection,
        "results_count": 5,
        "items": [
            {
                "id": f"{collection}_20260701",
                "date": "2026-07-01",
                "cloud_cover": 5.2,
                "bbox": [longitude - 0.05, latitude - 0.05, longitude + 0.05, latitude + 0.05],
            },
        ],
    }
