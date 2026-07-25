"""
Financial Modeler Agent — NPV/IRR, CAPEX/OPEX, sensitivity analysis.

Key principles:
- Conservative assumptions (never optimistic)
- Clear disclaimers ("indicative, not bankable")
- Sensitivity analysis for key variables
- Monte Carlo simulation for risk assessment
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


class FinancialAgent(BaseAgent):
    """Financial modeling agent for mining project evaluation."""

    def __init__(self):
        tools = [
            ToolDefinition(
                name="calculate_npv_irr",
                description="Calculate Net Present Value (NPV) and Internal Rate of Return (IRR) for a mining project.",
                parameters={
                    "type": "object",
                    "properties": {
                        "initial_capex": {"type": "number", "description": "Initial capital expenditure in USD"},
                        "annual_revenue": {"type": "number", "description": "Expected annual revenue in USD"},
                        "annual_opex": {"type": "number", "description": "Annual operating expenditure in USD"},
                        "project_life_years": {"type": "integer", "description": "Project life in years"},
                        "discount_rate": {"type": "number", "default": 0.10, "description": "Discount rate (e.g., 0.10 for 10%)"},
                        "terminal_value": {"type": "number", "default": 0, "description": "Terminal/residual value"},
                    },
                    "required": ["initial_capex", "annual_revenue", "annual_opex", "project_life_years"],
                },
                permissions=["compute:financial"],
            ),
            ToolDefinition(
                name="estimate_capex",
                description="Estimate capital expenditure for a mining project based on type and scale.",
                parameters={
                    "type": "object",
                    "properties": {
                        "mine_type": {
                            "type": "string",
                            "enum": ["open_pit", "underground", "alluvial", "artisanal"],
                        },
                        "capacity_tpd": {"type": "number", "description": "Processing capacity in tonnes per day"},
                        "mineral": {"type": "string", "description": "Primary mineral"},
                        "location_remote": {"type": "boolean", "default": True, "description": "Is the site remote?"},
                    },
                    "required": ["mine_type", "capacity_tpd", "mineral"],
                },
                permissions=["compute:financial"],
            ),
            ToolDefinition(
                name="estimate_opex",
                description="Estimate operating expenditure per tonne of ore processed.",
                parameters={
                    "type": "object",
                    "properties": {
                        "mine_type": {"type": "string", "enum": ["open_pit", "underground", "alluvial"]},
                        "capacity_tpd": {"type": "number"},
                        "mineral": {"type": "string"},
                        "processing_method": {
                            "type": "string",
                            "enum": ["gravity", "flotation", "cyanidation", "heap_leach", "artisanal"],
                            "default": "gravity",
                        },
                    },
                    "required": ["mine_type", "capacity_tpd", "mineral"],
                },
                permissions=["compute:financial"],
            ),
            ToolDefinition(
                name="sensitivity_analysis",
                description="Perform sensitivity analysis on key financial variables.",
                parameters={
                    "type": "object",
                    "properties": {
                        "base_case": {
                            "type": "object",
                            "description": "Base case NPV/IRR inputs",
                            "properties": {
                                "npv": {"type": "number"},
                                "irr": {"type": "number"},
                            },
                        },
                        "variables": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "gold_price", "grade", "recovery",
                                    "capex", "opex", "discount_rate",
                                ],
                            },
                            "default": ["gold_price", "grade", "capex"],
                        },
                        "variation_pct": {"type": "number", "default": 20, "description": "Variation percentage to test"},
                    },
                    "required": ["base_case"],
                },
                permissions=["compute:financial"],
            ),
        ]

        super().__init__(
            name="Financial",
            description=(
                "Financial modeling agent for mining project evaluation. "
                "Calculates NPV, IRR, CAPEX, OPEX, and sensitivity analysis. "
                "Uses conservative assumptions and provides clear disclaimers."
            ),
            model_id="meta/llama-3.1-405b-instruct",
            permissions={"compute:financial", "read:market"},
            tools=tools,
            system_prompt=self._build_system_prompt(),
        )

    def _build_system_prompt(self) -> str:
        return """You are a mining financial analyst specializing in project evaluation.

FINANCIAL PRINCIPLES:
1. CONSERVATIVE ASSUMPTIONS — never optimistic
   - Use lower-bound grade estimates
   - Use higher-bound cost estimates
   - Apply appropriate discount rates (10-15% for mining)
   - Include contingency (15-25% of CAPEX)

2. KEY METRICS:
   - NPV (Net Present Value): Must be positive for viable project
   - IRR (Internal Rate of Return): Must exceed cost of capital (typically >15%)
   - Payback Period: Prefer <5 years for small-scale
   - CAPEX/OPEX: Break down by component

3. SENSITIVITY ANALYSIS:
   - Test key variables: gold price, grade, recovery, CAPEX, OPEX
   - Identify break-even points
   - Show which variables have most impact
   - Monte Carlo simulation for risk distribution

4. DISCLAIMERS (ALWAYS INCLUDE):
   - "This is an indicative financial model, NOT a bankable feasibility study"
   - "Actual costs may vary significantly from estimates"
   - "Professional financial and technical due diligence is required before investment"
   - "All projections are based on assumptions that may not hold"

CAPEX COMPONENTS (for reference):
- Mine development: 20-30% of total
- Processing plant: 30-40%
- Infrastructure (roads, power, water): 15-20%
- Environmental and community: 5-10%
- Contingency: 15-25%

OPEX COMPONENTS:
- Mining costs (drilling, blasting, hauling): 30-40%
- Processing costs (crushing, grinding, recovery): 25-35%
- Labor: 15-25%
- Energy: 10-15%
- Maintenance: 5-10%
- Administration: 5-10%

KENYA-SPECIFIC:
- Power costs: $0.15-0.25/kWh (high — factor in solar/generator)
- Labor costs: relatively low but skilled labor scarce
- Logistics: road infrastructure may be poor
- Royalty: 5% of gross revenue
- Corporate tax: 30%
"""

    async def run(self, task: str, context: Optional[dict[str, Any]] = None) -> AgentResult:
        """Run financial analysis."""
        result = await super().run(task, context)

        result.disclaimers.extend([
            "This is an INDICATIVE financial model, NOT a bankable feasibility study. "
            "Professional financial and technical due diligence is required before any investment decision.",
            "All projections are based on assumptions that may not hold. "
            "Actual costs and revenues may vary significantly.",
            "Mining projects carry significant financial, technical, and regulatory risks. "
            "Past performance of similar projects does not guarantee future results.",
        ])

        return result


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

async def calculate_npv_irr(
    initial_capex: float,
    annual_revenue: float,
    annual_opex: float,
    project_life_years: int,
    discount_rate: float = 0.10,
    terminal_value: float = 0,
) -> dict[str, Any]:
    """Calculate NPV and IRR."""
    # NPV calculation
    annual_cash_flow = annual_revenue - annual_opex
    npv = -initial_capex
    for year in range(1, project_life_years + 1):
        npv += annual_cash_flow / ((1 + discount_rate) ** year)
    # Add terminal value
    npv += terminal_value / ((1 + discount_rate) ** project_life_years)

    # IRR calculation (Newton's method)
    irr = _find_irr(initial_capex, annual_cash_flow, project_life_years, terminal_value)

    # Payback period
    payback_years = initial_capex / annual_cash_flow if annual_cash_flow > 0 else float('inf')

    return {
        "npv_usd": round(npv, 2),
        "irr_pct": round(irr * 100, 2) if irr else None,
        "payback_years": round(payback_years, 1),
        "annual_cash_flow": round(annual_cash_flow, 2),
        "total_revenue": round(annual_revenue * project_life_years, 2),
        "total_opex": round(annual_opex * project_life_years, 2),
        "discount_rate_pct": round(discount_rate * 100, 1),
        "viability": "POSITIVE" if npv > 0 and irr and irr > 0.15 else "MARGINAL" if npv > 0 else "NEGATIVE",
        "disclaimer": "Indicative only. Not a bankable feasibility study.",
    }


def _find_irr(
    capex: float,
    annual_cf: float,
    years: int,
    terminal: float,
    tolerance: float = 0.0001,
    max_iter: int = 1000,
) -> Optional[float]:
    """Find IRR using Newton-Raphson method."""
    rate = 0.10  # Initial guess
    for _ in range(max_iter):
        npv = -capex
        dnpv = 0
        for y in range(1, years + 1):
            npv += annual_cf / ((1 + rate) ** y)
            dnpv -= y * annual_cf / ((1 + rate) ** (y + 1))
        npv += terminal / ((1 + rate) ** years)
        dnpv -= years * terminal / ((1 + rate) ** (years + 1))

        if abs(dnpv) < 1e-12:
            break
        new_rate = rate - npv / dnpv
        if abs(new_rate - rate) < tolerance:
            return new_rate
        rate = new_rate

    return rate if -1 < rate < 10 else None


async def estimate_capex(
    mine_type: str,
    capacity_tpd: float,
    mineral: str,
    location_remote: bool = True,
) -> dict[str, Any]:
    """Estimate CAPEX for a mining project."""
    # Base costs per tonne/day capacity (USD)
    base_costs = {
        "open_pit": 15000,
        "underground": 35000,
        "alluvial": 8000,
        "artisanal": 500,
    }

    base = base_costs.get(mine_type, 15000)
    base_capex = base * capacity_tpd

    # Remote location multiplier
    if location_remote:
        base_capex *= 1.3

    # Breakdown
    breakdown = {
        "mine_development": base_capex * 0.25,
        "processing_plant": base_capex * 0.35,
        "infrastructure": base_capex * 0.18,
        "environmental_community": base_capex * 0.07,
        "contingency": base_capex * 0.15,
    }

    return {
        "mine_type": mine_type,
        "capacity_tpd": capacity_tpd,
        "mineral": mineral,
        "remote_location": location_remote,
        "total_capex_usd": round(base_capex, 2),
        "capex_per_tpd": round(base, 2),
        "breakdown_usd": {k: round(v, 2) for k, v in breakdown.items()},
        "contingency_pct": 15,
        "disclaimer": "Rough order-of-magnitude estimate. ±50% accuracy. Detailed engineering study required.",
    }


async def estimate_opex(
    mine_type: str,
    capacity_tpd: float,
    mineral: str,
    processing_method: str = "gravity",
) -> dict[str, Any]:
    """Estimate OPEX per tonne."""
    # Base OPEX per tonne (USD)
    base_costs = {
        "open_pit": 12,
        "underground": 35,
        "alluvial": 8,
    }

    processing_costs = {
        "gravity": 5,
        "flotation": 12,
        "cyanidation": 18,
        "heap_leach": 10,
        "artisanal": 2,
    }

    mining_cost = base_costs.get(mine_type, 15)
    processing_cost = processing_costs.get(processing_method, 10)

    total_per_tonne = mining_cost + processing_cost

    # Breakdown
    breakdown = {
        "mining": mining_cost,
        "processing": processing_cost,
        "labor": total_per_tonne * 0.20,
        "energy": total_per_tonne * 0.12,
        "maintenance": total_per_tonne * 0.08,
        "admin": total_per_tonne * 0.05,
    }

    annual_opex = total_per_tonne * capacity_tpd * 365

    return {
        "mine_type": mine_type,
        "processing_method": processing_method,
        "opex_per_tonne_usd": round(total_per_tonne, 2),
        "breakdown_per_tonne": {k: round(v, 2) for k, v in breakdown.items()},
        "annual_opex_usd": round(annual_opex, 2),
        "capacity_tpd": capacity_tpd,
        "disclaimer": "Indicative estimate. Actual costs depend on local conditions.",
    }


async def sensitivity_analysis(
    base_case: dict[str, Any],
    variables: list[str] = None,
    variation_pct: float = 20,
) -> dict[str, Any]:
    """Perform sensitivity analysis on key variables."""
    if variables is None:
        variables = ["gold_price", "grade", "capex"]

    base_npv = base_case.get("npv", 0)
    results = {}

    for var in variables:
        # Model the sensitivity (simplified)
        impact_factors = {
            "gold_price": 1.5,      # High impact
            "grade": 1.3,           # High impact
            "recovery": 1.0,        # Medium impact
            "capex": -0.8,          # Negative (higher capex = lower NPV)
            "opex": -0.6,           # Negative
            "discount_rate": -0.5,  # Negative
        }

        factor = impact_factors.get(var, 1.0)
        npv_change = base_npv * (variation_pct / 100) * factor

        results[var] = {
            "base_value": "see base_case",
            "variation_pct": variation_pct,
            "npv_if_up": round(base_npv + npv_change, 2),
            "npv_if_down": round(base_npv - npv_change, 2),
            "impact": "HIGH" if abs(factor) >= 1.0 else "MEDIUM" if abs(factor) >= 0.7 else "LOW",
            "direction": "positive" if factor > 0 else "negative",
        }

    # Find most sensitive variable
    most_sensitive = max(results.items(), key=lambda x: abs(impact_factors.get(x[0], 1.0)))

    return {
        "base_npv": base_npv,
        "variation_pct": variation_pct,
        "sensitivity_results": results,
        "most_sensitive_variable": most_sensitive[0],
        "recommendation": f"Focus risk mitigation on '{most_sensitive[0]}' — it has the highest impact on project viability.",
        "disclaimer": "Simplified sensitivity analysis. Monte Carlo simulation recommended for comprehensive risk assessment.",
    }
