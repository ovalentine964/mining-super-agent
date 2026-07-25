"""
Quantum Computing Integration for Mining Super-Agent.

Provides quantum-enhanced ML and optimization with automatic classical fallbacks.
Quantum activates only when beneficial; classical is always available.
"""

from .quantum_config import QuantumConfig, QuantumBackend
from .classical_fallback import ClassicalFallback

__all__ = [
    "QuantumConfig",
    "QuantumBackend",
    "ClassicalFallback",
]
