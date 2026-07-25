"""
Mining Super-Agent Tools
========================

These are TOOLS that the superagent uses — NOT separate agents.
The superagent (DeerFlow harness + Nemotron 3 Ultra) decides which 
tool to use based on the user's question.

Jensen Huang: "We create super sub-agents connected to specialized tools."
"""

from .registry import ToolRegistry
from .geological import GeologicalTools
from .satellite import SatelliteTools
from .market import MarketTools
from .quantum import QuantumTools

__all__ = [
    "ToolRegistry",
    "GeologicalTools",
    "SatelliteTools",
    "MarketTools",
    "QuantumTools",
]
