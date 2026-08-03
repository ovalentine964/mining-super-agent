"""
Mining Super-Agent — DeerFlow Entry Point.

This is the main entry point that starts the Mining Super-Agent
powered by the DeerFlow harness.

Usage:
    # Start full gateway (HTTP API + Telegram + all channels):
    python -m src.main

    # Start with custom config:
    python -m src.main --config src/config/deerflow_config.yaml

    # Start only the Telegram bot:
    python -m src.main --telegram-only

    # Query programmatically (no server):
    python -m src.main --query "Is there gold in Nyatike?"

    # Start legacy mode (no DeerFlow):
    python -m src.main --legacy
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger("mining-super-agent")


def setup_logging(level: str = "INFO") -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> None:
    """Main entry point for the Mining Super-Agent."""
    parser = argparse.ArgumentParser(
        description="Mining Super-Agent powered by DeerFlow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to DeerFlow config YAML (default: src/config/deerflow_config.yaml)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Gateway bind host (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Gateway bind port (default: 8080)",
    )
    parser.add_argument(
        "--telegram-only",
        action="store_true",
        help="Start only the Telegram bot channel",
    )
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="Run a single query and exit (no server)",
    )
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="Start in legacy mode without DeerFlow (uses original agent code)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO)",
    )
    parser.add_argument(
        "--init-skills",
        action="store_true",
        help="Initialize mining skill packages for DeerFlow",
    )

    args = parser.parse_args()
    setup_logging(args.log_level)

    # ── Initialize skills ───────────────────────────────────────
    if args.init_skills:
        from src.deerflow_integration import register_mining_skills
        register_mining_skills()
        logger.info("Mining skills initialized.")
        return

    # ── Single query mode ───────────────────────────────────────
    if args.query:
        _run_query(args.query, args.config)
        return

    # ── Legacy mode ─────────────────────────────────────────────
    if args.legacy:
        _run_legacy(args.host, args.port)
        return

    # ── Telegram-only mode ──────────────────────────────────────
    if args.telegram_only:
        from src.deerflow_integration import start_telegram_channel
        logger.info("Starting Telegram channel only...")
        start_telegram_channel(args.config)
        return

    # ── Full gateway mode (default) ─────────────────────────────
    from src.deerflow_integration import start_deerflow_gateway, register_mining_skills

    # Auto-initialize skills if needed
    register_mining_skills()

    logger.info("=" * 60)
    logger.info("  MINING SUPER-AGENT — Powered by DeerFlow 2.0")
    logger.info("=" * 60)
    logger.info("Config: %s", args.config or "default")
    logger.info("Gateway: http://%s:%d", args.host, args.port)
    logger.info("DeerFlow: vendor/deerflow")
    logger.info("=" * 60)

    start_deerflow_gateway(
        config_path=args.config,
        host=args.host,
        port=args.port,
    )


def _run_query(question: str, config_path: str | None = None) -> None:
    """Run a single query and print the result."""
    from src.deerflow_integration import MiningDeerFlowAgent

    agent = MiningDeerFlowAgent(config_path=config_path)
    result = asyncio.run(agent.query(question))

    print("\n" + "=" * 60)
    print("QUERY:", question)
    print("=" * 60)
    print(f"\nAnswer:\n{result.get('answer', 'No answer')}")
    if result.get("tools_used"):
        print(f"\nTools used: {', '.join(result['tools_used'])}")
    if result.get("confidence"):
        print(f"Confidence: {result['confidence']:.0%}")
    if result.get("fallback"):
        print("\n⚠️  Used fallback mode (DeerFlow not fully available)")
    print()


def _run_legacy(host: str, port: int) -> None:
    """Run the legacy FastAPI server without DeerFlow."""
    logger.info("Starting in LEGACY mode (no DeerFlow)...")
    try:
        import uvicorn
        from src.api.main import app
        uvicorn.run(app, host=host, port=port, log_level="info")
    except ImportError as e:
        logger.error("Legacy server dependencies missing: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
