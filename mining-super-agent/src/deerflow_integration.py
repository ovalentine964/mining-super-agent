"""
DeerFlow Integration — Bridge between DeerFlow harness and Mining Super-Agent.

This module:
1. Configures DeerFlow with mining-specific settings
2. Registers mining tools with DeerFlow's tool system
3. Starts the DeerFlow gateway with Telegram channel support
4. Provides programmatic access to the DeerFlow agent for mining queries

Usage:
    # Start the full DeerFlow gateway (HTTP + Telegram):
    python -m src.main

    # Or use programmatically:
    from src.deerflow_integration import MiningDeerFlowAgent
    agent = MiningDeerFlowAgent()
    result = await agent.query("Is there gold in Nyatike?")
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Project root setup
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DEERFLOW_DIR = PROJECT_ROOT / "vendor" / "deerflow"
DEERFLOW_CONFIG = PROJECT_ROOT / "src" / "config" / "deerflow_config.yaml"


def _ensure_deerflow_on_path() -> None:
    """Add DeerFlow packages to sys.path so imports work."""
    harness_path = str(DEERFLOW_DIR / "backend" / "packages" / "harness")
    backend_path = str(DEERFLOW_DIR / "backend")
    src_path = str(PROJECT_ROOT / "src")

    for p in [harness_path, backend_path, src_path]:
        if p not in sys.path:
            sys.path.insert(0, p)


_ensure_deerflow_on_path()


# ---------------------------------------------------------------------------
# DeerFlow Agent wrapper for mining queries
# ---------------------------------------------------------------------------

class MiningDeerFlowAgent:
    """
    High-level wrapper around DeerFlow for mining domain queries.

    This class initializes DeerFlow with mining-specific configuration
    and provides convenient methods for common mining operations.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or str(DEERFLOW_CONFIG)
        self._initialized = False
        self._app_config = None

    def _ensure_config(self) -> None:
        """Set environment variables so DeerFlow finds our config."""
        if not os.environ.get("DEER_FLOW_CONFIG_PATH"):
            os.environ["DEER_FLOW_CONFIG_PATH"] = self.config_path
        if not os.environ.get("DEER_FLOW_PROJECT_ROOT"):
            os.environ["DEER_FLOW_PROJECT_ROOT"] = str(PROJECT_ROOT)

    def _load_config(self):
        """Load and validate the DeerFlow app config."""
        if self._app_config is not None:
            return self._app_config

        self._ensure_config()

        try:
            from deerflow.config.app_config import load_app_config
            self._app_config = load_app_config()
            logger.info("DeerFlow config loaded from %s", self.config_path)
            return self._app_config
        except ImportError as e:
            logger.error("Could not import DeerFlow config: %s", e)
            logger.error(
                "Ensure DeerFlow is installed. Run: "
                "cd vendor/deerflow/backend && pip install -e packages/harness"
            )
            raise

    async def query(
        self,
        question: str,
        context: Optional[dict[str, Any]] = None,
        model_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Send a query to the DeerFlow agent and get a response.

        Args:
            question: The user's question about mining/geology
            context: Optional additional context (location, images, etc.)
            model_name: Optional model override

        Returns:
            Dict with 'answer', 'tools_used', 'confidence', etc.
        """
        config = self._load_config()

        try:
            from deerflow.agents import create_agent
            from deerflow.tools import get_available_tools

            tools = get_available_tools(app_config=config)
            agent = create_agent(
                tools=tools,
                model_name=model_name or config.default_model,
                app_config=config,
            )

            # Build the message with context
            message = question
            if context:
                ctx_parts = []
                if "latitude" in context and "longitude" in context:
                    ctx_parts.append(f"Location: ({context['latitude']}, {context['longitude']})")
                if "image_path" in context:
                    ctx_parts.append(f"Image: {context['image_path']}")
                if "mineral" in context:
                    ctx_parts.append(f"Mineral: {context['mineral']}")
                if ctx_parts:
                    message = f"{question}\n\nContext: {'; '.join(ctx_parts)}"

            # Run the agent
            result = await agent.ainvoke({"messages": [{"role": "user", "content": message}]})

            return {
                "success": True,
                "answer": result.get("messages", [{}])[-1].get("content", ""),
                "tools_used": result.get("tools_used", []),
                "model": model_name or config.default_model,
            }

        except ImportError as e:
            logger.warning("DeerFlow agent not available: %s. Using fallback.", e)
            return await self._fallback_query(question, context)

    async def _fallback_query(
        self,
        question: str,
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Fallback query handler when DeerFlow is not fully installed.
        Uses the existing MiningSuperAgent directly.
        """
        try:
            from src.main_legacy import MiningSuperAgent
            agent = MiningSuperAgent()
            result = await agent.analyze(question, context)
            return {
                "success": result.success,
                "answer": result.summary,
                "confidence": result.confidence,
                "warnings": result.warnings,
                "fallback": True,
            }
        except Exception as e:
            logger.error("Fallback query also failed: %s", e)
            return {
                "success": False,
                "answer": f"Error: {e}",
                "fallback": True,
            }

    def analyze_mineral_photo(
        self,
        image_path: str,
        location: Optional[dict[str, float]] = None,
    ) -> dict[str, Any]:
        """Convenience: analyze a mineral photo."""
        context = {"image_path": image_path}
        if location:
            context["latitude"] = location.get("lat")
            context["longitude"] = location.get("lon")

        question = f"Identify the mineral in this photo: {image_path}"
        if location:
            question += f" (Location: {location['lat']}, {location['lon']})"

        return asyncio.run(self.query(question, context))

    def get_price_report(
        self,
        commodities: list[str] | None = None,
        language: str = "english",
    ) -> dict[str, Any]:
        """Convenience: get commodity price report."""
        if commodities is None:
            commodities = ["gold", "copper", "silver"]

        question = f"Get current prices for: {', '.join(commodities)}"
        if language == "swahili":
            question += " — Report in Swahili"

        return asyncio.run(self.query(question))

    def check_compliance(self, project_type: str, mineral: str) -> dict[str, Any]:
        """Convenience: check compliance requirements."""
        question = (
            f"What are the legal requirements for {project_type} mining of {mineral} "
            f"in Migori County, Kenya?"
        )
        return asyncio.run(self.query(question))


# ---------------------------------------------------------------------------
# Gateway launcher
# ---------------------------------------------------------------------------

def start_deerflow_gateway(
    config_path: Optional[str] = None,
    host: str = "0.0.0.0",
    port: int = 8080,
) -> None:
    """
    Start the DeerFlow gateway with all configured channels.

    This launches:
    - HTTP API (FastAPI/Uvicorn)
    - Telegram bot (if configured)
    - Any other configured IM channels

    Args:
        config_path: Path to deerflow_config.yaml
        host: Bind host
        port: Bind port
    """
    config_file = config_path or str(DEERFLOW_CONFIG)

    # Set DeerFlow environment
    os.environ["DEER_FLOW_CONFIG_PATH"] = config_file
    os.environ["DEER_FLOW_PROJECT_ROOT"] = str(PROJECT_ROOT)

    logger.info("Starting DeerFlow gateway with config: %s", config_file)
    logger.info("DeerFlow source: %s", DEERFLOW_DIR)

    try:
        # Try to use DeerFlow's built-in gateway
        from app.gateway import create_app
        import uvicorn

        app = create_app()
        uvicorn.run(app, host=host, port=port, log_level="info")

    except ImportError as e:
        logger.warning("DeerFlow gateway not available: %s", e)
        logger.info("Falling back to legacy API server...")
        _start_legacy_server(host, port)


def _start_legacy_server(host: str, port: int) -> None:
    """Fallback: start the legacy FastAPI server."""
    try:
        import uvicorn
        from src.api.main import app
        uvicorn.run(app, host=host, port=port, log_level="info")
    except ImportError as e:
        logger.error("Cannot start any server: %s", e)
        sys.exit(1)


def start_telegram_channel(config_path: Optional[str] = None) -> None:
    """
    Start the Telegram channel using DeerFlow's built-in Telegram integration.

    DeerFlow handles:
    - Webhook or polling mode
    - Message routing to the agent
    - Response formatting
    - Rate limiting
    """
    config_file = config_path or str(DEERFLOW_CONFIG)
    os.environ["DEER_FLOW_CONFIG_PATH"] = config_file
    os.environ["DEER_FLOW_PROJECT_ROOT"] = str(PROJECT_ROOT)

    try:
        from app.channels.telegram import start_telegram_bot
        logger.info("Starting DeerFlow Telegram channel...")
        start_telegram_bot()
    except ImportError as e:
        logger.warning("DeerFlow Telegram channel not available: %s", e)
        logger.info("Ensure python-telegram-bot is installed and DeerFlow backend is on PYTHONPATH")


# ---------------------------------------------------------------------------
# Skills loader — registers mining skills with DeerFlow
# ---------------------------------------------------------------------------

def register_mining_skills() -> None:
    """
    Register mining domain skills with DeerFlow's skill system.

    Skills are self-contained capability packages that DeerFlow can
    discover and use. Each skill has a SKILL.md describing its capabilities.
    """
    skills_dir = PROJECT_ROOT / "src" / "skills"
    if not skills_dir.exists():
        skills_dir.mkdir(parents=True, exist_ok=True)

        # Create core mining skills
        _create_skill(
            skills_dir / "mineral-identification",
            "Mineral Identification",
            "Identify minerals from photos, physical properties, and spectral data.",
            ["identify_mineral_photo", "classify_with_clip"],
        )
        _create_skill(
            skills_dir / "geological-analysis",
            "Geological Analysis",
            "Analyze geology, run 3D models, query geological databases.",
            ["query_geological_database", "run_gempy_model", "query_mindat", "run_geophysical_inversion"],
        )
        _create_skill(
            skills_dir / "satellite-exploration",
            "Satellite Exploration",
            "Analyze satellite imagery for mineral exploration — spectral indices, alteration zones.",
            ["query_sentinel2", "calculate_spectral_indices", "detect_alteration_zones"],
        )
        _create_skill(
            skills_dir / "market-intelligence",
            "Market Intelligence",
            "Track commodity prices, analyze trends, generate market reports.",
            ["get_commodity_price", "get_price_history", "analyze_price_trend"],
        )
        _create_skill(
            skills_dir / "compliance",
            "Mining Compliance",
            "Check legal requirements, EIA, FPIC, and generate compliance checklists.",
            ["check_license_requirements", "check_eia_requirements", "check_fpic_requirements", "generate_compliance_checklist"],
        )

        logger.info("Created mining skills in %s", skills_dir)


def _create_skill(skill_dir: Path, name: str, description: str, tools: list[str]) -> None:
    """Create a skill directory with SKILL.md."""
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    tools_list = "\n".join(f"- `{t}`" for t in tools)
    skill_md.write_text(f"""# {name}

{description}

## Tools

{tools_list}

## Usage

This skill is automatically discovered by DeerFlow. The agent will use these
tools when the user's query relates to {name.lower()}.
""")


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

__all__ = [
    "MiningDeerFlowAgent",
    "start_deerflow_gateway",
    "start_telegram_channel",
    "register_mining_skills",
    "PROJECT_ROOT",
    "DEERFLOW_DIR",
    "DEERFLOW_CONFIG",
]
