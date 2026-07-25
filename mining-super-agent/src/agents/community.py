"""
Community Relations Agent — Stakeholder analysis, FPIC, community engagement.

Covers:
- Stakeholder mapping and analysis
- FPIC (Free, Prior, and Informed Consent) guidance
- Community Development Agreement (CDA) support
- Cultural sensitivity for Luo community in Migori
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .base import AgentResult, BaseAgent, ToolDefinition

logger = logging.getLogger(__name__)


class CommunityAgent(BaseAgent):
    """Community relations agent for stakeholder engagement."""

    def __init__(self):
        tools = [
            ToolDefinition(
                name="stakeholder_analysis",
                description="Analyze stakeholders for a mining project — identify key groups, their interests, and influence.",
                parameters={
                    "type": "object",
                    "properties": {
                        "project_location": {"type": "string", "description": "Location of the project"},
                        "project_type": {"type": "string", "description": "Type of mining activity"},
                        "land_tenure": {
                            "type": "string",
                            "enum": ["community", "private", "government", "customary"],
                        },
                    },
                    "required": ["project_location"],
                },
                permissions=["read:community"],
            ),
            ToolDefinition(
                name="fpic_guidance",
                description="Provide step-by-step FPIC (Free, Prior, Informed Consent) guidance.",
                parameters={
                    "type": "object",
                    "properties": {
                        "stage": {
                            "type": "string",
                            "enum": ["planning", "initial_engagement", "consultation", "agreement", "monitoring"],
                        },
                        "community_type": {"type": "string", "enum": ["indigenous", "local", "mixed"]},
                    },
                    "required": ["stage"],
                },
                permissions=["read:community"],
            ),
            ToolDefinition(
                name="draft_cda_outline",
                description="Generate an outline for a Community Development Agreement.",
                parameters={
                    "type": "object",
                    "properties": {
                        "community_name": {"type": "string"},
                        "project_type": {"type": "string"},
                        "mineral": {"type": "string"},
                        "project_life_years": {"type": "integer", "default": 10},
                    },
                    "required": ["community_name", "project_type"],
                },
                permissions=["read:community"],
            ),
            ToolDefinition(
                name="cultural_guidance",
                description="Provide cultural sensitivity guidance for engaging with a specific community.",
                parameters={
                    "type": "object",
                    "properties": {
                        "community": {"type": "string", "description": "Community name or ethnic group"},
                        "context": {"type": "string", "description": "Engagement context"},
                    },
                    "required": ["community"],
                },
                permissions=["read:community"],
            ),
        ]

        super().__init__(
            name="Community",
            description=(
                "Community relations agent specializing in stakeholder engagement, "
                "FPIC compliance, and cultural sensitivity for mining projects in Kenya."
            ),
            model_id="meta/llama-3.1-8b-instruct",
            permissions={"read:community"},
            tools=tools,
            system_prompt=self._build_system_prompt(),
        )

    def _build_system_prompt(self) -> str:
        return """You are a community relations specialist for mining projects in Kenya.

YOUR EXPERTISE:
1. Stakeholder mapping and analysis
2. FPIC (Free, Prior, and Informed Consent) process
3. Community Development Agreement (CDA) negotiation
4. Cultural sensitivity, especially for Luo communities in Migori County

CULTURAL CONTEXT — LUO COMMUNITY IN MIGORI:
- Land is communally managed by families and clans
- Elders (Jadwong') play a key role in decision-making
- Community meetings follow specific protocols
- Land disputes are sensitive — involve clan elders
- Women's groups are important stakeholders
- Youth groups need separate engagement
- Respect for ancestral land is paramount

ENGAGEMENT PRINCIPLES:
1. Respect local customs and decision-making structures
2. Engage ALL stakeholders — not just leaders
3. Use local language (Dholuo, Swahili)
4. Be transparent about project impacts
5. Allow adequate time for community deliberation
6. Document everything in writing
7. Ensure benefits are tangible and local

FPIC PROCESS:
1. Identify legitimate community representatives
2. Provide complete project information in local language
3. Allow community to deliberate without pressure
4. Document consent through community's own process
5. Establish ongoing consultation mechanism
6. Monitor and enforce agreements
"""

    async def run(self, task: str, context: Optional[dict[str, Any]] = None) -> AgentResult:
        """Run community analysis."""
        result = await super().run(task, context)
        result.disclaimers.extend([
            "Community engagement must be conducted in person with qualified facilitators. "
            "This guidance supports but does not replace direct community engagement.",
            "FPIC is an ongoing process, not a one-time event. "
            "Continuous engagement is required throughout the project lifecycle.",
        ])
        return result


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

async def stakeholder_analysis(
    project_location: str,
    project_type: str = "mining",
    land_tenure: str = "community",
) -> dict[str, Any]:
    """Analyze stakeholders for a mining project."""
    return {
        "location": project_location,
        "stakeholder_groups": [
            {
                "group": "Local Community (Residents)",
                "interests": ["Land rights", "Employment", "Compensation", "Environmental protection"],
                "influence": "HIGH",
                "engagement_priority": "CRITICAL",
                "key_concerns": "Displacement, loss of farmland, water contamination",
            },
            {
                "group": "Community Elders (Jadwong')",
                "interests": ["Cultural preservation", "Community welfare", "Traditional authority"],
                "influence": "HIGH",
                "engagement_priority": "CRITICAL",
                "key_concerns": "Respect for customs, community benefits, land rights",
            },
            {
                "group": "Women's Groups",
                "interests": ["Employment", "Water access", "Children's welfare", "Market access"],
                "influence": "MEDIUM",
                "engagement_priority": "HIGH",
                "key_concerns": "Water contamination, loss of farming land, safety",
            },
            {
                "group": "Youth Groups",
                "interests": ["Employment", "Skills training", "Economic opportunity"],
                "influence": "MEDIUM",
                "engagement_priority": "HIGH",
                "key_concerns": "Jobs, training, future opportunities",
            },
            {
                "group": "County Government",
                "interests": ["Revenue", "Development", "Compliance", "Employment"],
                "influence": "HIGH",
                "engagement_priority": "CRITICAL",
                "key_concerns": "Regulatory compliance, local content, revenue",
            },
            {
                "group": "National Government (Mining Ministry)",
                "interests": ["Compliance", "Revenue", "National development"],
                "influence": "HIGH",
                "engagement_priority": "HIGH",
                "key_concerns": "License compliance, royalties, environmental standards",
            },
            {
                "group": "Environmental NGOs",
                "interests": ["Environmental protection", "Community rights", "Transparency"],
                "influence": "MEDIUM",
                "engagement_priority": "MEDIUM",
                "key_concerns": "Environmental impact, community consent, water quality",
            },
        ],
        "engagement_strategy": "Start with elders and community leaders, then broaden to all groups. "
                               "Use community meetings (baraza) as primary engagement format.",
    }


async def fpic_guidance(
    stage: str,
    community_type: str = "local",
) -> dict[str, Any]:
    """Provide FPIC guidance for a specific stage."""
    guidance = {
        "planning": {
            "stage": "Planning",
            "actions": [
                "Identify all affected communities",
                "Map community decision-making structures",
                "Identify legitimate community representatives",
                "Prepare information materials in local language",
                "Budget for FPIC process (time and resources)",
                "Hire local facilitators",
            ],
            "timeline": "1-2 months",
            "key_principle": "Preparation is everything. Don't rush into engagement.",
        },
        "initial_engagement": {
            "stage": "Initial Engagement",
            "actions": [
                "Introduce project to community leaders",
                "Explain FPIC process and community rights",
                "Answer initial questions and concerns",
                "Agree on consultation process and timeline",
                "Establish community liaison team",
            ],
            "timeline": "1-2 months",
            "key_principle": "Build trust before discussing project details.",
        },
        "consultation": {
            "stage": "Consultation",
            "actions": [
                "Hold community meetings (baraza) — minimum 3",
                "Provide complete project information",
                "Document all concerns and questions",
                "Conduct separate sessions for women and youth",
                "Allow adequate time for community deliberation",
                "Address concerns transparently",
            ],
            "timeline": "3-6 months",
            "key_principle": "Consultation means listening, not persuading.",
        },
        "agreement": {
            "stage": "Agreement",
            "actions": [
                "Negotiate Community Development Agreement",
                "Document benefit-sharing arrangements",
                "Establish grievance mechanism",
                "Sign agreement with community representatives",
                "Register agreement with relevant authorities",
            ],
            "timeline": "2-3 months",
            "key_principle": "Written agreement protects both parties.",
        },
        "monitoring": {
            "stage": "Monitoring",
            "actions": [
                "Establish joint monitoring committee",
                "Regular community meetings (quarterly minimum)",
                "Track compliance with CDA commitments",
                "Address grievances promptly",
                "Annual community satisfaction survey",
            ],
            "timeline": "Ongoing",
            "key_principle": "FPIC doesn't end with agreement — it's ongoing.",
        },
    }

    return guidance.get(stage, {
        "error": f"Unknown stage: {stage}",
        "available_stages": list(guidance.keys()),
    })


async def draft_cda_outline(
    community_name: str,
    project_type: str,
    mineral: str = "gold",
    project_life_years: int = 10,
) -> dict[str, Any]:
    """Generate a CDA outline."""
    return {
        "title": f"Community Development Agreement — {community_name}",
        "parties": [
            f"Community of {community_name}",
            "[Mining Company Name]",
        ],
        "duration": f"{project_life_years} years",
        "sections": [
            {
                "section": "1. Preamble",
                "content": "Background, purpose, and recognition of community rights",
            },
            {
                "section": "2. Employment and Training",
                "content": [
                    "Priority employment for community members",
                    "Skills training programs",
                    "Apprenticeship opportunities",
                    "Target: 60% local employment for unskilled, 30% for skilled",
                ],
            },
            {
                "section": "3. Local Procurement",
                "content": [
                    "First preference for local suppliers and contractors",
                    "Support for local business development",
                    "Target: 30% of procurement from local businesses",
                ],
            },
            {
                "section": "4. Community Development Projects",
                "content": [
                    "Annual community development fund (X% of revenue)",
                    "Priority areas: education, health, water, infrastructure",
                    "Community input on project selection",
                    "Transparency in fund management",
                ],
            },
            {
                "section": "5. Environmental Protection",
                "content": [
                    "Water quality monitoring",
                    "Air quality monitoring",
                    "Rehabilitation commitments",
                    "Environmental restoration fund",
                ],
            },
            {
                "section": "6. Grievance Mechanism",
                "content": [
                    "Accessible grievance process",
                    "Response timeframes",
                    "Escalation procedure",
                    "Independent mediation option",
                ],
            },
            {
                "section": "7. Dispute Resolution",
                "content": [
                    "Negotiation as first step",
                    "Mediation by independent party",
                    "Arbitration as last resort",
                    "Governing law: Laws of Kenya",
                ],
            },
            {
                "section": "8. Review and Amendment",
                "content": [
                    "Annual review of agreement",
                    "Amendment by mutual consent",
                    "Community consultation required for changes",
                ],
            },
        ],
    }


async def cultural_guidance(
    community: str,
    context: str = "mining engagement",
) -> dict[str, Any]:
    """Provide cultural guidance for community engagement."""
    # Luo-specific guidance
    luo_guidance = {
        "community": community,
        "language": "Dholuo (primary), Swahili (secondary), English (formal documents)",
        "greeting_customs": [
            "Greet elders first — use 'Oyawore' (good morning/day)",
            "Handshake is common — gentle, not firm",
            "Address elders by title (Jaduong', Nyar) not first name",
        ],
        "meeting_protocol": [
            "Community meetings (baraza) are led by the chief or elder",
            "Speakers follow a hierarchy — elders first",
            "Women may speak separately or in women's baraza",
            "Allow time for deliberation — decisions are not rushed",
            "Sitting arrangement matters — elders at the front",
        ],
        "sensitive_topics": [
            "Land is deeply tied to identity and ancestors",
            "Avoid direct confrontation — use indirect communication",
            "Death and burial sites are sacred",
            "Water sources have cultural significance",
        ],
        "dos": [
            "Show respect to elders at all times",
            "Learn basic Dholuo greetings",
            "Bring small gifts for initial meetings (not bribes)",
            "Listen more than you speak",
            "Document agreements in writing",
        ],
        "donts": [
            "Don't rush decisions — community needs time",
            "Don't bypass elders to talk to youth directly",
            "Don't make promises you can't keep",
            "Don't use technical jargon — use simple language",
            "Don't hold meetings during planting/harvest season",
        ],
    }

    return luo_guidance
