"""
Legal Compliance Agent — Kenya Mining Act 2016 and regulatory framework.

Covers:
- Mining Act 2016 (Cap. 306)
- Licensing requirements (prospecting, mining, dealer)
- Environmental Impact Assessment (EIA)
- Community rights and FPIC (Free, Prior, and Informed Consent)
- Compliance checklists
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


class LegalAgent(BaseAgent):
    """Legal compliance agent for Kenya mining regulations."""

    def __init__(self):
        tools = [
            ToolDefinition(
                name="check_license_requirements",
                description="Check licensing requirements for a specific mining activity in Kenya.",
                parameters={
                    "type": "object",
                    "properties": {
                        "activity": {
                            "type": "string",
                            "enum": [
                                "prospecting", "exploration", "mining",
                                "mineral_dealing", "processing", "transportation",
                            ],
                        },
                        "mineral": {"type": "string", "description": "Mineral being mined"},
                        "county": {"type": "string", "description": "County where activity takes place"},
                        "scale": {
                            "type": "string",
                            "enum": ["artisanal", "small_scale", "large_scale"],
                            "default": "artisanal",
                        },
                    },
                    "required": ["activity"],
                },
                permissions=["read:legal"],
            ),
            ToolDefinition(
                name="check_eia_requirements",
                description="Check Environmental Impact Assessment requirements for a mining project.",
                parameters={
                    "type": "object",
                    "properties": {
                        "project_type": {"type": "string", "description": "Type of mining project"},
                        "project_area_ha": {"type": "number", "description": "Project area in hectares"},
                        "environmental_sensitivity": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                            "default": "medium",
                        },
                    },
                    "required": ["project_type"],
                },
                permissions=["read:legal"],
            ),
            ToolDefinition(
                name="check_fpic_requirements",
                description="Check Free, Prior and Informed Consent (FPIC) requirements for community engagement.",
                parameters={
                    "type": "object",
                    "properties": {
                        "community_type": {
                            "type": "string",
                            "enum": ["indigenous", "local", "mixed"],
                        },
                        "project_stage": {
                            "type": "string",
                            "enum": ["exploration", "development", "operation", "closure"],
                        },
                        "land_tenure": {
                            "type": "string",
                            "enum": ["community", "private", "government", "customary"],
                        },
                    },
                    "required": ["community_type", "project_stage"],
                },
                permissions=["read:legal"],
            ),
            ToolDefinition(
                name="generate_compliance_checklist",
                description="Generate a comprehensive compliance checklist for a mining project.",
                parameters={
                    "type": "object",
                    "properties": {
                        "project_type": {"type": "string"},
                        "mineral": {"type": "string"},
                        "scale": {"type": "string", "enum": ["artisanal", "small_scale", "large_scale"]},
                        "county": {"type": "string"},
                    },
                    "required": ["project_type", "mineral"],
                },
                permissions=["read:legal"],
            ),
            ToolDefinition(
                name="query_mining_act",
                description="Query specific sections of the Kenya Mining Act 2016.",
                parameters={
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "Legal topic to query (e.g., 'prospecting rights', 'community consent', 'royalties')",
                        },
                        "section": {"type": "string", "description": "Specific section number (optional)"},
                    },
                    "required": ["topic"],
                },
                permissions=["read:legal"],
            ),
        ]

        super().__init__(
            name="Legal",
            description=(
                "Legal compliance agent specializing in Kenya's Mining Act 2016. "
                "Provides licensing guidance, EIA requirements, FPIC compliance, "
                "and comprehensive compliance checklists."
            ),
            model_id="meta/llama-3.1-405b-instruct",
            permissions={"read:legal", "api:legal_db"},
            tools=tools,
            system_prompt=self._build_system_prompt(),
        )

    def _build_system_prompt(self) -> str:
        return """You are a legal compliance specialist for Kenya's mining sector.

KEY LEGISLATION:
1. Mining Act 2016 (Cap. 306) — primary mining law
2. Environmental Management and Coordination Act (EMCA) 1999
3. Land Act 2012 — land rights and compensation
4. Community Land Act 2016 — community land rights
5. Physical and Land Use Planning Act 2019

MINING ACT 2016 KEY PROVISIONS:

LICENSING (Part III):
- Reconnaissance Permit: 12 months, non-exclusive
- Prospecting License: 3 years (metallic), renewable
- Mining License: 25 years (large scale), renewable
- Artisanal Mining Permit: for individuals, small scale
- Mineral Dealer License: for buying/selling minerals
- Mineral Processing License: for processing plants

ROYALTIES (Section 185):
- Gold: 5% of gross value
- Copper: 5% of gross value
- Coltan: 5% of gross value
- Gemstones: 10% of gross value
- Industrial minerals: 2-5%

COMMUNITY RIGHTS (Part IX):
- Community Development Agreement (CDA) required for large-scale mining
- Local employment and procurement preferences
- Environmental restoration fund
- Compensation for land use

FPIC REQUIREMENTS:
- Free: No coercion or manipulation
- Prior: Consent obtained BEFORE activities begin
- Informed: Full disclosure of project impacts
- Consent: Affirmative agreement (not just absence of objection)

EIA REQUIREMENTS:
- First Schedule activities: Full EIA required
- Second Schedule: Partial EIA
- Must be conducted by NEMA-licensed expert
- Public participation mandatory
- Environmental Audit during operations

IMPORTANT DISCLAIMERS:
- This is legal INFORMATION, not legal ADVICE
- Always consult a qualified Kenyan mining lawyer
- Laws may have been amended — verify current version
- County-specific regulations may apply
"""

    async def run(self, task: str, context: Optional[dict[str, Any]] = None) -> AgentResult:
        """Run legal analysis."""
        result = await super().run(task, context)

        result.disclaimers.extend([
            "This is legal INFORMATION, not legal ADVICE. "
            "Always consult a qualified Kenyan mining lawyer before making legal decisions.",
            "The Kenya Mining Act 2016 may have been amended. "
            "Verify the current version with the Kenya Law Reports.",
            "County-specific regulations and bylaws may apply in addition to national law.",
        ])

        return result


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

async def check_license_requirements(
    activity: str,
    mineral: str = "gold",
    county: str = "Migori",
    scale: str = "artisanal",
) -> dict[str, Any]:
    """Check licensing requirements for a mining activity."""
    licenses = {
        "prospecting": {
            "license_type": "Prospecting License",
            "authority": "Mining Rights Board",
            "duration": "3 years (metallic minerals), renewable",
            "fees": "KES 10,000 - 100,000 depending on area",
            "requirements": [
                "Application to Mining Rights Board",
                "Work program submission",
                "Environmental commitment",
                "Proof of financial capability",
                "Community engagement plan",
            ],
        },
        "mining": {
            "license_type": "Mining License",
            "authority": "Cabinet Secretary, Mining",
            "duration": "25 years (large scale), renewable",
            "fees": "KES 500,000 - 5,000,000 depending on scale",
            "requirements": [
                "Approved EIA report",
                "Mining plan and feasibility study",
                "Community Development Agreement",
                "Environmental restoration bond",
                "Financial capability proof",
                "Mine closure plan",
            ],
        },
        "artisanal": {
            "license_type": "Artisanal Mining Permit",
            "authority": "County Government",
            "duration": "2 years, renewable",
            "fees": "KES 1,000 - 5,000",
            "requirements": [
                "Kenyan citizen",
                "Application to County Mining Committee",
                "Membership in mining cooperative",
                "Basic safety training",
            ],
        },
    }

    license_info = licenses.get(activity, licenses["artisanal"])

    return {
        "activity": activity,
        "mineral": mineral,
        "county": county,
        "scale": scale,
        "license": license_info,
        "additional_notes": [
            f"Royalty rate for {mineral}: 5% of gross value (Mining Act Section 185)",
            "Export permit required for any mineral export",
            "All minerals belong to the Government of Kenya (Section 63)",
        ],
    }


async def check_eia_requirements(
    project_type: str,
    project_area_ha: float = 0,
    environmental_sensitivity: str = "medium",
) -> dict[str, Any]:
    """Check EIA requirements."""
    return {
        "project_type": project_type,
        "area_ha": project_area_ha,
        "sensitivity": environmental_sensitivity,
        "eia_required": True,
        "eia_type": "Full EIA" if project_area_ha > 50 else "Partial EIA",
        "authority": "National Environment Management Authority (NEMA)",
        "requirements": [
            "EIA study by NEMA-licensed expert",
            "Scoping report",
            "Baseline environmental study",
            "Impact assessment",
            "Mitigation measures",
            "Environmental management plan",
            "Public participation (minimum 2 public meetings)",
            "Submit to NEMA for review and license",
        ],
        "timeline": "3-6 months typical",
        "cost_estimate": "KES 500,000 - 5,000,000 depending on project size",
        "public_participation": {
            "required": True,
            "minimum_meetings": 2,
            "stakeholders": ["Local community", "County government", "NGOs", "Other interested parties"],
            "notice_period": "21 days minimum before meeting",
        },
    }


async def check_fpic_requirements(
    community_type: str,
    project_stage: str,
    land_tenure: str = "community",
) -> dict[str, Any]:
    """Check FPIC requirements."""
    return {
        "community_type": community_type,
        "project_stage": project_stage,
        "land_tenure": land_tenure,
        "fpic_required": True,
        "requirements": {
            "free": {
                "description": "Consent must be given freely, without coercion, intimidation, or manipulation",
                "practical_steps": [
                    "Independent community advisors",
                    "Adequate time for decision-making",
                    "No threats or inducements",
                ],
            },
            "prior": {
                "description": "Consent must be obtained BEFORE any activities begin",
                "practical_steps": [
                    "Engage community at earliest planning stage",
                    "No exploration or development before consent",
                    "Allow sufficient consultation period",
                ],
            },
            "informed": {
                "description": "Community must receive full, accurate information about the project",
                "practical_steps": [
                    "Project description in local language",
                    "Environmental and social impact information",
                    "Economic benefits and risks",
                    "Duration and extent of activities",
                    "Right to refuse",
                ],
            },
            "consent": {
                "description": "Affirmative agreement, not just absence of objection",
                "practical_steps": [
                    "Document community decision-making process",
                    "Record consent through recognized community structures",
                    "Written Community Development Agreement",
                    "Ongoing consultation mechanism",
                ],
            },
        },
        "community_development_agreement": {
            "required": True,
            "key_elements": [
                "Employment commitments",
                "Procurement preferences for local suppliers",
                "Community development projects",
                "Environmental protection measures",
                "Dispute resolution mechanism",
                "Benefit sharing formula",
            ],
        },
    }


async def generate_compliance_checklist(
    project_type: str,
    mineral: str,
    scale: str = "artisanal",
    county: str = "Migori",
) -> dict[str, Any]:
    """Generate a comprehensive compliance checklist."""
    return {
        "project_type": project_type,
        "mineral": mineral,
        "scale": scale,
        "county": county,
        "checklist": {
            "legal_and_licensing": [
                {"item": "Obtain Prospecting/Mining License", "status": "pending", "priority": "critical"},
                {"item": "Register with County Mining Committee", "status": "pending", "priority": "critical"},
                {"item": "Obtain Mineral Dealer License (if dealing)", "status": "pending", "priority": "high"},
                {"item": "Apply for export permit (if exporting)", "status": "pending", "priority": "medium"},
            ],
            "environmental": [
                {"item": "Conduct EIA study", "status": "pending", "priority": "critical"},
                {"item": "Obtain NEMA EIA license", "status": "pending", "priority": "critical"},
                {"item": "Develop Environmental Management Plan", "status": "pending", "priority": "high"},
                {"item": "Establish environmental restoration fund", "status": "pending", "priority": "high"},
                {"item": "Conduct public participation meetings", "status": "pending", "priority": "critical"},
            ],
            "community": [
                {"item": "Engage community leaders", "status": "pending", "priority": "critical"},
                {"item": "Conduct FPIC process", "status": "pending", "priority": "critical"},
                {"item": "Negotiate Community Development Agreement", "status": "pending", "priority": "high"},
                {"item": "Establish grievance mechanism", "status": "pending", "priority": "medium"},
            ],
            "financial": [
                {"item": "Pay annual license fees", "status": "pending", "priority": "high"},
                {"item": "Set up royalty payment mechanism (5%)", "status": "pending", "priority": "high"},
                {"item": "Obtain insurance", "status": "pending", "priority": "medium"},
            ],
            "safety": [
                {"item": "Develop mine safety plan", "status": "pending", "priority": "high"},
                {"item": "Provide worker safety training", "status": "pending", "priority": "high"},
                {"item": "Install safety equipment", "status": "pending", "priority": "high"},
            ],
        },
        "estimated_timeline": "6-12 months for full compliance",
        "estimated_cost": "KES 1,000,000 - 10,000,000 depending on scale",
    }


async def query_mining_act(topic: str, section: str = None) -> dict[str, Any]:
    """Query the Kenya Mining Act 2016."""
    # Knowledge base of key provisions
    provisions = {
        "prospecting rights": {
            "sections": ["Part III, Sections 20-35"],
            "summary": "Prospecting licenses are granted by the Mining Rights Board. "
                       "Duration is 3 years for metallic minerals. Requires work program "
                       "and environmental commitment.",
        },
        "royalties": {
            "sections": ["Section 185"],
            "summary": "Royalty rates: 5% for most minerals, 10% for gemstones. "
                       "Payable quarterly to the Commissioner of Mining.",
        },
        "community consent": {
            "sections": ["Part IX, Sections 110-120"],
            "summary": "Community Development Agreement required for large-scale mining. "
                       "Must include employment, procurement, and development commitments.",
        },
        "environmental protection": {
            "sections": ["Part X, Sections 130-145"],
            "summary": "EIA required before mining license. Environmental restoration fund "
                       "mandatory. Mine closure plan required.",
        },
    }

    topic_lower = topic.lower()
    matched = None
    for key, value in provisions.items():
        if key in topic_lower or any(word in topic_lower for word in key.split()):
            matched = value
            break

    if not matched:
        matched = {
            "sections": ["Refer to full Mining Act 2016"],
            "summary": f"Topic '{topic}' — consult the full Mining Act 2016 or a qualified lawyer.",
        }

    return {
        "topic": topic,
        "section": section,
        "provisions": matched,
        "reference": "Mining Act 2016 (Cap. 306), Laws of Kenya",
        "disclaimer": "This is a summary. Always refer to the full text of the Act.",
    }
