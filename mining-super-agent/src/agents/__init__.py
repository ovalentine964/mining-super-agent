"""
Mining Super-Agent: Multi-Agent System
Council-approved, production-ready agent framework.
"""

from .base import BaseAgent, AgentResult, ToolCall, ToolResult
from .orchestrator import OrchestratorAgent
from .geological import GeologicalAgent
from .satellite import SatelliteAgent
from .mineral_id import MineralIdAgent
from .market import MarketAgent
from .legal import LegalAgent
from .financial import FinancialAgent
from .community import CommunityAgent
from .exploration import ExplorationAgent
from .qc import QCAgent
from .quantum import QuantumAgent

__all__ = [
    "BaseAgent",
    "AgentResult",
    "ToolCall",
    "ToolResult",
    "OrchestratorAgent",
    "GeologicalAgent",
    "SatelliteAgent",
    "MineralIdAgent",
    "MarketAgent",
    "LegalAgent",
    "FinancialAgent",
    "CommunityAgent",
    "ExplorationAgent",
    "QCAgent",
    "QuantumAgent",
]
