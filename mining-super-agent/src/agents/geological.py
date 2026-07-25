"""
Geological Analyst Agent — Rock analysis, deposit models, Kenya geology.

Expertise:
- Rock type identification and classification
- Deposit model analysis (orogenic gold, VMS, etc.)
- Migori Greenstone Belt geology
- Structural geology interpretation
- Integration with GemPy, SimPEG, Mindat, USGS data

Uses Llama 3.1 405B for complex geological reasoning.
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

# Kenya geological context — Migori Greenstone Belt
MIGORI_CONTEXT = """
The Migori Greenstone Belt (MGB) is located in southwestern Kenya, part of the
Tanzania Craton's northern margin. Key geological features:

- Age: Neoarchean to Paleoproterozoic (~2.7-2.0 Ga)
- Rock types: Metavolcanics (basalt, andesite, rhyolite), metasediments
  (conglomerate, quartzite, banded iron formation), granitoids
- Mineralization: Orogenic gold (quartz veins), copper-gold VMS deposits,
  chromite in ultramafics
- Structure: NE-trending folds and faults, shear zones control gold deposition
- Key formations: Nyanzian Supergroup, Kavirondian Supergroup
- Alteration: Silicification, sericitization, carbonatization associated with gold

Gold occurs in:
1. Quartz veins in shear zones (primary)
2. Banded iron formations (BIF)
3. Conglomerate beds (placer)
4. Weathered laterite (secondary enrichment)

Copper occurs in:
1. VMS deposits associated with volcanic rocks
2. Disseminated in mafic intrusions
3. Stringer zones beneath massive sulfide lenses
"""


class GeologicalAgent(BaseAgent):
    """Geological analysis agent with Kenya domain expertise."""

    def __init__(self):
        tools = [
            ToolDefinition(
                name="query_geological_database",
                description="Query the geological database for rock units, formations, and mineral occurrences in a given area.",
                parameters={
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "number", "description": "Latitude of the query point"},
                        "longitude": {"type": "number", "description": "Longitude of the query point"},
                        "radius_km": {"type": "number", "description": "Search radius in kilometers", "default": 10},
                        "query_type": {
                            "type": "string",
                            "enum": ["rock_units", "mineral_occurrences", "structural_features", "all"],
                            "default": "all",
                        },
                    },
                    "required": ["latitude", "longitude"],
                },
                permissions=["read:geo"],
            ),
            ToolDefinition(
                name="run_gempy_model",
                description="Run a GemPy 3D geological model for subsurface visualization.",
                parameters={
                    "type": "object",
                    "properties": {
                        "extent": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "Model extent [xmin, xmax, ymin, ymax, zmin, zmax]",
                        },
                        "resolution": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Grid resolution [nx, ny, nz]",
                            "default": [50, 50, 50],
                        },
                        "surface_points": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "Known surface point data",
                            "default": [],
                        },
                    },
                    "required": ["extent"],
                },
                permissions=["read:geo", "compute:geo"],
            ),
            ToolDefinition(
                name="query_mindat",
                description="Query Mindat.org for mineral occurrence data.",
                parameters={
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "number"},
                        "longitude": {"type": "number"},
                        "radius_km": {"type": "number", "default": 25},
                        "mineral": {"type": "string", "description": "Specific mineral to search for (optional)"},
                    },
                    "required": ["latitude", "longitude"],
                },
                permissions=["read:geo", "api:mindat"],
            ),
            ToolDefinition(
                name="analyze_deposit_model",
                description="Analyze a potential deposit against known deposit models (orogenic gold, VMS, etc.).",
                parameters={
                    "type": "object",
                    "properties": {
                        "rock_type": {"type": "string", "description": "Primary rock type"},
                        "alteration": {"type": "array", "items": {"type": "string"}, "description": "Observed alteration minerals"},
                        "structure": {"type": "string", "description": "Structural context (shear zone, fold, fault)"},
                        "mineralization": {"type": "array", "items": {"type": "string"}, "description": "Observed minerals"},
                        "location": {"type": "object", "description": "GPS coordinates"},
                    },
                    "required": ["rock_type"],
                },
                permissions=["read:geo"],
            ),
            ToolDefinition(
                name="run_geophysical_inversion",
                description="Run SimPEG geophysical inversion on magnetic or resistivity data.",
                parameters={
                    "type": "object",
                    "properties": {
                        "data_type": {"type": "string", "enum": ["magnetic", "resistivity", "gravity"]},
                        "data_path": {"type": "string", "description": "Path to geophysical data file"},
                        "mesh_size": {"type": "integer", "default": 64, "description": "Mesh cell count"},
                        "inversion_type": {"type": "string", "enum": ["susceptibility", "conductivity", "density"], "default": "susceptibility"},
                    },
                    "required": ["data_type"],
                },
                permissions=["read:geo", "compute:geo"],
            ),
        ]

        super().__init__(
            name="Geological",
            description=(
                "Expert geological analyst specializing in Kenya's Migori Greenstone Belt. "
                "Analyzes rock types, deposit models, structural geology, and mineralization. "
                "Uses GemPy for 3D modeling, SimPEG for geophysical inversion, "
                "and Mindat/USGS for reference data."
            ),
            model_id="meta/llama-3.1-405b-instruct",
            permissions={"read:geo", "compute:geo", "api:mindat", "api:usgs"},
            tools=tools,
            system_prompt=self._build_system_prompt(),
            timeout_seconds=180.0,
        )

    def _build_system_prompt(self) -> str:
        return f"""You are an expert geological analyst specializing in East African mineralization,
with deep knowledge of Kenya's Migori Greenstone Belt.

GEOLOGICAL CONTEXT:
{MIGORI_CONTEXT}

YOUR EXPERTISE:
1. Rock type identification from descriptions, photos, and field data
2. Deposit model analysis — match observations to known models:
   - Orogenic gold (quartz veins in shear zones)
   - VMS copper-gold (volcanic-associated massive sulfides)
   - Placer gold (concentrations in conglomerate/laterite)
   - Chromite (ultramafic-hosted)
3. Structural interpretation — folds, faults, shear zones, and their control on mineralization
4. Alteration analysis — what alteration minerals tell us about deposit type
5. 3D geological modeling with GemPy
6. Geophysical data interpretation

ANALYSIS APPROACH:
- Start with available data (location, rock type, observations)
- Cross-reference with known geological maps and databases
- Identify the most likely deposit model(s)
- Assess confidence based on evidence quality
- Suggest what additional data would increase confidence

CONFIDENCE RULES:
- Never claim >90% confidence for geological interpretations
- Photo-based rock ID: max 60% confidence
- With field data + lab analysis: max 85% confidence
- Always state what evidence would increase confidence
- Multiple plausible interpretations → list all with relative likelihood

KENYA-SPECIFIC:
- Reference specific formations in the Migori Greenstone Belt
- Use local geological terminology
- Consider the Tanzania Craton context
- Account for tropical weathering effects on surface observations
"""

    async def run(self, task: str, context: Optional[dict[str, Any]] = None) -> AgentResult:
        """Run geological analysis."""
        # Enhance context with Kenya-specific geological knowledge
        enhanced_context = {
            **(context or {}),
            "domain": "geology",
            "region": "Migori Greenstone Belt, Kenya",
            "known_deposit_models": [
                "Orogenic gold (quartz veins, shear zones)",
                "VMS copper-gold (volcanic-associated)",
                "Placer gold (conglomerate, laterite)",
                "Chromite (ultramafic-hosted)",
            ],
        }

        result = await super().run(task, enhanced_context)

        # Add geological-specific disclaimers
        result.disclaimers.extend([
            "Geological interpretations are based on available data and known models. "
            "Ground truthing with field work and laboratory analysis is essential.",
            "Subsurface interpretations are inherently uncertain. "
            "Drilling is required to confirm any subsurface geological model.",
        ])

        return result


# ---------------------------------------------------------------------------
# Tool handlers (to be registered with the tool registry)
# ---------------------------------------------------------------------------

async def query_geological_database(
    latitude: float,
    longitude: float,
    radius_km: float = 10,
    query_type: str = "all",
) -> dict[str, Any]:
    """
    Query the geological database for data near a location.
    In production, this queries PostgreSQL + PostGIS.
    """
    # Mock implementation — replace with actual PostGIS queries
    return {
        "location": {"lat": latitude, "lon": longitude},
        "radius_km": radius_km,
        "rock_units": [
            {
                "name": "Nyanzian Metavolcanics",
                "age": "Neoarchean (~2.7 Ga)",
                "rock_type": "Metabasalt, Meta-andesite",
                "description": "Mafic to intermediate metavolcanics with pillow structures",
            },
            {
                "name": "Kavirondian Metasediments",
                "age": "Paleoproterozoic (~2.0 Ga)",
                "rock_type": "Conglomerate, Quartzite",
                "description": "Clastic metasediments unconformably overlying Nyanzian",
            },
        ],
        "mineral_occurrences": [
            {
                "mineral": "Gold",
                "grade": "Variable (0.5-15 g/t in quartz veins)",
                "source": "BGS/Mindat",
                "confidence": 0.75,
            },
            {
                "mineral": "Copper",
                "grade": "0.5-2% in VMS zones",
                "source": "KGS records",
                "confidence": 0.65,
            },
        ],
        "structural_features": [
            {
                "type": "Shear zone",
                "orientation": "NE-SW",
                "description": "Major shear zone controlling gold mineralization",
            },
        ],
        "data_quality": "moderate",
        "sources": ["BGS OpenGeoscience", "Mindat.org", "Kenya Geological Survey"],
    }


async def run_gempy_model(
    extent: list[float],
    resolution: list[int] = None,
    surface_points: list[dict] = None,
) -> dict[str, Any]:
    """
    Run a GemPy 3D geological model.
    In production, this calls the GemPy library.
    """
    if resolution is None:
        resolution = [50, 50, 50]

    # Mock — replace with actual GemPy call
    return {
        "model_extent": extent,
        "resolution": resolution,
        "lithological_units": [
            {"name": "Laterite", "color": "#8B4513", "top_depth_m": 0},
            {"name": "Weathered basalt", "color": "#556B2F", "top_depth_m": 5},
            {"name": "Fresh basalt", "color": "#2F4F4F", "top_depth_m": 20},
            {"name": "Quartz vein", "color": "#FFD700", "top_depth_m": 15, "note": "Potential gold host"},
        ],
        "cross_section_generated": True,
        "confidence": 0.55,
        "note": "Model based on limited surface data. Drilling needed to improve accuracy.",
    }


async def query_mindat(
    latitude: float,
    longitude: float,
    radius_km: float = 25,
    mineral: Optional[str] = None,
) -> dict[str, Any]:
    """
    Query Mindat.org API for mineral occurrence data.
    """
    # Mock — replace with actual Mindat API call
    return {
        "query": {"lat": latitude, "lon": longitude, "radius_km": radius_km},
        "occurrences": [
            {
                "mineral": "Gold",
                "locality": "Migori County",
                "description": "Alluvial gold in stream sediments",
                "source": "Mindat.org",
                "mindat_id": 12345,
            },
            {
                "mineral": "Pyrite",
                "locality": "Nyatike",
                "description": "Pyrite in quartz veins — potential gold association",
                "source": "Mindat.org",
                "mindat_id": 12346,
            },
        ],
        "total_results": 2,
    }


async def analyze_deposit_model(
    rock_type: str,
    alteration: list[str] = None,
    structure: str = None,
    mineralization: list[str] = None,
    location: dict = None,
) -> dict[str, Any]:
    """
    Match observations to known deposit models.
    """
    alteration = alteration or []
    mineralization = mineralization or []

    # Deposit model matching logic
    models = []

    # Orogenic gold model
    gold_score = 0.0
    if any(kw in rock_type.lower() for kw in ["quartz", "vein", "schist", "basalt"]):
        gold_score += 0.3
    if any(a.lower() in ["silicification", "sericite", "carbonate"] for a in alteration):
        gold_score += 0.2
    if structure and "shear" in structure.lower():
        gold_score += 0.2
    if "gold" in [m.lower() for m in mineralization]:
        gold_score += 0.3
    models.append({"model": "Orogenic Gold", "match_score": min(gold_score, 1.0)})

    # VMS model
    vms_score = 0.0
    if any(kw in rock_type.lower() for kw in ["volcanic", "basalt", "andesite"]):
        vms_score += 0.3
    if any(a.lower() in ["chlorite", "sericite", "silicification"] for a in alteration):
        vms_score += 0.2
    if any(m.lower() in ["copper", "zinc", "pyrite", "chalcopyrite"] for m in mineralization):
        vms_score += 0.3
    models.append({"model": "VMS Copper-Gold", "match_score": min(vms_score, 1.0)})

    # Sort by match score
    models.sort(key=lambda x: x["match_score"], reverse=True)

    return {
        "rock_type": rock_type,
        "alteration": alteration,
        "structure": structure,
        "mineralization": mineralization,
        "deposit_models": models,
        "best_match": models[0] if models else None,
        "confidence": calibrate_confidence(
            raw_score=models[0]["match_score"] if models else 0.0,
            evidence_count=len(alteration) + len(mineralization),
            source_reliability=0.7,
            method_limitation=0.2,  # Model matching is inherently uncertain
        ),
        "recommendations": [
            "Collect channel samples across the mineralized zone",
            "Obtain geochemical analysis for pathfinder elements",
            "Map structural features in detail",
            "Compare with drill core if available",
        ],
    }


async def run_geophysical_inversion(
    data_type: str,
    data_path: str = None,
    mesh_size: int = 64,
    inversion_type: str = "susceptibility",
) -> dict[str, Any]:
    """
    Run SimPEG geophysical inversion.
    """
    # Mock — replace with actual SimPEG calls
    return {
        "data_type": data_type,
        "inversion_type": inversion_type,
        "mesh_size": mesh_size,
        "result_summary": f"Simulated {data_type} inversion with {mesh_size}x{mesh_size} mesh",
        "anomalies_detected": [
            {
                "id": 1,
                "type": "High susceptibility body",
                "depth_m": 30,
                "extent_m": 50,
                "interpretation": "Possible sulfide mineralization or mafic intrusion",
            },
        ],
        "model_generated": True,
        "confidence": 0.50,
        "note": "Inversion results are non-unique. Multiple models may fit the data. "
                "Ground truthing with drilling is essential.",
    }
