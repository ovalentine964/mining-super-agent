"""
Legal Tools — Kenya Mining Act 2016 and Licensing Information
=============================================================

Tools that the superagent uses for legal queries.
NOT a separate agent — the superagent calls these tools directly.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Kenya Mining Act 2016 key provisions
MINING_ACT_SUMMARY = {
    "title": "Mining Act, 2016",
    "act_number": "No. 12 of 2016",
    "commencement": "2016-05-27",
    "key_provisions": {
        "mineral_rights": {
            "section": "Part IV",
            "summary": "All minerals vest in the national government. Landowners do not own minerals under their land.",
            "key_point": "You need a license to mine, even on your own land.",
        },
        "artisanal_mining": {
            "section": "Section 91",
            "summary": "Artisanal mining permits available for Kenyan citizens mining on their own land.",
            "key_point": "You can get a permit to mine your own land without a full mining license.",
        },
        "community_consent": {
            "section": "Section 104",
            "summary": "Free, Prior, and Informed Consent (FPIC) required from affected communities.",
            "key_point": "No one can mine on your land without your consent.",
        },
        "environmental_impact": {
            "section": "Part V",
            "summary": "Environmental Impact Assessment (EIA) required before mining.",
            "key_point": "Any mining operation needs an EIA license from NEMA.",
        },
        "royalties": {
            "section": "Section 182",
            "summary": "Royalties payable to the national government on mineral sales.",
            "key_point": "Royalty rates: 1-5% of mineral value depending on type.",
        },
        "export": {
            "section": "Section 186",
            "summary": "Mineral export requires a license from the Cabinet Secretary.",
            "key_point": "You cannot export minerals without a license.",
        },
    },
    "disclaimer": "Hii ni taarifa ya jumla tu. Tafadhali shauriana na wakili kwa ushauri wa kisheria.",
}


async def query_mining_act(query: str) -> dict[str, Any]:
    """
    Query the Kenya Mining Act 2016 for legal information.
    
    Returns relevant sections based on the query.
    """
    # Simple keyword matching (RAG will improve this)
    query_lower = query.lower()
    
    relevant_sections = []
    
    for section_name, section_data in MINING_ACT_SUMMARY["key_provisions"].items():
        # Check if query matches section
        if any(keyword in query_lower for keyword in section_name.split("_")):
            relevant_sections.append({
                "section": section_name,
                "reference": section_data["section"],
                "summary": section_data["summary"],
                "key_point": section_data["key_point"],
            })
    
    if not relevant_sections:
        # Return general info
        relevant_sections = [
            MINING_ACT_SUMMARY["key_provisions"]["mineral_rights"],
            MINING_ACT_SUMMARY["key_provisions"]["artisanal_mining"],
        ]
    
    return {
        "act": MINING_ACT_SUMMARY["title"],
        "relevant_sections": relevant_sections,
        "disclaimer": MINING_ACT_SUMMARY["disclaimer"],
        "swahili_summary": _format_legal_swahili(relevant_sections),
    }


async def get_licensing_info(license_type: str = "artisanal") -> dict[str, Any]:
    """
    Get licensing requirements and procedures.
    """
    licenses = {
        "artisanal": {
            "name": "Artisanal Mining Permit",
            "swahili": "Kibali cha Uchimbaji wa Mikono",
            "eligibility": "Kenyan citizen, 18+, mining on own land or with community consent",
            "cost": "KES 1,000 - 5,000",
            "duration": "1 year, renewable",
            "requirements": [
                "National ID or passport",
                "Proof of land ownership or community consent",
                "Mining plan (basic)",
                "Environmental commitment",
            ],
            "process": [
                "1. Apply to County Mining Officer",
                "2. Site inspection",
                "3. Approval and payment",
                "4. Permit issued",
            ],
            "timeline": "2-4 weeks",
        },
        "small_scale": {
            "name": "Small Scale Mining License",
            "swahili": "Leseni ya Uchimbaji wa Ndogo",
            "eligibility": "Kenyan citizen or company, mining area up to 10 hectares",
            "cost": "KES 50,000 - 200,000",
            "duration": "3 years, renewable",
            "requirements": [
                "Company registration",
                "Mining plan",
                "EIA license from NEMA",
                "Community consent (FPIC)",
                "Financial capability proof",
            ],
            "process": [
                "1. Pre-consultation with Mining Officer",
                "2. Submit application to Mining Cadastre",
                "3. EIA process",
                "4. Community consultation",
                "5. Technical review",
                "6. License approval",
            ],
            "timeline": "3-6 months",
        },
    }
    
    license_info = licenses.get(license_type, licenses["artisanal"])
    
    return {
        "license_type": license_type,
        "details": license_info,
        "disclaimer": MINING_ACT_SUMMARY["disclaimer"],
        "swahili_summary": f"Kibali: {license_info['swahili']}. Gharama: {license_info['cost']}. Muda: {license_info['timeline']}.",
    }


def _format_legal_swahili(sections: list[dict]) -> str:
    """Format legal information in Swahili."""
    summaries = []
    for section in sections:
        summaries.append(f"• {section['summary']}")
    return "\n".join(summaries)
