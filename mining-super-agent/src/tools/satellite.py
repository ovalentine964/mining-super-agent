"""
Satellite Tools — Sentinel-2, Planetary Computer, spectral indices.

These tools handle satellite imagery download, processing, and analysis
for mineral exploration.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)


async def sentinel2_download(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    cloud_cover_max: float = 20,
    buffer_km: float = 5,
) -> dict[str, Any]:
    """
    Download Sentinel-2 L2A imagery via Planetary Computer STAC API.

    Uses pystac-client to search and download Sentinel-2 data.
    """
    try:
        from pystac_client import Client
        import planetary_computer as pc

        # Connect to Planetary Computer STAC
        catalog = Client.open(
            "https://planetarycomputer.microsoft.com/api/stac/v1",
            modifier=pc.sign_inplace,
        )

        # Calculate bounding box
        import math
        buffer_deg = buffer_km / 111.0  # Approximate km to degrees
        bbox = [
            longitude - buffer_deg,
            latitude - buffer_deg,
            longitude + buffer_deg,
            latitude + buffer_deg,
        ]

        # Search for Sentinel-2 L2A
        search = catalog.search(
            collections=["sentinel-2-l2a"],
            bbox=bbox,
            datetime=f"{start_date}/{end_date}",
            query={"eo:cloud_cover": {"lt": cloud_cover_max}},
            limit=10,
        )

        items = list(search.items())

        if not items:
            return {
                "success": False,
                "error": "No Sentinel-2 imagery found for the specified criteria",
                "suggestion": "Try expanding date range or increasing cloud cover threshold",
            }

        # Sort by cloud cover
        items.sort(key=lambda item: item.properties.get("eo:cloud_cover", 100))
        best = items[0]

        return {
            "success": True,
            "imagery_id": best.id,
            "date": best.properties.get("datetime"),
            "cloud_cover": best.properties.get("eo:cloud_cover"),
            "bands_available": list(best.assets.keys()),
            "download_urls": {
                band: best.assets[band].href
                for band in ["B02", "B03", "B04", "B08", "B11", "B12"]
                if band in best.assets
            },
            "total_results": len(items),
            "source": "Sentinel-2 L2A via Microsoft Planetary Computer",
        }

    except ImportError:
        return {
            "success": False,
            "error": "pystac-client or planetary-computer not installed",
            "install": "pip install pystac-client planetary-computer",
        }


async def calculate_ndvi(
    nir_band: Any,
    red_band: Any,
) -> dict[str, Any]:
    """
    Calculate NDVI (Normalized Difference Vegetation Index).

    NDVI = (NIR - Red) / (NIR + Red)
    Range: -1 to 1 (higher = more vegetation)
    """
    import numpy as np

    nir = np.array(nir_band, dtype=np.float32)
    red = np.array(red_band, dtype=np.float32)

    # Avoid division by zero
    denominator = nir + red
    denominator[denominator == 0] = np.nan

    ndvi = (nir - red) / denominator

    return {
        "index": "NDVI",
        "formula": "(NIR - Red) / (NIR + Red)",
        "statistics": {
            "mean": float(np.nanmean(ndvi)),
            "std": float(np.nanstd(ndvi)),
            "min": float(np.nanmin(ndvi)),
            "max": float(np.nanmax(ndvi)),
            "median": float(np.nanmedian(ndvi)),
        },
        "interpretation": _interpret_ndvi(float(np.nanmean(ndvi))),
    }


async def calculate_clay_ratio(
    swir1_band: Any,
    swir2_band: Any,
) -> dict[str, Any]:
    """
    Calculate Clay Mineral Ratio.

    Clay Ratio = SWIR1 / SWIR2
    Higher values indicate clay mineral abundance (alteration indicator).
    """
    import numpy as np

    swir1 = np.array(swir1_band, dtype=np.float32)
    swir2 = np.array(swir2_band, dtype=np.float32)

    swir2[swir2 == 0] = np.nan
    ratio = swir1 / swir2

    return {
        "index": "Clay Ratio",
        "formula": "SWIR1 (B11) / SWIR2 (B12)",
        "statistics": {
            "mean": float(np.nanmean(ratio)),
            "std": float(np.nanstd(ratio)),
            "min": float(np.nanmin(ratio)),
            "max": float(np.nanmax(ratio)),
        },
        "anomaly_threshold": float(np.nanmean(ratio) + 2 * np.nanstd(ratio)),
        "interpretation": "Elevated clay ratio indicates argillic alteration — potential mineralization indicator",
    }


async def calculate_iron_oxide_ratio(
    red_band: Any,
    blue_band: Any,
) -> dict[str, Any]:
    """
    Calculate Iron Oxide Ratio.

    Iron Oxide Ratio = Red / Blue
    Higher values indicate iron oxide abundance (gossan indicator).
    """
    import numpy as np

    red = np.array(red_band, dtype=np.float32)
    blue = np.array(blue_band, dtype=np.float32)

    blue[blue == 0] = np.nan
    ratio = red / blue

    return {
        "index": "Iron Oxide Ratio",
        "formula": "Red (B04) / Blue (B02)",
        "statistics": {
            "mean": float(np.nanmean(ratio)),
            "std": float(np.nanstd(ratio)),
            "min": float(np.nanmin(ratio)),
            "max": float(np.nanmax(ratio)),
        },
        "anomaly_threshold": float(np.nanmean(ratio) + 2 * np.nanstd(ratio)),
        "interpretation": "Elevated iron oxide ratio indicates gossan or supergene enrichment — potential mineralization",
    }


async def cloud_cover_check(
    latitude: float,
    longitude: float,
    date: str,
) -> dict[str, Any]:
    """Check cloud cover for a specific date and location."""
    try:
        from pystac_client import Client
        import planetary_computer as pc

        catalog = Client.open(
            "https://planetarycomputer.microsoft.com/api/stac/v1",
            modifier=pc.sign_inplace,
        )

        import math
        buffer_deg = 0.05
        bbox = [
            longitude - buffer_deg,
            latitude - buffer_deg,
            longitude + buffer_deg,
            latitude + buffer_deg,
        ]

        search = catalog.search(
            collections=["sentinel-2-l2a"],
            bbox=bbox,
            datetime=f"{date}/{date}",
            limit=5,
        )

        items = list(search.items())
        if items:
            cloud = items[0].properties.get("eo:cloud_cover", -1)
            return {
                "success": True,
                "date": date,
                "cloud_cover_pct": round(cloud, 1),
                "usable": cloud < 20,
                "assessment": "GOOD" if cloud < 10 else "ACCEPTABLE" if cloud < 20 else "POOR",
            }

        return {"success": False, "error": "No imagery found for this date"}

    except ImportError:
        return {
            "success": False,
            "error": "Required packages not installed",
            "install": "pip install pystac-client planetary-computer",
        }


def _interpret_ndvi(ndvi: float) -> str:
    """Interpret NDVI value."""
    if ndvi < 0:
        return "Water or bare rock — potential outcrop exposure"
    elif ndvi < 0.15:
        return "Sparse vegetation — bare soil/rock, good for alteration mapping"
    elif ndvi < 0.3:
        return "Moderate vegetation — may mask some alteration signals"
    elif ndvi < 0.5:
        return "Dense vegetation — alteration mapping limited to clearings"
    else:
        return "Very dense vegetation — ground-based exploration recommended"


def register_satellite_tools(registry) -> None:
    """Register all satellite tools with the tool registry."""
    registry.register_handler("sentinel2_download", sentinel2_download)
    registry.register_handler("calculate_ndvi", calculate_ndvi)
    registry.register_handler("calculate_clay_ratio", calculate_clay_ratio)
    registry.register_handler("calculate_iron_oxide_ratio", calculate_iron_oxide_ratio)
    registry.register_handler("cloud_cover_check", cloud_cover_check)
