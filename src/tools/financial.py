"""
Financial Tools — NPV/IRR Calculations and Valuations
======================================================

Tools that the superagent uses for financial analysis.
NOT a separate agent — the superagent calls these tools directly.

Council requirement: Always use conservative assumptions, never optimistic.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Financial disclaimers
DISCLAIMER_FINANCIAL = "Hii ni takwimu tu, si uthibitisho wa kibenki. Tafadhali shauriana na mtaalamu wa fedha."
DISCLAIMER_EN = "This is indicative only, not bankable. Please consult a financial professional."


async def calculate_npv(
    mineral: str,
    annual_production_kg: float,
    price_per_kg: float,
    capex: float,
    opex_annual: float,
    mine_life_years: int = 10,
    discount_rate: float = 0.15,  # 15% — conservative for Kenya
    recovery_rate: float = 0.75,  # 75% — conservative for artisanal
) -> dict[str, Any]:
    """
    Calculate NPV/IRR for a mining project.
    
    Always uses conservative assumptions:
    - Discount rate: 15% (high for Kenya risk)
    - Recovery rate: 75% (artisanal mining typical)
    - Price: current market price (no optimism)
    """
    # Calculate annual revenue
    effective_production = annual_production_kg * recovery_rate
    annual_revenue = effective_production * price_per_kg
    annual_profit = annual_revenue - opex_annual
    
    # Calculate NPV
    cash_flows = [-capex]  # Year 0: investment
    for year in range(1, mine_life_years + 1):
        cash_flows.append(annual_profit)
    
    npv = np.npv(discount_rate, cash_flows)
    
    # Calculate IRR
    try:
        irr = np.irr(cash_flows)
    except:
        irr = None  # IRR may not converge
    
    # Calculate payback period
    cumulative = -capex
    payback_years = None
    for year in range(1, mine_life_years + 1):
        cumulative += annual_profit
        if cumulative >= 0 and payback_years is None:
            # Linear interpolation for exact payback
            prev_cumulative = cumulative - annual_profit
            fraction = -prev_cumulative / annual_profit
            payback_years = year - 1 + fraction
    
    # Sensitivity analysis
    sensitivity = {}
    for price_change in [-0.2, -0.1, 0, 0.1, 0.2]:
        adjusted_price = price_per_kg * (1 + price_change)
        adjusted_revenue = effective_production * adjusted_price
        adjusted_profit = adjusted_revenue - opex_annual
        adjusted_flows = [-capex] + [adjusted_profit] * mine_life_years
        adjusted_npv = np.npv(discount_rate, adjusted_flows)
        sensitivity[f"price_{int(price_change*100)}%"] = round(adjusted_npv, 2)
    
    return {
        "mineral": mineral,
        "npv": round(npv, 2),
        "irr": round(irr, 4) if irr else None,
        "payback_years": round(payback_years, 1) if payback_years else None,
        "annual_revenue": round(annual_revenue, 2),
        "annual_profit": round(annual_profit, 2),
        "capex": capex,
        "opex_annual": opex_annual,
        "mine_life_years": mine_life_years,
        "discount_rate": discount_rate,
        "recovery_rate": recovery_rate,
        "sensitivity": sensitivity,
        "assumptions": {
            "discount_rate": f"{discount_rate*100}% (conservative for Kenya)",
            "recovery_rate": f"{recovery_rate*100}% (artisanal mining typical)",
            "price": f"${price_per_kg}/kg (current market, no optimism)",
        },
        "disclaimer": DISCLAIMER_FINANCIAL,
        "disclaimer_en": DISCLAIMER_EN,
        "swahili_summary": _format_npv_swahili(npv, irr, payback_years),
    }


async def estimate_value(
    mineral: str,
    estimated_kg: float,
    price_per_kg: float,
    confidence: float = 0.5,
) -> dict[str, Any]:
    """
    Estimate the value of minerals on a piece of land.
    
    Conservative: uses confidence factor to scale estimate.
    """
    # Scale by confidence (conservative)
    effective_kg = estimated_kg * confidence
    
    # Value at current prices
    gross_value = effective_kg * price_per_kg
    
    # Net value (after typical costs)
    # Assume 40% goes to extraction costs
    net_value = gross_value * 0.6
    
    return {
        "mineral": mineral,
        "estimated_kg": estimated_kg,
        "effective_kg": effective_kg,
        "confidence": confidence,
        "price_per_kg": price_per_kg,
        "gross_value_usd": round(gross_value, 2),
        "gross_value_kes": round(gross_value * 130, 2),  # Approximate KES
        "net_value_usd": round(net_value, 2),
        "net_value_kes": round(net_value * 130, 2),
        "note": "Value scaled by confidence factor. Actual value depends on extraction feasibility.",
        "disclaimer": DISCLAIMER_FINANCIAL,
        "swahili_summary": (
            f"Thamani ya {mineral}: "
            f"${round(net_value, 2)} USD (KES {round(net_value * 130, 2)}). "
            f"Uhakika: {int(confidence*100)}%. "
            f"{DISCLAIMER_FINANCIAL}"
        ),
    }


def _format_npv_swahili(npv: float, irr: float | None, payback: float | None) -> str:
    """Format NPV results in Swahili."""
    parts = [f"NPV: ${round(npv, 2)} USD"]
    
    if irr:
        parts.append(f"IRR: {round(irr*100, 1)}%")
    
    if payback:
        parts.append(f"Muda wa kurejesha: {round(payback, 1)} miaka")
    
    parts.append(DISCLAIMER_FINANCIAL)
    
    return ". ".join(parts)


def register_financial_tools(registry) -> None:
    """Register all financial tools with the tool registry."""
    from .schemas import NPVInput, NPVOutput, ValueEstimateInput, ValueEstimateOutput

    registry.register_handler(
        "npv_calculator",
        calculate_npv,
        input_schema=NPVInput,
        output_schema=NPVOutput,
    )
    registry.register_handler(
        "value_estimator",
        estimate_value,
        input_schema=ValueEstimateInput,
        output_schema=ValueEstimateOutput,
    )
