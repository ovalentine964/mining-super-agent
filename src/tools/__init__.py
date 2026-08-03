"""
Sovereign Resource DAO Tools
========================

These are TOOLS that the superagent uses — NOT separate agents.
The superagent (DeerFlow harness + Nemotron 3 Ultra) decides which 
tool to use based on the user's question.

Jensen Huang: "We create super sub-agents connected to specialized tools."
"""

from .registry import ToolRegistry, ToolNotFoundError
from .geological import register_geological_tools
from .satellite import register_satellite_tools
from .market import register_market_tools
from .quantum import register_quantum_tools
from .vision import register_vision_tools
from .legal import register_legal_tools
from .financial import register_financial_tools
from .reports import register_report_tools
from . import schemas

__all__ = [
    "ToolRegistry",
    "ToolNotFoundError",
    "register_geological_tools",
    "register_satellite_tools",
    "register_market_tools",
    "register_quantum_tools",
    "register_vision_tools",
    "register_legal_tools",
    "register_financial_tools",
    "register_report_tools",
    "schemas",
    "register_all_tools",
]


def register_all_tools(registry: ToolRegistry) -> None:
    """Convenience: register ALL tools from ALL modules at once."""
    register_geological_tools(registry)
    register_satellite_tools(registry)
    register_market_tools(registry)
    register_quantum_tools(registry)
    register_vision_tools(registry)
    register_legal_tools(registry)
    register_financial_tools(registry)
    register_report_tools(registry)
