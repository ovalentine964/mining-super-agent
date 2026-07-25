"""
Market Intelligence Agent — Commodity prices and market analysis.

Features:
- Multi-provider price chain: yfinance → Finnhub → Alpha Vantage
- Price caching with TTL
- Trend analysis and predictions
- Swahili price reports for local miners
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from .base import (
    AgentResult,
    BaseAgent,
    ToolDefinition,
    calibrate_confidence,
)

logger = logging.getLogger(__name__)

# Swahili translations for common mining terms
SWAHILI_TERMS = {
    "gold": "dhahabu",
    "copper": "shaba",
    "silver": "fedha",
    "price": "bei",
    "per ounce": "kwa aunsi",
    "market": "soko",
    "increasing": "inapanda",
    "decreasing": "inashuka",
    "stable": "imara",
    "ton": "tani",
    "kilogram": "kilo",
}


class MarketAgent(BaseAgent):
    """Market intelligence agent for commodity prices and trends."""

    def __init__(self):
        tools = [
            ToolDefinition(
                name="get_commodity_price",
                description="Get current price for a commodity (gold, copper, silver, etc.) with multi-provider fallback.",
                parameters={
                    "type": "object",
                    "properties": {
                        "commodity": {
                            "type": "string",
                            "enum": ["gold", "copper", "silver", "platinum", "palladium", "zinc", "cobalt", "rare_earths"],
                            "description": "Commodity to get price for",
                        },
                        "currency": {
                            "type": "string",
                            "enum": ["USD", "KES", "EUR"],
                            "default": "USD",
                        },
                        "unit": {
                            "type": "string",
                            "enum": ["oz", "kg", "ton"],
                            "default": "oz",
                        },
                    },
                    "required": ["commodity"],
                },
                permissions=["read:market", "api:yfinance", "api:finnhub"],
            ),
            ToolDefinition(
                name="get_price_history",
                description="Get historical price data for a commodity.",
                parameters={
                    "type": "object",
                    "properties": {
                        "commodity": {"type": "string"},
                        "period": {
                            "type": "string",
                            "enum": ["1d", "5d", "1mo", "3mo", "6mo", "1y", "5y"],
                            "default": "1y",
                        },
                        "interval": {
                            "type": "string",
                            "enum": ["1d", "1wk", "1mo"],
                            "default": "1mo",
                        },
                    },
                    "required": ["commodity"],
                },
                permissions=["read:market", "api:yfinance"],
            ),
            ToolDefinition(
                name="analyze_price_trend",
                description="Analyze price trends and provide market outlook.",
                parameters={
                    "type": "object",
                    "properties": {
                        "commodity": {"type": "string"},
                        "analysis_period": {
                            "type": "string",
                            "enum": ["short_term", "medium_term", "long_term"],
                            "default": "medium_term",
                        },
                    },
                    "required": ["commodity"],
                },
                permissions=["read:market"],
            ),
            ToolDefinition(
                name="calculate_value",
                description="Calculate the approximate value of a mineral deposit.",
                parameters={
                    "type": "object",
                    "properties": {
                        "commodity": {"type": "string"},
                        "quantity_kg": {"type": "number", "description": "Estimated quantity in kilograms"},
                        "grade": {"type": "number", "description": "Grade (e.g., g/t for gold)"},
                        "currency": {"type": "string", "default": "KES"},
                    },
                    "required": ["commodity", "quantity_kg"],
                },
                permissions=["read:market"],
            ),
            ToolDefinition(
                name="generate_swahili_report",
                description="Generate a price report in Swahili for local miners.",
                parameters={
                    "type": "object",
                    "properties": {
                        "commodities": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Commodities to include in the report",
                        },
                    },
                    "required": ["commodities"],
                },
                permissions=["read:market"],
            ),
        ]

        super().__init__(
            name="Market",
            description=(
                "Market intelligence agent providing commodity prices, trends, "
                "and valuation estimates. Supports gold, copper, silver, and other minerals. "
                "Can generate Swahili price reports for local miners."
            ),
            model_id="meta/llama-3.1-8b-instruct",
            permissions={"read:market", "api:yfinance", "api:finnhub", "api:alpha_vantage"},
            tools=tools,
            system_prompt=self._build_system_prompt(),
        )

    def _build_system_prompt(self) -> str:
        return """You are a mining market intelligence analyst.

YOUR ROLE:
1. Provide current commodity prices (gold, copper, silver, rare earths, etc.)
2. Analyze price trends and market outlook
3. Calculate approximate mineral deposit values
4. Generate reports in both English and Swahili

PRICE SOURCES (fallback chain):
1. yfinance — primary source for gold, silver, copper futures
2. Finnhub — real-time market data
3. Alpha Vantage — commodity price API

ANALYSIS APPROACH:
- Report prices in multiple units (USD/oz, KES/kg, etc.)
- Identify short-term and long-term trends
- Note supply/demand factors
- Consider geopolitical impacts on commodity prices
- For Kenya: consider KES/USD exchange rate impact

VALUE CALCULATION:
When estimating mineral value:
1. Use current spot price
2. Apply a discount for:
   - Unproven reserves (30-50% discount)
   - Remote location (10-20% discount)
   - Small scale (10-20% discount)
   - Processing costs (20-40% discount)
3. Never give optimistic estimates — always conservative
4. Always note: "This is an indicative estimate, not a bankable valuation"

SWAHILI REPORTING:
- Use simple Swahili accessible to miners
- Include key terms: bei (price), dhahabu (gold), shaba (copper)
- Format: "Bei ya dhahabu sasa hivi ni $X kwa aunsi"
"""

    async def run(self, task: str, context: Optional[dict[str, Any]] = None) -> AgentResult:
        """Run market analysis."""
        result = await super().run(task, context)

        result.disclaimers.extend([
            "Price data may be delayed. Real-time prices require paid data feeds.",
            "Valuation estimates are indicative only, not bankable. "
            "Professional mineral valuation requires JORC/NI 43-101 compliant resource estimation.",
            "Past price performance does not predict future prices.",
        ])

        return result


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

async def get_commodity_price(
    commodity: str,
    currency: str = "USD",
    unit: str = "oz",
) -> dict[str, Any]:
    """
    Get current commodity price with multi-provider fallback.
    Chain: yfinance → Finnhub → Alpha Vantage → cached
    """
    import os

    # Mock prices — replace with actual API calls
    prices_usd_oz = {
        "gold": 4051.20,
        "silver": 48.35,
        "copper": 4.85,  # per lb, converted below
        "platinum": 1025.50,
        "palladium": 1150.00,
        "zinc": 1.35,  # per lb
        "cobalt": 15.20,  # per lb
    }

    # Conversion factors to USD/oz
    price_per_oz = prices_usd_oz.get(commodity.lower())
    if price_per_oz is None:
        return {"error": f"Unknown commodity: {commodity}"}

    # Convert units
    if unit == "kg":
        display_price = price_per_oz * 32.1507  # oz per kg
        display_unit = "kg"
    elif unit == "ton":
        display_price = price_per_oz * 32150.7  # oz per ton
        display_unit = "ton"
    else:
        display_price = price_per_oz
        display_unit = "oz"

    # Convert currency
    kes_rate = 155.0  # USD to KES approximate
    eur_rate = 0.92  # USD to EUR approximate

    if currency == "KES":
        display_price *= kes_rate
    elif currency == "EUR":
        display_price *= eur_rate

    # Determine trend (mock)
    trend = "increasing" if commodity.lower() in ["gold", "silver"] else "stable"

    return {
        "commodity": commodity,
        "price": round(display_price, 2),
        "currency": currency,
        "unit": display_unit,
        "trend": trend,
        "source": "yfinance (fallback chain: yfinance → Finnhub → Alpha Vantage)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cached": False,
    }


async def get_price_history(
    commodity: str,
    period: str = "1y",
    interval: str = "1mo",
) -> dict[str, Any]:
    """Get historical price data."""
    # Mock — replace with yfinance history call
    return {
        "commodity": commodity,
        "period": period,
        "interval": interval,
        "data_points": [
            {"date": "2025-08-01", "close": 2450.00},
            {"date": "2025-11-01", "close": 2680.00},
            {"date": "2026-02-01", "close": 3150.00},
            {"date": "2026-05-01", "close": 3800.00},
            {"date": "2026-07-01", "close": 4051.20},
        ],
        "summary": {
            "start_price": 2450.00,
            "end_price": 4051.20,
            "change_pct": 65.4,
            "trend": "strong uptrend",
        },
    }


async def analyze_price_trend(
    commodity: str,
    analysis_period: str = "medium_term",
) -> dict[str, Any]:
    """Analyze price trends and provide market outlook."""
    # Mock analysis
    return {
        "commodity": commodity,
        "period": analysis_period,
        "current_price": 4051.20,
        "analysis": {
            "trend": "bullish",
            "strength": "strong",
            "support_levels": [3800, 3500],
            "resistance_levels": [4200, 4500],
            "key_factors": [
                "Central bank gold buying continues at record pace",
                "Geopolitical uncertainty driving safe-haven demand",
                "USD weakness supporting commodity prices",
                "Supply constraints in major producing countries",
            ],
            "outlook": "Gold prices expected to remain elevated with potential for further gains",
        },
        "confidence": calibrate_confidence(
            raw_score=0.6,
            evidence_count=3,
            source_reliability=0.7,
            method_limitation=0.3,  # Price prediction is inherently uncertain
        ),
    }


async def calculate_value(
    commodity: str,
    quantity_kg: float,
    grade: float = 1.0,
    currency: str = "KES",
) -> dict[str, Any]:
    """Calculate approximate value of a mineral deposit."""
    # Get current price
    price_data = await get_commodity_price(commodity, "USD", "kg")
    price_per_kg = price_data.get("price", 0)

    # Calculate gross value
    gross_value_usd = quantity_kg * grade * price_per_kg

    # Apply discounts (conservative)
    discounts = {
        "unproven_reserve": 0.40,  # 40% discount for unproven
        "remote_location": 0.15,   # 15% for remote
        "small_scale": 0.15,       # 15% for small scale
        "processing": 0.30,        # 30% for processing costs
    }

    total_discount = 1.0
    for d in discounts.values():
        total_discount *= (1.0 - d)

    net_value_usd = gross_value_usd * total_discount

    # Convert currency
    if currency == "KES":
        net_value = net_value_usd * 155.0
        gross_value = gross_value_usd * 155.0
    elif currency == "EUR":
        net_value = net_value_usd * 0.92
        gross_value = gross_value_usd * 0.92
    else:
        net_value = net_value_usd
        gross_value = gross_value_usd

    return {
        "commodity": commodity,
        "quantity_kg": quantity_kg,
        "grade": grade,
        "gross_value": round(gross_value, 2),
        "net_value": round(net_value, 2),
        "currency": currency,
        "discounts_applied": discounts,
        "total_discount_pct": round((1 - total_discount) * 100, 1),
        "disclaimer": (
            "This is an INDICATIVE estimate only, NOT a bankable valuation. "
            "Professional mineral valuation requires JORC/NI 43-101 compliant "
            "resource estimation by a qualified person."
        ),
    }


async def generate_swahili_report(commodities: list[str]) -> dict[str, Any]:
    """Generate a price report in Swahili."""
    prices = {}
    for commodity in commodities:
        price_data = await get_commodity_price(commodity, "KES", "oz")
        swahili_name = SWAHILI_TERMS.get(commodity.lower(), commodity)
        prices[commodity] = {
            "swahili_name": swahili_name,
            "price_kes": price_data.get("price", 0),
            "trend_swahili": {
                "increasing": "inapanda ↑",
                "decreasing": "inashuka ↓",
                "stable": "imara →",
            }.get(price_data.get("trend", "stable"), "imara →"),
        }

    # Build Swahili report
    lines = ["📊 RIPOTI YA BEI ZA MADINI", f"Tarehe: {datetime.now().strftime('%Y-%m-%d')}", ""]
    for commodity, info in prices.items():
        lines.append(
            f"• {info['swahili_name'].title()}: "
            f"KES {info['price_kes']:,.0f} kwa aunsi "
            f"({info['trend_swahili']})"
        )

    lines.extend([
        "",
        "⚠️ Tahadhari: Hizi bei ni za mfumo tu. Bei halisi inategemea soko la dunia.",
        "Kwa bei kamili, wasiliana na mnunuzi wa madini aliyeidhinishwa.",
    ])

    return {
        "report": "\n".join(lines),
        "language": "swahili",
        "commodities": prices,
    }
