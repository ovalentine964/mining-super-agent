"""
PDF Report Generator for Mining Analysis Reports.
Generates professional geological reports in English and Swahili.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PDFReportGenerator:
    """Generate PDF reports for mining analysis."""

    def __init__(self, templates_dir: str = "src/reports/templates"):
        self.templates_dir = Path(templates_dir)

    def generate_analysis_report(
        self,
        analysis: Dict[str, Any],
        language: str = "en",
        output_path: Optional[str] = None,
    ) -> str:
        """Generate a PDF analysis report."""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib import colors
        except ImportError:
            logger.warning("reportlab not installed — generating text report instead")
            return self._generate_text_report(analysis, language)

        if output_path is None:
            output_path = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        doc = SimpleDocTemplate(output_path, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title = "Mining Analysis Report" if language == "en" else "Ripoti ya Uchambuzi wa Madini"
        story.append(Paragraph(title, styles["Title"]))
        story.append(Spacer(1, 1 * cm))

        # Date
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        story.append(Paragraph(f"Generated: {date_str}", styles["Normal"]))
        story.append(Spacer(1, 0.5 * cm))

        # Summary
        if "summary" in analysis:
            story.append(Paragraph("Summary" if language == "en" else "Muhtasari", styles["Heading2"]))
            story.append(Paragraph(str(analysis["summary"]), styles["Normal"]))
            story.append(Spacer(1, 0.5 * cm))

        # Mineral Identification
        if "mineral" in analysis:
            story.append(Paragraph("Mineral Identification" if language == "en" else "Utambuzi wa Madini", styles["Heading2"]))
            data = [
                ["Property", "Value"],
                ["Mineral", str(analysis.get("mineral", "Unknown"))],
                ["Confidence", f"{analysis.get('confidence', 0):.1%}"],
                ["Source", str(analysis.get("source_type", "image"))],
            ]
            table = Table(data)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(table)
            story.append(Spacer(1, 0.5 * cm))

        # Disclaimers
        disclaimers = analysis.get("disclaimers", [])
        if disclaimers:
            story.append(Paragraph("Disclaimers" if language == "en" else "Onyo", styles["Heading2"]))
            for d in disclaimers:
                story.append(Paragraph(f"• {d}", styles["Normal"]))

        # Build PDF
        doc.build(story)
        logger.info("Report generated: %s", output_path)
        return output_path

    def _generate_text_report(self, analysis: Dict[str, Any], language: str) -> str:
        """Fallback text report when reportlab is not available."""
        output_path = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        lines = [
            "=" * 60,
            "MINING ANALYSIS REPORT" if language == "en" else "RIPOTI YA UCHAMBUZI WA MADINI",
            "=" * 60,
            f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            "",
        ]
        if "summary" in analysis:
            lines.extend(["SUMMARY:", str(analysis["summary"]), ""])
        if "mineral" in analysis:
            lines.extend([
                "MINERAL IDENTIFICATION:",
                f"  Mineral: {analysis.get('mineral', 'Unknown')}",
                f"  Confidence: {analysis.get('confidence', 0):.1%}",
                "",
            ])
        if "disclaimers" in analysis:
            lines.append("DISCLAIMERS:")
            for d in analysis["disclaimers"]:
                lines.append(f"  • {d}")

        Path(output_path).write_text("\n".join(lines))
        return output_path
