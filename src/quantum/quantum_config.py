"""
Quantum configuration — backend selection, resource limits, automatic degradation.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class QuantumBackend(Enum):
    PENNYLANE = "pennylane"
    QISKIT = "qiskit"
    CLASSICAL = "classical"


@dataclass
class QuantumConfig:
    preferred_backend: QuantumBackend = QuantumBackend.PENNYLANE
    max_qubits: int = 20
    max_shots: int = 1024
    timeout_seconds: float = 300.0
    auto_select: bool = True
    force_classical: bool = False
    qubit_threshold: int = 8
    benchmark_history: dict[str, dict[str, float]] = field(default_factory=dict)

    def _pennylane_available(self) -> bool:
        try:
            import pennylane; return True
        except ImportError:
            return False

    def _qiskit_available(self) -> bool:
        try:
            import qiskit; return True
        except ImportError:
            return False

    def available_backends(self) -> list[QuantumBackend]:
        backends = [QuantumBackend.CLASSICAL]
        if self._pennylane_available():
            backends.append(QuantumBackend.PENNYLANE)
        if self._qiskit_available():
            backends.append(QuantumBackend.QISKIT)
        return backends

    def select_backend(self, problem_type: str, problem_size: int, n_qubits_needed: int | None = None) -> QuantumBackend:
        if self.force_classical:
            return QuantumBackend.CLASSICAL
        if not self.auto_select:
            return self.preferred_backend if self.preferred_backend in self.available_backends() else QuantumBackend.CLASSICAL

        qubits = n_qubits_needed or max(1, int(math.ceil(math.log2(max(2, problem_size)))))
        if qubits < self.qubit_threshold:
            return QuantumBackend.CLASSICAL
        if qubits > self.max_qubits:
            return QuantumBackend.CLASSICAL

        if self.preferred_backend in self.available_backends():
            return self.preferred_backend
        for b in [QuantumBackend.PENNYLANE, QuantumBackend.QISKIT]:
            if b != self.preferred_backend and b in self.available_backends():
                return b
        return QuantumBackend.CLASSICAL

    def record_benchmark(self, problem_type: str, backend: QuantumBackend, elapsed_seconds: float, accuracy: float | None = None):
        if problem_type not in self.benchmark_history:
            self.benchmark_history[problem_type] = {}
        entry = self.benchmark_history[problem_type]
        key = backend.value
        alpha = 0.3
        old = entry.get(f"{key}_time", elapsed_seconds)
        entry[f"{key}_time"] = alpha * elapsed_seconds + (1 - alpha) * old
        if accuracy is not None:
            old_acc = entry.get(f"{key}_accuracy", accuracy)
            entry[f"{key}_accuracy"] = alpha * accuracy + (1 - alpha) * old_acc


DEFAULT_CONFIG = QuantumConfig()
