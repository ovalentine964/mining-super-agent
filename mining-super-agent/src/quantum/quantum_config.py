"""
Quantum Configuration — backend selection, resource limits, automatic degradation.

Decides when to use quantum vs classical based on problem size, available backends,
and historical performance benchmarks.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class QuantumBackend(Enum):
    """Available quantum backends."""
    PENNYLANE = "pennylane"
    QISKIT = "qiskit"
    CLASSICAL = "classical"


@dataclass
class QuantumConfig:
    """Configuration for quantum computing integration.

    Attributes:
        preferred_backend: Which quantum backend to try first.
        max_qubits: Maximum qubits to simulate (CPU limit).
        max_shots: Default measurement shots.
        timeout_seconds: Max time for a quantum computation.
        auto_select: Automatically pick best backend based on problem size.
        force_classical: Override all quantum with classical (for testing/fallback).
        qubit_threshold: Problem size below which classical is faster.
        benchmark_history: Tracks quantum vs classical performance.
    """

    preferred_backend: QuantumBackend = QuantumBackend.PENNYLANE
    max_qubits: int = 20
    max_shots: int = 1024
    timeout_seconds: float = 300.0
    auto_select: bool = True
    force_classical: bool = False
    qubit_threshold: int = 8
    benchmark_history: dict[str, dict[str, float]] = field(default_factory=dict)

    # ── Backend availability ──────────────────────────────────────────────

    def _pennylane_available(self) -> bool:
        try:
            import pennylane  # noqa: F401
            return True
        except ImportError:
            return False

    def _qiskit_available(self) -> bool:
        try:
            import qiskit  # noqa: F401
            return True
        except ImportError:
            return False

    def available_backends(self) -> list[QuantumBackend]:
        """Return list of currently available backends."""
        backends = [QuantumBackend.CLASSICAL]
        if self._pennylane_available():
            backends.append(QuantumBackend.PENNYLANE)
        if self._qiskit_available():
            backends.append(QuantumBackend.QISKIT)
        return backends

    # ── Automatic backend selection ────────────────────────────────────────

    def select_backend(
        self,
        problem_type: str,
        problem_size: int,
        n_qubits_needed: int | None = None,
    ) -> QuantumBackend:
        """Pick the best backend for a given problem.

        Args:
            problem_type: e.g. 'classification', 'optimization', 'chemistry'.
            problem_size: number of data points, variables, etc.
            n_qubits_needed: estimated qubits required.

        Returns:
            The backend to use (always CLASSICAL if quantum unavailable or not beneficial).
        """
        if self.force_classical:
            logger.info("force_classical=True → using CLASSICAL backend")
            return QuantumBackend.CLASSICAL

        if not self.auto_select:
            if self.preferred_backend in self.available_backends():
                return self.preferred_backend
            return QuantumBackend.CLASSICAL

        # Check if quantum was historically worse for this problem type
        if self._quantum_was_slower(problem_type):
            logger.info(f"Quantum historically slower for '{problem_type}' → CLASSICAL")
            return QuantumBackend.CLASSICAL

        # Problem too small for quantum advantage
        qubits = n_qubits_needed or self._estimate_qubits(problem_size)
        if qubits < self.qubit_threshold:
            logger.info(
                f"Problem needs {qubits} qubits < threshold {self.qubit_threshold} → CLASSICAL"
            )
            return QuantumBackend.CLASSICAL

        # Too many qubits to simulate on CPU
        if qubits > self.max_qubits:
            logger.warning(
                f"Need {qubits} qubits > max {self.max_qubits} → CLASSICAL"
            )
            return QuantumBackend.CLASSICAL

        # Pick preferred if available
        if self.preferred_backend in self.available_backends():
            logger.info(
                f"Using {self.preferred_backend.value} for '{problem_type}' "
                f"({qubits} qubits)"
            )
            return self.preferred_backend

        # Try the other quantum backend
        for backend in [QuantumBackend.PENNYLANE, QuantumBackend.QISKIT]:
            if backend != self.preferred_backend and backend in self.available_backends():
                logger.info(f"Falling back to {backend.value}")
                return backend

        return QuantumBackend.CLASSICAL

    # ── Benchmark integration ──────────────────────────────────────────────

    def record_benchmark(
        self,
        problem_type: str,
        backend: QuantumBackend,
        elapsed_seconds: float,
        accuracy: float | None = None,
    ) -> None:
        """Record performance for a backend on a problem type."""
        if problem_type not in self.benchmark_history:
            self.benchmark_history[problem_type] = {}
        key = backend.value
        entry = self.benchmark_history[problem_type]
        # Exponential moving average
        alpha = 0.3
        old_time = entry.get(f"{key}_time", elapsed_seconds)
        entry[f"{key}_time"] = alpha * elapsed_seconds + (1 - alpha) * old_time
        if accuracy is not None:
            old_acc = entry.get(f"{key}_accuracy", accuracy)
            entry[f"{key}_accuracy"] = alpha * accuracy + (1 - alpha) * old_acc

    def _quantum_was_slower(self, problem_type: str) -> bool:
        """Check if benchmark history shows quantum is slower."""
        history = self.benchmark_history.get(problem_type)
        if not history:
            return False
        classical_time = history.get("classical_time")
        quantum_time = min(
            history.get("pennylane_time", float("inf")),
            history.get("qiskit_time", float("inf")),
        )
        if classical_time and quantum_time < float("inf"):
            return quantum_time > classical_time * 1.5  # quantum is >50% slower
        return False

    def get_report(self) -> dict[str, Any]:
        """Return current config and benchmark state."""
        return {
            "preferred_backend": self.preferred_backend.value,
            "max_qubits": self.max_qubits,
            "available_backends": [b.value for b in self.available_backends()],
            "force_classical": self.force_classical,
            "auto_select": self.auto_select,
            "benchmark_history": dict(self.benchmark_history),
        }

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _estimate_qubits(problem_size: int) -> int:
        """Rough estimate: log2(problem_size) qubits needed."""
        import math
        if problem_size <= 1:
            return 1
        return max(1, int(math.ceil(math.log2(problem_size))))


# Module-level default config
DEFAULT_CONFIG = QuantumConfig()
