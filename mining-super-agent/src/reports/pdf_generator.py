"""
PDF Report Generator for Mining Super-Agent.
Generates professional geological reports in PDF format.
Supports Swahili and English templates.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

logger = logging.getLogger(__name__)

# Report output directory
REPORTS_DIR = Path(__file__).parent / "output"
TEMPLATES_DIR = Path(__file__).parent / "templates"


class ReportGenerator:
    """Generates professional mining analysis PDF reports."""

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir) if output_dir else REPORTS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=True,
        )

    def generate_report(
        self,
        observation_id: str,
        mineral_name: str,
        rock_type: str,
        confidence: float,
        description: str,
        is_economic: bool,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        image_path: Optional[str] = None,
        market_data: Optional[dict] = None,
        financial_projection: Optional[dict] = None,
        language: str = "sw",
        user_name: Optional[str] = None,
    ) -> str:
        """
        Generate a PDF report for a mining observation.

        Args:
            observation_id: Unique observation ID
            mineral_name: Identified mineral name
            rock_type: Type of rock
            confidence: Confidence score (0.0 - 1.0)
            description: Detailed description
            is_economic: Whether mineral has economic value
            latitude: GPS latitude
            longitude: GPS longitude
            image_path: Path to observation image
            market_data: Current market prices
            financial_projection: Financial projections
            language: Report language ('sw' or 'en')
            user_name: Report recipient name

        Returns:
            Path to generated PDF file
        """
        # Select template
        template_name = f"report_{language}.html"
        try:
            template = self.env.get_template(template_name)
        except Exception:
            logger.warning(f"Template {template_name} not found, falling back to English")
            template = self.env.get_template("report_en.html")

        # Confidence level label
        confidence_label = self._get_confidence_label(confidence, language)
        confidence_color = self._get_confidence_color(confidence)

        # Current date/time
        now = datetime.now()

        # Build market data if not provided
        if market_data is None:
            market_data = self._get_default_market_data()

        # Build financial projection if not provided and mineral is economic
        if financial_projection is None and is_economic:
            financial_projection = self._get_default_financial_projection(confidence)

        # Convert image to base64 for embedding
        image_base64 = None
        if image_path and os.path.exists(image_path):
            import base64
            with open(image_path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")

        # Template context
        context = {
            "observation_id": observation_id,
            "mineral_name": mineral_name,
            "rock_type": rock_type,
            "confidence": confidence,
            "confidence_label": confidence_label,
            "confidence_color": confidence_color,
            "confidence_percent": f"{confidence * 100:.0f}",
            "description": description,
            "is_economic": is_economic,
            "latitude": f"{latitude:.6f}" if latitude else "N/A",
            "longitude": f"{longitude:.6f}" if longitude else "N/A",
            "image_base64": image_base64,
            "market_data": market_data,
            "financial_projection": financial_projection,
            "report_date": now.strftime("%d %B %Y"),
            "report_time": now.strftime("%H:%M"),
            "report_id": f"RPT-{observation_id[:8].upper()}",
            "user_name": user_name or "Miner",
            "language": language,
            # Disclaimers
            "disclaimer_primary": self._get_disclaimer("primary", language),
            "disclaimer_financial": self._get_disclaimer("financial", language),
            "disclaimer_ai": self._get_disclaimer("ai", language),
        }

        # Render HTML
        html_content = template.render(**context)

        # Generate PDF
        pdf_filename = f"report_{observation_id[:8]}_{language}_{now.strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = self.output_dir / pdf_filename

        HTML(string=html_content).write_pdf(str(pdf_path))

        logger.info(f"Report generated: {pdf_path}")
        return str(pdf_path)

    def _get_confidence_label(self, confidence: float, language: str) -> str:
        """Get human-readable confidence label."""
        if language == "sw":
            if confidence >= 0.8:
                return "Uhakika Mkubwa Sana"
            elif confidence >= 0.6:
                return "Uhakika Mkubwa"
            elif confidence >= 0.4:
                return "Uhakika Wastani"
            elif confidence >= 0.2:
                return "Uhakika mdogo"
            else:
                return "Uhakika Mdogo Sana"
        else:
            if confidence >= 0.8:
                return "Very High Confidence"
            elif confidence >= 0.6:
                return "High Confidence"
            elif confidence >= 0.4:
                return "Moderate Confidence"
            elif confidence >= 0.2:
                return "Low Confidence"
            else:
                return "Very Low Confidence"

    def _get_confidence_color(self, confidence: float) -> str:
        """Get color for confidence display."""
        if confidence >= 0.7:
            return "#22C55E"  # Green
        elif confidence >= 0.4:
            return "#F59E0B"  # Amber
        else:
            return "#EF4444"  # Red

    def _get_disclaimer(self, disclaimer_type: str, language: str) -> str:
        """Get disclaimer text."""
        disclaimers = {
            "primary": {
                "sw": "Ripoti hii imetolewa na mfumo wa akili bandia (AI) kama zana ya msaada tu. "
                      "Si mbadala wa ushauri wa kitaalamu wa kijiolojia. "
                      "Daima thibitisha na mtaalamu wa madini kabla ya maamuzi yoyote ya kifedha.",
                "en": "This report was generated by an artificial intelligence (AI) system as an aid tool only. "
                      "It is not a substitute for professional geological advice. "
                      "Always verify with a mining expert before making any financial decisions.",
            },
            "financial": {
                "sw": "Takwimu za kifedha katika ripoti hii ni makadirio tu. "
                      "Mapato halisi yanaweza kutofautiana sana kutokana na mambo mengi "
                      "yakiwemo bei za soko, gharama za uendeshaji, na mabadiliko ya sera.",
                "en": "Financial figures in this report are estimates only. "
                      "Actual returns may vary significantly due to many factors "
                      "including market prices, operating costs, and policy changes.",
            },
            "ai": {
                "sw": "Uchambuzi huu umefanywa na AI na una mapungufu. "
                      "Uthibitisho wa madini kwa picha pekee una uhakika wa chini "
                      "(chini ya 65%). Uchunguzi wa maabara unahitajika kwa uthibitisho.",
                "en": "This analysis was performed by AI and has limitations. "
                      "Photo-based mineral identification alone has low confidence "
                      "(below 65%). Laboratory testing is required for verification.",
            },
        }
        return disclaimers.get(disclaimer_type, {}).get(language, disclaimers[disclaimer_type]["en"])

    def _get_default_market_data(self) -> dict:
        """Get default market data (placeholder)."""
        return {
            "gold": {
                "name": "Gold (Au)",
                "price_usd": 4051.20,
                "price_kes": 523412,
                "unit": "oz",
                "change_percent": 1.2,
            },
            "copper": {
                "name": "Copper (Cu)",
                "price_usd": 10245.00,
                "price_kes": 1323630,
                "unit": "tonne",
                "change_percent": -0.5,
            },
            "neodymium": {
                "name": "Neodymium (Nd)",
                "price_usd": 95.00,
                "price_kes": 12270,
                "unit": "kg",
                "change_percent": 2.1,
            },
        }

    def _get_default_financial_projection(self, confidence: float) -> dict:
        """Get conservative financial projection."""
        # Scale by confidence — lower confidence = lower projection
        factor = confidence * 0.5  # Conservative: max 50% of confidence

        return {
            "conservative": {
                "label": "Conservative (Min)",
                "value_kes": int(5000000 * factor),
                "value_usd": int(3870 * factor),
                "probability": "80%",
            },
            "moderate": {
                "label": "Moderate (Expected)",
                "value_kes": int(25000000 * factor),
                "value_usd": int(19350 * factor),
                "probability": "50%",
            },
            "optimistic": {
                "label": "Optimistic (Max)",
                "value_kes": int(100000000 * factor),
                "value_usd": int(77400 * factor),
                "probability": "20%",
            },
            "disclaimer": "These projections are purely illustrative and based on general "
                          "industry averages. Actual value depends on deposit size, grade, "
                          "accessibility, market conditions, and legal framework. "
                          "Professional geological survey required for accurate valuation.",
        }


def generate_report_cli():
    """CLI entry point for report generation."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate mining analysis PDF report")
    parser.add_argument("--observation-id", required=True, help="Observation ID")
    parser.add_argument("--mineral", required=True, help="Identified mineral name")
    parser.add_argument("--rock-type", default="Unknown", help="Rock type")
    parser.add_argument("--confidence", type=float, required=True, help="Confidence (0.0-1.0)")
    parser.add_argument("--description", required=True, help="Description")
    parser.add_argument("--economic", action="store_true", help="Is economic mineral")
    parser.add_argument("--lat", type=float, help="Latitude")
    parser.add_argument("--lon", type=float, help="Longitude")
    parser.add_argument("--image", help="Image path")
    parser.add_argument("--lang", default="sw", choices=["sw", "en"], help="Language")
    parser.add_argument("--output", help="Output directory")

    args = parser.parse_args()

    generator = ReportGenerator(output_dir=args.output)

    pdf_path = generator.generate_report(
        observation_id=args.observation_id,
        mineral_name=args.mineral,
        rock_type=args.rock_type,
        confidence=args.confidence,
        description=args.description,
        is_economic=args.economic,
        latitude=args.lat,
        longitude=args.lon,
        image_path=args.image,
        language=args.lang,
    )

    print(f"Report generated: {pdf_path}")


if __name__ == "__main__":
    generate_report_cli()
