"""
Mining Super-Agent — Entry point.

This imports from superagent.py — the single-agent architecture.
No orchestrator. No 10 specialist agents. ONE intelligent entity with tools.

Usage:
    from src.superagent import MiningSuperAgent
    agent = MiningSuperAgent()
    response = await agent.chat("Is there gold in Nyatike?")
"""

try:
    from .superagent import MiningSuperAgent
except ImportError:
    from src.superagent import MiningSuperAgent  # type: ignore[no-redef]

__all__ = ["MiningSuperAgent"]
