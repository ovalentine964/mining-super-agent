"""
Report Tools — PDF Report Generation
=====================================

Tools that the superagent uses for generating professional reports.
NOT a separate agent — the superagent calls these tools directly.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


async def generate_pdf(
    title: str,
    language: str = "sw",  # "sw" or "en"
    mineral_analysis: dict[str, Any] | None = None,
    geological_data: dict[str, Any] | None = None,
    market_data: dict[str, Any] | None = None,
    financial_data: dict[str, Any] | None = None,
    legal_data: dict[str, Any] | None = None,
    location: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Generate a professional PDF geological report.
    
    Includes:
    - Geological analysis section
    - Market data section
    - Financial projections section
    - Legal information section
    - Disclaimers and confidence statements
    """
    from ..reports.pdf_generator import PDFReportGenerator
    
    generator = PDFReportGenerator(language=language)
    
    report_data = {
        "title": title,
        "language": language,
        "mineral_analysis": mineral_analysis,
        "geological_data": geological_data,
        "market_data": market_data,
        "financial_data": financial_data,
        "legal_data": legal_data,
        "location": location,
    }
    
    # Generate PDF
    pdf_bytes = generator.generate(report_data)
    
    return {
        "pdf_bytes": pdf_bytes,
        "title": title,
        "language": language,
        "sections": [
            "geological_analysis",
            "market_data",
            "financial_projections",
            "legal_information",
        ],
        "disclaimer": (
            "Ripoti hii imetengenezwa na AI na ina taarifa za awali tu. "
            "Tafadhali pata uthibitisho wa mtaalamu kabla ya kufanya maamuzi ya kiuchumi."
            if language == "sw" else
            "This report is AI-generated and contains preliminary information only. "
            "Please obtain professional verification before making economic decisions."
        ),
    }
