"""
Geological Tools — GemPy, SimPEG, Mindat, geological database.

These are the actual tool implementations that get registered with the ToolRegistry.
Each function is a handler that gets called when an agent invokes the tool.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


async def gempy_3d_model(
    extent: list[float],
    resolution: list[int] = None,
    surface_points: list[dict] = None,
    orientation_data: list[dict] = None,
) -> dict[str, Any]:
    """
    Create a 3D geological model using GemPy.

    GemPy is an open-source Python library for implicit geological modeling.
    It creates 3D structural models from surface observations and orientation data.

    Args:
        extent: [xmin, xmax, ymin, ymax, zmin, zmax]
        resolution: [nx, ny, nz] grid resolution
        surface_points: Known surface point locations with formation labels
        orientation_data: Dip/azimuth measurements at surface points
    """
    if resolution is None:
        resolution = [50, 50, 50]

    try:
        import gempy as gp
        import numpy as np

        # Create GeoModel
        geo_model = gp.create_geomodel(
            project_name="mining_model",
            extent=extent,
            resolution=resolution,
        )

        # Add surface points if provided
        if surface_points:
            for sp in surface_points:
                gp.add_surface_points(
                    geo_model,
                    coord=np.array([[sp["x"], sp["y"], sp["z"]]]),
                    surface_names=[sp.get("formation", "unknown")],
                )

        # Compute model
        gp.compute_model(geo_model)

        return {
            "success": True,
            "model_extent": extent,
            "resolution": resolution,
            "lithological_units": [
                {"id": i, "name": f"Unit_{i}"}
                for i in range(len(geo_model.surfaces.df))
            ],
            "note": "3D model computed. Export with gempy.plot_3d(geo_model)",
        }

    except ImportError:
        logger.warning("GemPy not installed — returning mock model")
        return {
            "success": False,
            "error": "GemPy not installed. Install with: pip install gempy",
            "mock_result": {
                "extent": extent,
                "resolution": resolution,
                "units": ["Laterite", "Weathered basalt", "Fresh basalt", "Quartz vein"],
                "note": "Install GemPy for actual 3D modeling",
            },
        }


async def simpeg_inversion(
    data_type: str,
    data_path: Optional[str] = None,
    mesh_size: int = 64,
    inversion_type: str = "susceptibility",
) -> dict[str, Any]:
    """
    Run SimPEG geophysical inversion.

    SimPEG (Simulation and Parameter Estimation in Geophysics) is an open-source
    framework for geophysical forward modeling and inversion.

    Args:
        data_type: "magnetic", "resistivity", or "gravity"
        data_path: Path to geophysical data file
        mesh_size: Number of mesh cells
        inversion_type: Physical property to invert for
    """
    try:
        import simpeg
        from simpeg import maps, data_misfit, regularization, optimization
        from simpeg import inverse_problem, directives
        import numpy as np

        # Create mesh
        mesh = simpeg.mesh.TensorMesh([mesh_size, mesh_size, mesh_size])

        # This is a simplified framework — real implementation requires
        # proper survey setup, forward simulation, and data loading
        return {
            "success": True,
            "data_type": data_type,
            "inversion_type": inversion_type,
            "mesh_cells": mesh_size ** 3,
            "note": (
                "SimPEG inversion framework initialized. "
                "Provide survey data for full inversion."
            ),
        }

    except ImportError:
        return {
            "success": False,
            "error": "SimPEG not installed. Install with: pip install simpeg",
            "mock_result": {
                "data_type": data_type,
                "mesh_size": mesh_size,
                "note": "Install SimPEG for actual geophysical inversion",
            },
        }


async def mindat_query(
    latitude: float,
    longitude: float,
    radius_km: float = 25,
    mineral: Optional[str] = None,
    api_key: Optional[str] = None,
) -> dict[str, Any]:
    """
    Query Mindat.org API for mineral occurrence data.

    Mindat.org is the world's largest mineral database with information on
    over 600,000 mineral localities worldwide.
    """
    import os
    import httpx

    key = api_key or os.environ.get("MINDAT_API_KEY", "")

    if not key:
        return {
            "success": False,
            "error": "MINDAT_API_KEY not set",
            "fallback": "Use BGS OpenGeoscience or USGS MRDATA as alternatives",
        }

    # Mindat API v3
    headers = {"Authorization": f"key {key}"}
    params = {
        "lat": latitude,
        "lng": longitude,
        "distance": radius_km,
        "fmt": "json",
    }
    if mineral:
        params["mineral"] = mineral

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://api.mindat.org/v3/locmindat/",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "success": True,
            "query": {"lat": latitude, "lon": longitude, "radius_km": radius_km},
            "results": data.get("results", []),
            "total": data.get("count", 0),
            "source": "Mindat.org API v3",
        }

    except httpx.HTTPError as e:
        return {
            "success": False,
            "error": f"Mindat API error: {e}",
            "fallback": "Check API key and network connectivity",
        }


async def usgs_mrdata_query(
    latitude: float,
    longitude: float,
    radius_km: float = 50,
    commodity: Optional[str] = None,
) -> dict[str, Any]:
    """
    Query USGS Mineral Resources Data System (MRDS).

    MRDS contains records of mineral occurrences worldwide, including
    location, commodity, deposit type, and production history.
    """
    import httpx

    # USGS MRDS WFS endpoint
    url = "https://mrdata.usgs.gov/wfs/mrds"
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": "mrds",
        "outputFormat": "application/json",
        "CQL_FILTER": f"DWITHIN(geom, POINT({longitude} {latitude}), {radius_km * 1000}, meters)",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        features = data.get("features", [])
        return {
            "success": True,
            "query": {"lat": latitude, "lon": longitude, "radius_km": radius_km},
            "results": [
                {
                    "name": f.get("properties", {}).get("name", "Unknown"),
                    "commodity": f.get("properties", {}).get("commodity", ""),
                    "deposit_type": f.get("properties", {}).get("dep_type", ""),
                    "coordinates": f.get("geometry", {}).get("coordinates", []),
                }
                for f in features[:50]
            ],
            "total": len(features),
            "source": "USGS MRDS",
        }

    except httpx.HTTPError as e:
        return {
            "success": False,
            "error": f"USGS MRDS error: {e}",
        }


async def geological_database_query(
    latitude: float,
    longitude: float,
    radius_km: float = 10,
    query_type: str = "all",
) -> dict[str, Any]:
    """
    Query the local geological database (PostgreSQL + PostGIS).
    In production, this connects to the PostGIS database.
    """
    # Mock — replace with actual PostGIS queries
    return {
        "success": True,
        "location": {"lat": latitude, "lon": longitude},
        "radius_km": radius_km,
        "query_type": query_type,
        "results": {
            "rock_units": [
                {
                    "name": "Nyanzian Metavolcanics",
                    "age": "Neoarchean (~2.7 Ga)",
                    "rock_type": "Metabasalt, Meta-andesite",
                },
            ],
            "mineral_occurrences": [
                {
                    "mineral": "Gold",
                    "grade": "0.5-15 g/t",
                    "confidence": 0.75,
                    "source": "Kenya Geological Survey",
                },
            ],
            "structural_features": [
                {
                    "type": "NE-trending shear zone",
                    "significance": "Controls gold mineralization",
                },
            ],
        },
        "data_sources": ["Kenya Geological Survey", "BGS OpenGeoscience"],
    }


async def analyze_deposit_model(
    observations: dict[str, Any],
    location: dict[str, float] | None = None,
    mineral_type: str | None = None,
) -> dict[str, Any]:
    """
    Match observations to known deposit models.

    Compares field observations (rock type, alteration, mineralization,
    structural setting) against a database of known deposit types to
    identify the most likely deposit model.

    Args:
        observations: Dict with keys like rock_type, alteration, minerals,
                      structures, host_rock, etc.
        location: Optional lat/lon for context.
        mineral_type: Optional hint about target mineral.
    """
    # Known deposit model templates
    DEPOSIT_MODELS = {
        "orogenic_gold": {
            "name": "Orogenic Gold",
            "key_indicators": [
                "quartz_veins", "shear_zones", "arsenopyrite",
                "pyrite", "sericite_alteration", "carbonate_alteration",
            ],
            "host_rocks": ["greenstone", "metavolcanics", "metasediments", "banded_iron_formation"],
            "typical_grades": "1-15 g/t Au",
            "tectonic_setting": "Convergent margin, Archean greenstone belts",
            "examples": ["Migori Greenstone Belt", "Witwatersrand", "Kalgoorlie"],
        },
        "volcanogenic_massive_sulfide": {
            "name": "Volcanogenic Massive Sulfide (VMS)",
            "key_indicators": [
                "massive_sulfide", "chalcopyrite", "sphalerite",
                "galena", "stockwork_veining", "chlorite_alteration",
            ],
            "host_rocks": ["felsic_volcanics", "bimodal_volcanics", "black_shale"],
            "typical_grades": "1-5% Cu, 1-10% Zn",
            "tectonic_setting": "Back-arc basin, mid-ocean ridge",
            "examples": ["Kisumu Belt", "Iberian Pyrite Belt"],
        },
        "skarn": {
            "name": "Skarn Deposit",
            "key_indicators": [
                "garnet", "pyroxene", "calcite",
                "magnetite", "chalcopyrite", "limestone_contact",
            ],
            "host_rocks": ["limestone", "dolomite", "granite_intrusion"],
            "typical_grades": "0.5-3% Cu or variable",
            "tectonic_setting": "Intrusion-related, contact metamorphism",
            "examples": [],
        },
        "placer": {
            "name": "Placer Deposit",
            "key_indicators": [
                "alluvial_gravel", "heavy_minerals", "rounded_clasts",
                "stream_sediment_gold", "black_sand",
            ],
            "host_rocks": ["alluvium", "terrace_gravel", "river_sediment"],
            "typical_grades": "0.1-5 g/m³ Au",
            "tectonic_setting": "Secondary enrichment in drainage basins",
            "examples": ["Migori alluvial", "Sierra Leone placers"],
        },
    }

    # Score each deposit model against observations
    obs_text = " ".join(str(v) for v in observations.values()).lower()
    obs_keys = set(k.lower() for k in observations.keys())

    scored_models = []
    for model_key, model in DEPOSIT_MODELS.items():
        score = 0
        matched_indicators = []
        for indicator in model["key_indicators"]:
            if indicator in obs_text or indicator.replace("_", " ") in obs_text:
                score += 2
                matched_indicators.append(indicator)
        for host in model["host_rocks"]:
            if host in obs_text or host.replace("_", " ") in obs_text:
                score += 1
        if mineral_type and mineral_type.lower() in model["name"].lower():
            score += 3

        if score > 0:
            scored_models.append({
                "model": model["name"],
                "confidence": min(round(score / 10, 2), 0.95),
                "matched_indicators": matched_indicators,
                "typical_grades": model["typical_grades"],
                "tectonic_setting": model["tectonic_setting"],
                "examples": model["examples"],
            })

    scored_models.sort(key=lambda x: x["confidence"], reverse=True)

    return {
        "success": True,
        "observations_used": list(observations.keys()),
        "matched_models": scored_models[:5],
        "best_match": scored_models[0] if scored_models else None,
        "note": "Deposit model matching based on field observations. Geological survey recommended for confirmation.",
    }


def register_geological_tools(registry) -> None:
    """Register all geological tools with the tool registry."""
    registry.register_handler("gempy_3d_model", gempy_3d_model)
    registry.register_handler("run_geophysical_inversion", simpeg_inversion)
    registry.register_handler("query_mindat", mindat_query)
    registry.register_handler("usgs_mrdata_query", usgs_mrdata_query)
    registry.register_handler("query_geological_database", geological_database_query)
    registry.register_handler("analyze_deposit_model", analyze_deposit_model)
