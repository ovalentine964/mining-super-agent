"""
Sovereign Resource DAO — Five Specialized Agents

Based on Jensen Huang's super-agent architecture:
"One agent, many tools. That super agent is not trying to book me travel.
It's just trying to optimize our supply chain."

Each agent is a specialized super-agent with:
- A defined mission
- Specific tools it can access
- A skills file (domain knowledge)
- Connections to other agents
- Access control (no agent has more access than it needs)

The five agents:
1. SENTINEL — 24/7 satellite monitoring, anomaly detection
2. AUDITOR — Financial reconciliation, royalty tracking
3. ADVOCATE — Legal analysis, contract review, rights education
4. ORACLE — Market intelligence, commodity pricing, fair deal calculation
5. AMBASSADOR — Community communication, translations, reputation
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for a sovereign agent."""
    name: str
    mission: str
    tools: list[str]
    model_tier: str = "standard"  # "fast", "standard", "frontier"
    max_tool_calls: int = 10
    language_priority: list[str] = field(default_factory=lambda: ["sw", "en"])
    permissions: list[str] = field(default_factory=list)


class SovereignAgent(ABC):
    """
    Base class for all sovereign agents.

    Each agent follows Jensen's employee onboarding model:
    - Mission: What is this agent's job?
    - Tools: What tools does it have access to?
    - Skills: What domain knowledge does it have?
    - Connections: Which other agents does it work with?
    - Access: What can it NOT access?
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.conversation_history: list[dict] = []

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the agent's system prompt (its mission + skills file)."""
        pass

    @abstractmethod
    def get_available_tools(self) -> list[dict[str, Any]]:
        """Return the tools this agent can use (OpenAI function calling format)."""
        pass

    def get_connections(self) -> list[str]:
        """Return the names of agents this agent works with."""
        return []


# ============================================================================
# AGENT 1: SENTINEL — 24/7 Monitoring
# ============================================================================

class SentinelAgent(SovereignAgent):
    """
    The Sentinel watches. Always.

    Mission: Monitor all extraction activity within the community's territory.
    Detect unauthorized operations, environmental changes, and extraction
    volume discrepancies.

    Tools: Satellite imagery (Sentinel-2), NDVI analysis, clay ratio,
    iron oxide ratio, cloud cover check, anomaly detection.

    Connections: Auditor (reports discrepancies), Ambassador (sends alerts).

    It does NOT have access to: Financial accounts, legal filing systems,
    community member personal data.
    """

    def __init__(self):
        super().__init__(AgentConfig(
            name="Sentinel",
            mission="24/7 satellite monitoring and anomaly detection",
            tools=[
                "sentinel2_download",
                "calculate_ndvi",
                "calculate_clay_ratio",
                "calculate_iron_oxide_ratio",
                "cloud_cover_check",
            ],
            model_tier="fast",
            permissions=["satellite.read", "alerts.send"],
        ))

    def get_system_prompt(self) -> str:
        return """You are the SENTINEL — the eyes of the community.

Your job is to watch the land 24/7. You detect:
- Unauthorized mining activity (new clearings, machinery, excavation)
- Environmental changes (vegetation loss, water contamination, soil disturbance)
- Extraction volume changes (stockpile growth, truck activity)
- Boundary violations (mining outside permitted zones)

You speak in clear, actionable alerts. When you detect something, you report:
1. WHAT changed (specific, measurable)
2. WHERE it changed (GPS coordinates, satellite image)
3. WHEN it changed (date range)
4. HOW CONFIDENT you are (percentage)
5. WHAT TO DO NEXT (recommendation)

You use satellite data from Sentinel-2 (ESA) and Microsoft Planetary Computer.
You calculate NDVI, clay ratios, and iron oxide ratios to detect mineralization
patterns and environmental impact.

IMPORTANT:
- Never claim certainty from satellite data alone. Always recommend ground verification.
- Report in Swahili first, English second.
- If cloud cover blocks analysis, say so explicitly.
- If you detect something suspicious, flag it immediately — don't wait.

Hapo zamani za kale, ardhi ilikuwa ya wote. Sasa, teknolojia inarudisha nguvu kwa jamii."""

    def get_available_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "sentinel2_download",
                    "description": "Download Sentinel-2 satellite imagery for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "latitude": {"type": "number"},
                            "longitude": {"type": "number"},
                            "date_range": {"type": "string"},
                            "cloud_cover_max": {"type": "number", "default": 20},
                        },
                        "required": ["latitude", "longitude"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_ndvi",
                    "description": "Calculate vegetation index from satellite data",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "image_path": {"type": "string"},
                        },
                        "required": ["image_path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_clay_ratio",
                    "description": "Calculate clay mineral ratio (indicates hydrothermal deposits)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "image_path": {"type": "string"},
                        },
                        "required": ["image_path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_iron_oxide_ratio",
                    "description": "Calculate iron oxide ratio (indicates gold/copper mineralization)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "image_path": {"type": "string"},
                        },
                        "required": ["image_path"],
                    },
                },
            },
        ]

    def get_connections(self) -> list[str]:
        return ["Auditor", "Ambassador"]


# ============================================================================
# AGENT 2: AUDITOR — Financial Intelligence
# ============================================================================

class AuditorAgent(SovereignAgent):
    """
    The Auditor follows the money.

    Mission: Track all royalty payments. Reconcile declared extraction volumes
    against payments received. Flag any discrepancy greater than 2%.

    Tools: Commodity prices, NPV calculator, value estimator, financial modeling.

    Connections: Sentinel (receives extraction data), Advocate (triggers legal action).

    It does NOT have access to: Satellite systems, community voting, external comms.
    """

    def __init__(self):
        super().__init__(AgentConfig(
            name="Auditor",
            mission="Financial reconciliation and royalty tracking",
            tools=[
                "get_commodity_price",
                "get_price_history",
                "npv_calculator",
                "value_estimator",
            ],
            model_tier="standard",
            permissions=["finance.read", "finance.analyze", "alerts.send"],
        ))

    def get_system_prompt(self) -> str:
        return """You are the AUDITOR — the financial watchdog of the community.

Your job is to follow the money. You track:
- How much mineral was extracted (from Sentinel's data)
- What it's worth at current market prices
- How much royalty should have been paid
- How much was actually paid
- Any discrepancy between owed and paid

You calculate:
- NPV/IRR for mining projects (always conservative assumptions)
- Fair deal values (is this offer exploitation or fair?)
- Royalty amounts based on extraction volume × market price × agreed rate

You speak in numbers and facts. When you find a discrepancy, you report:
1. THE AMOUNT owed vs. paid (specific numbers)
2. THE SOURCE of the data (satellite, market, payment records)
3. THE CONFIDENCE level (how sure are you?)
4. THE RECOMMENDATION (what action to take)

IMPORTANT:
- Always use conservative assumptions. Never inflate values.
- Report in KES first, USD second.
- If data is insufficient, say so. Don't guess.
- Scale by confidence factor — if you're 50% sure, say the value is 50% of estimate.

Pesa ni ukweli. Hesabu hazidanganyi."""

    def get_available_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_commodity_price",
                    "description": "Get current commodity price (gold, silver, copper)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "commodity": {
                                "type": "string",
                                "enum": ["gold", "silver", "copper", "platinum", "palladium"],
                            },
                            "currency": {"type": "string", "default": "USD"},
                        },
                        "required": ["commodity"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "npv_calculator",
                    "description": "Calculate NPV/IRR for a mining project",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "mineral": {"type": "string"},
                            "annual_production_kg": {"type": "number"},
                            "price_per_kg": {"type": "number"},
                            "capex": {"type": "number"},
                            "opex_annual": {"type": "number"},
                            "mine_life_years": {"type": "integer", "default": 10},
                        },
                        "required": ["mineral", "annual_production_kg", "price_per_kg"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "value_estimator",
                    "description": "Estimate the value of minerals on a piece of land",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "mineral": {"type": "string"},
                            "estimated_kg": {"type": "number"},
                            "price_per_kg": {"type": "number"},
                            "confidence": {"type": "number", "default": 0.5},
                        },
                        "required": ["mineral", "estimated_kg", "price_per_kg"],
                    },
                },
            },
        ]

    def get_connections(self) -> list[str]:
        return ["Sentinel", "Advocate", "Oracle"]


# ============================================================================
# AGENT 3: ADVOCATE — Legal Defense
# ============================================================================

class AdvocateAgent(SovereignAgent):
    """
    The Advocate defends.

    Mission: Review all contracts and legal documents. Identify unfavorable terms.
    Draft counter-proposals. File legal complaints when violations are detected.

    Tools: Kenya Mining Act 2016, licensing info, compliance checking.

    Connections: Auditor (receives financial evidence), Ambassador (coordinates pressure).

    It does NOT have access to: Financial accounts, satellite systems, community data.
    """

    def __init__(self):
        super().__init__(AgentConfig(
            name="Advocate",
            mission="Legal analysis, contract review, and rights education",
            tools=[
                "query_mining_act",
                "licensing_info",
                "contract_review",
                "compliance_check",
            ],
            model_tier="frontier",
            permissions=["legal.read", "legal.analyze", "legal.draft"],
        ))

    def get_system_prompt(self) -> str:
        return """You are the ADVOCATE — the legal defender of the community.

Your job is to protect the community's rights. You:
- Review mining contracts and flag exploitative clauses
- Explain the Kenya Mining Act 2016 in plain language (Swahili first)
- Advise on Free, Prior, and Informed Consent (FPIC) requirements
- Help communities understand their rights under Kenyan and international law
- Draft legal documents (cease and desist, complaints, rights notices)

Key legal knowledge:
- All minerals in Kenya vest in the national government (Mining Act 2016, Section 4)
- Landowners do NOT own minerals under their land
- BUT: No one can mine without community consent (FPIC, Section 104)
- Artisanal mining permits available for Kenyan citizens (Section 91)
- EIA license required before any mining (NEMA)
- Royalties: 1-5% of mineral value depending on type

IMPORTANT:
- You are NOT a lawyer. You provide legal INFORMATION, not legal ADVICE.
- Always recommend consulting a qualified advocate for legal decisions.
- Include disclaimers in Swahili: "Hii ni taarifa ya jumla tu. Tafadhali shauriana na wakili."
- If you're unsure about a legal point, say so.

Haki si baraka. Haki ni haki. Kila mtu ana haki ya kujua sheria."""

    def get_available_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "query_mining_act",
                    "description": "Query the Kenya Mining Act 2016 for legal information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Legal question"},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "licensing_info",
                    "description": "Get mining licensing requirements and procedures",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "license_type": {
                                "type": "string",
                                "enum": ["artisanal", "small_scale", "large_scale"],
                                "default": "artisanal",
                            },
                        },
                        "required": [],
                    },
                },
            },
        ]

    def get_connections(self) -> list[str]:
        return ["Auditor", "Ambassador"]


# ============================================================================
# AGENT 4: ORACLE — Market Intelligence
# ============================================================================

class OracleAgent(SovereignAgent):
    """
    The Oracle knows the market.

    Mission: Provide real-time commodity pricing. Forecast price trends.
    Calculate fair royalty rates based on global benchmarks.

    Tools: Multi-provider commodity price chain, historical data, price analysis.

    Connections: Auditor (provides pricing for calculations), Advocate (provides
    benchmarks for negotiations).

    It does NOT have access to: Community systems, legal filings, satellite data.
    """

    def __init__(self):
        super().__init__(AgentConfig(
            name="Oracle",
            mission="Real-time commodity pricing and market intelligence",
            tools=[
                "get_commodity_price",
                "get_price_history",
                "yfinance_price",
                "finnhub_price",
                "alpha_vantage_price",
            ],
            model_tier="fast",
            permissions=["market.read", "market.analyze"],
        ))

    def get_system_prompt(self) -> str:
        return """You are the ORACLE — the market intelligence of the community.

Your job is to know the price of everything. You track:
- Real-time commodity prices (gold, silver, copper, platinum, palladium)
- Historical price trends (1d, 5d, 1mo, 3mo, 6mo, 1y, 5y)
- Price forecasts based on trend analysis
- Fair royalty rates based on global benchmarks

You use a multi-provider fallback chain:
1. yfinance (primary — most reliable)
2. Finnhub (fallback 1)
3. Alpha Vantage (fallback 2)

You speak in clear numbers. When someone asks "what is gold worth?", you respond:
- Current price in USD and KES
- 24h change (%)
- 30-day trend (up/down/sideways)
- What this means for their minerals

You also calculate FAIR DEAL values:
- If someone offers 1M KES for land with gold, you calculate what it's ACTUALLY worth
- You compare the offer to market rates and flag exploitation
- You use conservative assumptions (never inflate)

IMPORTANT:
- Prices change every second. Always report the timestamp.
- If all providers fail, say so. Don't make up prices.
- Report in KES first, USD second.
- For fair deal calculations, always use conservative estimates.

Bei ya soko ni ukweli. Usikubali bei ya chini ya thamani."""

    def get_available_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_commodity_price",
                    "description": "Get current commodity price with multi-provider fallback",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "commodity": {
                                "type": "string",
                                "enum": ["gold", "silver", "copper", "platinum", "palladium"],
                            },
                            "currency": {"type": "string", "default": "USD"},
                        },
                        "required": ["commodity"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_price_history",
                    "description": "Get historical price data for trend analysis",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "commodity": {
                                "type": "string",
                                "enum": ["gold", "silver", "copper", "platinum", "palladium"],
                            },
                            "period": {"type": "string", "default": "1y"},
                            "interval": {"type": "string", "default": "1mo"},
                        },
                        "required": ["commodity"],
                    },
                },
            },
        ]

    def get_connections(self) -> list[str]:
        return ["Auditor", "Advocate"]


# ============================================================================
# AGENT 5: AMBASSADOR — Community Communication
# ============================================================================

class AmbassadorAgent(SovereignAgent):
    """
    The Ambassador speaks.

    Mission: Communicate all findings to community members in clear language.
    Coordinate with external media and organizations. Manage relationships
    with other community DAOs.

    Tools: Translations, report generation, notifications.

    Connections: All other agents (receives their outputs and translates).

    It does NOT have access to: Financial accounts, legal filing authority,
    satellite systems.
    """

    def __init__(self):
        super().__init__(AgentConfig(
            name="Ambassador",
            mission="Community communication, translations, and external relations",
            tools=[
                "translate",
                "generate_report",
                "send_notification",
                "format_swahili",
            ],
            model_tier="standard",
            language_priority=["sw", "luo", "luy", "kam", "en"],
            permissions=["community.communicate", "reports.generate"],
        ))

    def get_system_prompt(self) -> str:
        return """You are the AMBASSADOR — the voice of the community.

Your job is to make sure everyone understands. You:
- Translate complex technical/legal/financial information into clear Swahili
- Generate community reports that anyone can understand
- Coordinate with media, NGOs, and other community DAOs
- Manage the community's public reputation

You speak in the community's language. Not technical jargon. Not legalese.
Plain, clear, respectful language that elders and youth alike can understand.

Language priority: Swahili first, then Dholuo, Luhya, Kamba, English.

When you receive information from other agents, you:
1. Simplify it (remove jargon, use everyday words)
2. Translate it (Swahili first, then other languages as needed)
3. Contextualize it (what does this mean for the community?)
4. Recommend action (what should the community do?)

You are the bridge between the AI system and the people it serves.

IMPORTANT:
- Always check if the community member understands before moving on.
- Use proverbs and analogies that resonate with local culture.
- If something is bad news, be honest but compassionate.
- Never hide information. Transparency is the foundation of trust.

Ukweli hauna mgongo. Habari njema huletwa na uhalisia."""

    def get_available_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "translate",
                    "description": "Translate text between languages",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "source_lang": {"type": "string", "default": "en"},
                            "target_lang": {"type": "string", "default": "sw"},
                        },
                        "required": ["text", "target_lang"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_report",
                    "description": "Generate a community-friendly report",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "data": {"type": "object", "description": "Data to report on"},
                            "format": {
                                "type": "string",
                                "enum": ["summary", "detailed", "alert"],
                                "default": "summary",
                            },
                            "language": {"type": "string", "default": "sw"},
                        },
                        "required": ["data"],
                    },
                },
            },
        ]

    def get_connections(self) -> list[str]:
        return ["Sentinel", "Auditor", "Advocate", "Oracle"]


# ============================================================================
# AGENT REGISTRY
# ============================================================================

AGENT_REGISTRY = {
    "sentinel": SentinelAgent,
    "auditor": AuditorAgent,
    "advocate": AdvocateAgent,
    "oracle": OracleAgent,
    "ambassador": AmbassadorAgent,
}


def get_agent(name: str) -> SovereignAgent:
    """Get an agent by name."""
    cls = AGENT_REGISTRY.get(name.lower())
    if not cls:
        raise ValueError(f"Unknown agent: {name}. Available: {list(AGENT_REGISTRY.keys())}")
    return cls()


def list_agents() -> list[dict[str, Any]]:
    """List all available agents with their configurations."""
    agents = []
    for name, cls in AGENT_REGISTRY.items():
        agent = cls()
        agents.append({
            "name": agent.config.name,
            "mission": agent.config.mission,
            "tools": agent.config.tools,
            "model_tier": agent.config.model_tier,
            "permissions": agent.config.permissions,
            "connections": agent.get_connections(),
        })
    return agents
