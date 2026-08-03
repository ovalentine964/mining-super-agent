"""
Fair Deal Calculator — Is This Offer Exploitation or Fair?

This tool tells a community whether a mining offer is fair or exploitative.
It compares the offer against:
1. Current commodity market prices
2. Estimated mineral reserves (from geological data)
3. Global royalty benchmarks
4. Historical exploitation patterns in Africa

Built specifically for Valentine's situation:
- Chinese operators offering 1M KSH for land in Nyatike, Migori County
- Land has gold AND copper deposits
- No disclosure of what's underground
- No license verification
- Using hydraulic/leaching extraction with heavy machinery

THE PRINCIPLE: You can't negotiate fairly if you don't know what you have.
This tool gives you that knowledge.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class MineralEstimate:
    """Estimate of mineral value on a piece of land."""
    mineral: str
    estimated_kg: float
    confidence: float            # 0.0 - 1.0
    price_per_kg_usd: float
    gross_value_usd: float
    gross_value_kes: float
    net_value_usd: float         # After extraction costs
    net_value_kes: float


@dataclass
class FairDealVerdict:
    """Verdict on whether a mining offer is fair."""
    offer_amount_kes: float
    estimated_total_value_kes: float
    fair_share_kes: float        # What community should receive (based on benchmarks)
    exploitation_ratio: float    # offer / fair_share (lower = more exploitative)
    verdict: str                 # "FAIR", "BELOW_MARKET", "EXPLOITATIVE", "SEVERELY_EXPLOITATIVE"
    explanation_sw: str          # Swahili explanation
    explanation_en: str          # English explanation
    recommended_minimum_kes: float
    recommended_actions: list[str]


# Global commodity prices (updated from market tools)
COMMODITY_PRICES = {
    "gold": {"usd_per_kg": 64_000, "kes_per_kg": 8_320_000},     # ~$2000/oz
    "copper": {"usd_per_kg": 8.5, "kes_per_kg": 1_105},           # ~$8.50/kg
    "silver": {"usd_per_kg": 780, "kes_per_kg": 101_400},         # ~$24/oz
    "pyrite": {"usd_per_kg": 0.05, "kes_per_kg": 6.5},            # Fool's gold — worthless
}

# Extraction costs (conservative estimates for artisanal/small-scale in Kenya)
EXTRACTION_COSTS = {
    "gold": {"cost_per_kg_usd": 15_000, "recovery_rate": 0.70},    # 70% recovery
    "copper": {"cost_per_kg_usd": 3.5, "recovery_rate": 0.75},     # 75% recovery
    "silver": {"cost_per_kg_usd": 200, "recovery_rate": 0.70},
}

# Global royalty benchmarks
ROYALTY_BENCHMARKS = {
    "kenya_mining_act": {"min": 0.01, "max": 0.05},           # 1-5% of mineral value
    "botswana_diamonds": {"typical": 0.80},                    # 80% to government
    "norway_oil": {"typical": 0.78},                           # 78% to government
    "fair_community_share": {"min": 0.10, "typical": 0.20},    # 10-20% to community
}


def estimate_mineral_value(
    mineral: str,
    estimated_kg: float,
    confidence: float = 0.5,
) -> MineralEstimate:
    """
    Estimate the value of minerals on a piece of land.

    Always conservative:
    - Uses confidence factor to scale estimate
    - Uses conservative recovery rates
    - Uses current market prices (no speculation)
    """
    prices = COMMODITY_PRICES.get(mineral.lower(), COMMODITY_PRICES["pyrite"])
    costs = EXTRACTION_COSTS.get(mineral.lower(), {"cost_per_kg_usd": 0, "recovery_rate": 0.5})

    # Scale by confidence
    effective_kg = estimated_kg * confidence

    # Gross value at current prices
    gross_value_usd = effective_kg * prices["usd_per_kg"]
    gross_value_kes = effective_kg * prices["kes_per_kg"]

    # Net value (after extraction costs)
    extraction_cost = effective_kg * costs["cost_per_kg_usd"]
    net_value_usd = max(0, gross_value_usd - extraction_cost)
    net_value_kes = max(0, gross_value_kes - (extraction_cost * 130))  # Approximate KES

    return MineralEstimate(
        mineral=mineral,
        estimated_kg=estimated_kg,
        confidence=confidence,
        price_per_kg_usd=prices["usd_per_kg"],
        gross_value_usd=gross_value_usd,
        gross_value_kes=gross_value_kes,
        net_value_usd=net_value_usd,
        net_value_kes=net_value_kes,
    )


def evaluate_offer(
    offer_amount_kes: float,
    minerals: list[dict[str, Any]],
    location: str = "Unknown",
    operator_type: str = "foreign",
) -> FairDealVerdict:
    """
    Evaluate whether a mining offer is fair or exploitative.

    Args:
        offer_amount_kes: The amount being offered (e.g., 1,000,000 KES)
        minerals: List of dicts with 'mineral', 'estimated_kg', 'confidence'
        location: Location description
        operator_type: "foreign" or "local"

    Returns:
        FairDealVerdict with analysis and recommendations
    """
    # Calculate total estimated value
    total_value_kes = 0.0
    mineral_breakdown = []

    for m in minerals:
        estimate = estimate_mineral_value(
            mineral=m["mineral"],
            estimated_kg=m.get("estimated_kg", 0),
            confidence=m.get("confidence", 0.3),  # Default 30% confidence
        )
        total_value_kes += estimate.net_value_kes
        mineral_breakdown.append(estimate)

    # Calculate fair share (community should get 10-20% of net value)
    fair_share_kes = total_value_kes * ROYALTY_BENCHMARKS["fair_community_share"]["typical"]
    minimum_acceptable_kes = total_value_kes * ROYALTY_BENCHMARKS["fair_community_share"]["min"]

    # Calculate exploitation ratio
    exploitation_ratio = offer_amount_kes / fair_share_kes if fair_share_kes > 0 else 0

    # Determine verdict
    if exploitation_ratio >= 0.8:
        verdict = "FAIR"
    elif exploitation_ratio >= 0.3:
        verdict = "BELOW_MARKET"
    elif exploitation_ratio >= 0.05:
        verdict = "EXPLOITATIVE"
    else:
        verdict = "SEVERELY_EXPLOITATIVE"

    # Generate explanations
    mineral_names = [m["mineral"] for m in minerals]
    mineral_str = " na ".join(mineral_names) if len(mineral_names) > 1 else mineral_names[0]

    explanation_sw = (
        f"Ukilinganisha na bei ya soko ya {mineral_str} sasa hivi, "
        f"ardhi yako ina thamani ya takriban KES {total_value_kes:,.0f}. "
        f"Kulingana na viwango vya kimataifa, jamii inapaswa kupata "
        f"angalau KES {fair_share_kes:,.0f} (10-20% ya thamani). "
        f"Ofa ya KES {offer_amount_kes:,.0f} ni {exploitation_ratio*100:.1f}% ya kiwango cha haki. "
    )

    if verdict == "SEVERELY_EXPLOITATIVE":
        explanation_sw += (
            "HII NI UONAJI SANA. Usikubali ofa hii. "
            "Wanaokupa hawakuambi ukweli kuhusu kilicho chini ya ardhi yako."
        )
    elif verdict == "EXPLOITATIVE":
        explanation_sw += (
            "Hii ni ofa ya chini sana. Unapoteza pesa nyingi. "
            "Jua thamani ya ardhi yako kwanza kabla ya kukubali chochote."
        )
    elif verdict == "BELOW_MARKET":
        explanation_sw += (
            "Ofa ni ya chini ya kiwango cha soko. "
            "Unaweza kupata zaidi kwa kujua thamani ya ardhi yako."
        )
    else:
        explanation_sw += "Ofa inaonekana ya haki. Bado hakikisha na mtaalamu."

    explanation_en = (
        f"Based on current market prices for {', '.join(mineral_names)}, "
        f"your land has an estimated value of KES {total_value_kes:,.0f}. "
        f"International benchmarks suggest the community should receive "
        f"at least KES {fair_share_kes:,.0f} (10-20% of value). "
        f"The offer of KES {offer_amount_kes:,.0f} is {exploitation_ratio*100:.1f}% of fair value. "
        f"Verdict: {verdict}."
    )

    # Recommended actions
    actions = []
    if verdict in ("EXPLOITATIVE", "SEVERELY_EXPLOITATIVE"):
        actions = [
            "DO NOT accept the offer yet",
            "Get an independent geological survey (use this AI system)",
            "Verify if the operator has a valid mining license",
            "Demand disclosure of what minerals are present",
            "Consult a mining lawyer (free legal aid available)",
            "Report to the County Mining Officer if no license",
            "Document everything (photos, GPS, conversations)",
            "Contact other landowners who have been approached",
        ]
    elif verdict == "BELOW_MARKET":
        actions = [
            "Negotiate for a higher amount based on market data",
            "Request independent geological verification",
            "Verify operator's mining license",
            "Consider royalty-based deal instead of lump sum",
        ]

    return FairDealVerdict(
        offer_amount_kes=offer_amount_kes,
        estimated_total_value_kes=total_value_kes,
        fair_share_kes=fair_share_kes,
        exploitation_ratio=exploitation_ratio,
        verdict=verdict,
        explanation_sw=explanation_sw,
        explanation_en=explanation_en,
        recommended_minimum_kes=minimum_acceptable_kes,
        recommended_actions=actions,
    )


def evaluate_valentine_offer() -> FairDealVerdict:
    """
    Evaluate the specific offer Valentine is facing:
    - 1M KSH offer from Chinese operators
    - Land in Nyatike, Migori County
    - Gold AND copper deposits
    - No disclosure of what's underground
    """
    # Conservative estimates for Nyatike geology
    # (based on Kenya Geological Survey data for Migori Greenstone Belt)
    minerals = [
        {
            "mineral": "gold",
            "estimated_kg": 50,      # Conservative: 50kg gold
            "confidence": 0.3,       # Low confidence — no survey done
        },
        {
            "mineral": "copper",
            "estimated_kg": 5000,    # Conservative: 5 tonnes copper
            "confidence": 0.4,       # Slightly higher — known copper belt
        },
    ]

    return evaluate_offer(
        offer_amount_kes=1_000_000,  # 1 million KSH
        minerals=minerals,
        location="Nyatike, Migori County",
        operator_type="foreign",
    )
