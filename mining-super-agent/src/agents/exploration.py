"""
Exploration Planner Agent — Drilling programs, sampling, geophysics.

Covers:
- Drilling program design (RC, diamond, auger)
- Sampling strategy (channel, chip, grab, soil)
- Geophysical survey planning (magnetic, resistivity, IP)
- Cost estimation for exploration programs
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .base import AgentResult, BaseAgent, ToolDefinition, calibrate_confidence

logger = logging.getLogger(__name__)


class ExplorationAgent(BaseAgent):
    """Exploration planning agent for drill programs and surveys."""

    def __init__(self):
        tools = [
            ToolDefinition(
                name="design_drilling_program",
                description="Design a drilling program for mineral exploration.",
                parameters={
                    "type": "object",
                    "properties": {
                        "target_type": {
                            "type": "string",
                            "enum": ["gold_vein", "copper_vms", "placer", "reconnaissance"],
                        },
                        "area_ha": {"type": "number", "description": "Exploration area in hectares"},
                        "budget_usd": {"type": "number", "description": "Available budget in USD"},
                        "existing_data": {
                            "type": "string",
                            "description": "Description of existing geological/geophysical data",
                        },
                        "drill_type_preference": {
                            "type": "string",
                            "enum": ["diamond", "rc", "auger", "auto"],
                            "default": "auto",
                        },
                    },
                    "required": ["target_type", "area_ha"],
                },
                permissions=["plan:exploration"],
            ),
            ToolDefinition(
                name="design_sampling_strategy",
                description="Design a sampling strategy for a mineral exploration project.",
                parameters={
                    "type": "object",
                    "properties": {
                        "target_mineral": {"type": "string"},
                        "terrain": {
                            "type": "string",
                            "enum": ["flat", "hilly", "riverine", "forest"],
                        },
                        "sampling_type": {
                            "type": "string",
                            "enum": ["soil", "stream_sediment", "rock_chip", "channel", "grab"],
                            "default": "soil",
                        },
                        "area_ha": {"type": "number"},
                    },
                    "required": ["target_mineral", "area_ha"],
                },
                permissions=["plan:exploration"],
            ),
            ToolDefinition(
                name="plan_geophysical_survey",
                description="Plan a geophysical survey (magnetic, resistivity, IP).",
                parameters={
                    "type": "object",
                    "properties": {
                        "survey_type": {
                            "type": "string",
                            "enum": ["magnetic", "resistivity", "ip", "gravity", "combined"],
                        },
                        "area_ha": {"type": "number"},
                        "target_depth_m": {"type": "number", "default": 100},
                        "resolution": {
                            "type": "string",
                            "enum": ["reconnaissance", "detailed", "very_detailed"],
                            "default": "detailed",
                        },
                    },
                    "required": ["survey_type", "area_ha"],
                },
                permissions=["plan:exploration"],
            ),
            ToolDefinition(
                name="estimate_exploration_costs",
                description="Estimate costs for an exploration program.",
                parameters={
                    "type": "object",
                    "properties": {
                        "drilling_meters": {"type": "number", "default": 0},
                        "drill_type": {"type": "string", "enum": ["diamond", "rc", "auger"], "default": "diamond"},
                        "soil_samples": {"type": "integer", "default": 0},
                        "rock_samples": {"type": "integer", "default": 0},
                        "geophysical_survey_ha": {"type": "number", "default": 0},
                        "survey_type": {"type": "string", "default": "magnetic"},
                        "assays_per_sample": {"type": "integer", "default": 1},
                    },
                    "required": [],
                },
                permissions=["plan:exploration"],
            ),
        ]

        super().__init__(
            name="Exploration",
            description=(
                "Exploration planning agent for designing drilling programs, "
                "sampling strategies, and geophysical surveys. "
                "Provides cost estimates and work programs."
            ),
            model_id="meta/llama-3.1-405b-instruct",
            permissions={"plan:exploration", "read:geo"},
            tools=tools,
            system_prompt=self._build_system_prompt(),
        )

    def _build_system_prompt(self) -> str:
        return """You are a mineral exploration planning specialist.

DRILLING KNOWLEDGE:
1. DIAMOND DRILLING (DD):
   - Best for: detailed exploration, core recovery, structural geology
   - Cost: $50-150/meter (depends on depth, terrain)
   - Advantages: continuous core, structural data, high recovery
   - Disadvantages: slow, expensive, needs water

2. REVERSE CIRCULATION (RC):
   - Best for: grade control, bulk sampling, medium depth
   - Cost: $30-80/meter
   - Advantages: faster than DD, cheaper, no water needed
   - Disadvantages: no core, sample contamination risk

3. AUGER DRILLING:
   - Best for: shallow soil sampling, placer deposits
   - Cost: $10-30/meter
   - Advantages: cheap, fast, portable
   - Disadvantages: shallow only (<30m), limited in hard rock

SAMPLING KNOWLEDGE:
- Soil sampling: grid pattern, 50-200m spacing for reconnaissance
- Stream sediment: catchment-wide, good for regional exploration
- Rock chip: outcrop sampling, 1-2kg per sample
- Channel: continuous sampling across mineralized zone

GEOPHYSICAL SURVEYS:
- Magnetic: detects magnetic minerals (magnetite, pyrrhotite), structural features
- Resistivity: maps conductivity contrasts (sulfides, clay, water)
- IP (Induced Polarization): detects disseminated sulfides (best for gold/copper)
- Gravity: density contrasts (massive sulfides, salt domes)

COST ESTIMATION RULES:
- Always include 20% contingency
- Include mobilization/demobilization costs
- Include assay costs ($20-50 per sample for multi-element)
- Include field crew costs (camp, transport, safety)
- Kenya-specific: road access may be poor, add logistics cost
"""

    async def run(self, task: str, context: Optional[dict[str, Any]] = None) -> AgentResult:
        """Run exploration planning."""
        result = await super().run(task, context)
        result.disclaimers.extend([
            "Exploration plans are preliminary and should be reviewed by a qualified geologist.",
            "Cost estimates are indicative (±30-50%). Obtain quotes from drilling contractors.",
            "All exploration requires appropriate licenses and environmental approvals.",
        ])
        return result


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

async def design_drilling_program(
    target_type: str,
    area_ha: float,
    budget_usd: float = 0,
    existing_data: str = "",
    drill_type_preference: str = "auto",
) -> dict[str, Any]:
    """Design a drilling program."""
    # Auto-select drill type
    if drill_type_preference == "auto":
        if target_type == "placer":
            drill_type = "auger"
        elif target_type == "reconnaissance":
            drill_type = "rc"
        else:
            drill_type = "diamond"
    else:
        drill_type = drill_type_preference

    # Estimate meters based on area and target
    line_spacing = 200 if target_type == "reconnaissance" else 100
    hole_spacing = 100 if target_type == "reconnaissance" else 50
    holes_per_line = max(3, int((area_ha ** 0.5 * 100) / hole_spacing))
    num_lines = max(2, int((area_ha ** 0.5 * 100) / line_spacing))
    total_holes = holes_per_line * num_lines
    avg_depth = 30 if drill_type == "auger" else 60 if drill_type == "rc" else 80
    total_meters = total_holes * avg_depth

    # Cost estimation
    cost_per_m = {"diamond": 100, "rc": 55, "auger": 20}.get(drill_type, 100)
    drilling_cost = total_meters * cost_per_m
    mobilization = 5000 if drill_type == "auger" else 15000
    assay_cost = total_holes * 5 * 35  # 5 samples per hole, $35 each
    total_cost = drilling_cost + mobilization + assay_cost

    return {
        "target_type": target_type,
        "area_ha": area_ha,
        "drill_type": drill_type,
        "program_design": {
            "num_lines": num_lines,
            "holes_per_line": holes_per_line,
            "total_holes": total_holes,
            "line_spacing_m": line_spacing,
            "hole_spacing_m": hole_spacing,
            "avg_depth_m": avg_depth,
            "total_meters": total_meters,
        },
        "cost_estimate_usd": {
            "drilling": round(drilling_cost, 2),
            "mobilization": round(mobilization, 2),
            "assays": round(assay_cost, 2),
            "contingency_20pct": round(total_cost * 0.2, 2),
            "total": round(total_cost * 1.2, 2),
        },
        "timeline_weeks": max(4, total_holes // 5),
        "assays_recommended": [
            "Fire assay for gold (50g sample)",
            "Multi-element ICP-MS",
            "Specific gravity",
        ],
    }


async def design_sampling_strategy(
    target_mineral: str,
    area_ha: float,
    terrain: str = "flat",
    sampling_type: str = "soil",
) -> dict[str, Any]:
    """Design a sampling strategy."""
    spacing_map = {
        "reconnaissance": 200,
        "detailed": 100,
        "very_detailed": 50,
    }
    spacing = spacing_map["detailed"]

    num_samples = int(area_ha * 10000 / (spacing * spacing))

    return {
        "target_mineral": target_mineral,
        "sampling_type": sampling_type,
        "area_ha": area_ha,
        "strategy": {
            "grid_type": "regular grid" if terrain == "flat" else "contour-parallel",
            "spacing_m": spacing,
            "estimated_samples": num_samples,
            "sample_depth_cm": 20 if sampling_type == "soil" else 0,
            "sample_weight_kg": 1.0,
        },
        "cost_estimate_usd": {
            "field_collection": num_samples * 5,
            "assays": num_samples * 35,
            "transport": 500,
            "total": round(num_samples * 40 + 500, 2),
        },
        "assays": [
            f"Multi-element ICP-MS for {target_mineral} pathfinders",
            "Gold by fire assay (if gold target)",
        ],
    }


async def plan_geophysical_survey(
    survey_type: str,
    area_ha: float,
    target_depth_m: float = 100,
    resolution: str = "detailed",
) -> dict[str, Any]:
    """Plan a geophysical survey."""
    line_spacing = {
        "reconnaissance": 400,
        "detailed": 200,
        "very_detailed": 100,
    }.get(resolution, 200)

    total_line_km = (area_ha * 10000 / (line_spacing * 1000)) * (area_ha ** 0.5)

    cost_per_km = {
        "magnetic": 200,
        "resistivity": 500,
        "ip": 800,
        "gravity": 300,
    }.get(survey_type, 300)

    survey_cost = total_line_km * cost_per_km

    return {
        "survey_type": survey_type,
        "area_ha": area_ha,
        "resolution": resolution,
        "parameters": {
            "line_spacing_m": line_spacing,
            "total_line_km": round(total_line_km, 1),
            "target_depth_m": target_depth_m,
        },
        "cost_estimate_usd": {
            "survey": round(survey_cost, 2),
            "mobilization": 3000,
            "data_processing": round(survey_cost * 0.15, 2),
            "total": round(survey_cost * 1.15 + 3000, 2),
        },
        "timeline_weeks": max(2, int(total_line_km / 10)),
        "deliverables": [
            "Processed geophysical maps",
            "Anomaly interpretation report",
            "Drill target recommendations",
        ],
    }


async def estimate_exploration_costs(
    drilling_meters: float = 0,
    drill_type: str = "diamond",
    soil_samples: int = 0,
    rock_samples: int = 0,
    geophysical_survey_ha: float = 0,
    survey_type: str = "magnetic",
    assays_per_sample: int = 1,
) -> dict[str, Any]:
    """Estimate total exploration costs."""
    costs = {}

    if drilling_meters > 0:
        rate = {"diamond": 100, "rc": 55, "auger": 20}.get(drill_type, 100)
        costs["drilling"] = drilling_meters * rate

    if soil_samples > 0:
        costs["soil_collection"] = soil_samples * 5
        costs["soil_assays"] = soil_samples * assays_per_sample * 35

    if rock_samples > 0:
        costs["rock_collection"] = rock_samples * 3
        costs["rock_assays"] = rock_samples * assays_per_sample * 35

    if geophysical_survey_ha > 0:
        rate_per_ha = {"magnetic": 50, "resistivity": 150, "ip": 250}.get(survey_type, 100)
        costs["geophysical_survey"] = geophysical_survey_ha * rate_per_ha

    subtotal = sum(costs.values())
    contingency = subtotal * 0.20
    mobilization = 5000
    total = subtotal + contingency + mobilization

    return {
        "breakdown": {k: round(v, 2) for k, v in costs.items()},
        "subtotal": round(subtotal, 2),
        "contingency_20pct": round(contingency, 2),
        "mobilization": mobilization,
        "total_usd": round(total, 2),
        "disclaimer": "Indicative estimate (±30-50%). Get contractor quotes for budgeting.",
    }
