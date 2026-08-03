"""
QAOA (Quantum Approximate Optimization Algorithm) for Drill Target Optimization.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from .quantum_config import QuantumConfig, QuantumBackend, DEFAULT_CONFIG
from .classical_fallback import ClassicalFallback, BenchmarkResult

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    selected_targets: list[int]
    total_value: float
    energy: float
    backend_used: str
    elapsed_seconds: float


class QAOAOptimizer:
    """QAOA-based drill target optimization."""

    def __init__(self, config: QuantumConfig | None = None):
        self.config = config or DEFAULT_CONFIG

    @staticmethod
    def build_qubo_matrix(site_values, distance_matrix, cost_per_site, n_select, penalty_weight=10.0):
        n = len(site_values)
        Q = np.zeros((n, n))
        for i in range(n):
            Q[i, i] = -(site_values[i] - cost_per_site[i])
        for i in range(n):
            for j in range(i + 1, n):
                dist = distance_matrix[i, j]
                if dist > 0:
                    penalty = penalty_weight / (dist + 1e-6)
                    Q[i, j] += penalty
                    Q[j, i] += penalty
        for i in range(n):
            Q[i, i] += penalty_weight * (1 - 2 * n_select)
            for j in range(i + 1, n):
                Q[i, j] += 2 * penalty_weight
                Q[j, i] += 2 * penalty_weight
        return Q

    def solve_with_qaoa(self, Q: np.ndarray, depth: int = 3, maxiter: int = 200) -> OptimizationResult:
        start = time.perf_counter()
        try:
            from qiskit.quantum_info import SparsePauliOp
            from qiskit_algorithms import QAOA as QiskitQAOA
            from qiskit_algorithms.optimizers import COBYLA
            from qiskit_aer import AerSimulator
            from qiskit.primitives import BackendSampler

            n = Q.shape[0]
            hamiltonian = self._qubo_to_ising(Q)
            backend = AerSimulator()
            sampler = BackendSampler(backend=backend)
            optimizer = COBYLA(maxiter=maxiter)
            qaoa = QiskitQAOA(sampler=sampler, optimizer=optimizer, reps=depth)
            result = qaoa.compute_minimum_eigenvalue(hamiltonian)

            best_bitstring = self._extract_bitstring(result, n)
            selected = [i for i, bit in enumerate(best_bitstring) if bit == 1]
            energy = float(result.eigenvalue.real) if hasattr(result.eigenvalue, 'real') else float(result.eigenvalue)

            elapsed = time.perf_counter() - start
            return OptimizationResult(selected_targets=selected, total_value=-energy, energy=energy, backend_used="qiskit_qaoa", elapsed_seconds=elapsed)
        except Exception as e:
            logger.warning("QAOA failed: %s. Falling back.", e)
            return self._solve_classical(Q)

    def _qubo_to_ising(self, Q: np.ndarray):
        from qiskit.quantum_info import SparsePauliOp
        n = Q.shape[0]
        pauli_list, coeffs = [], []
        for i in range(n):
            label = ["I"] * n
            label[n - 1 - i] = "Z"
            pauli_list.append("".join(label))
            coeffs.append(-Q[i, i] / 2)
            for j in range(i + 1, n):
                if Q[i, j] != 0 or Q[j, i] != 0:
                    coupling = (Q[i, j] + Q[j, i]) / 2
                    label = ["I"] * n
                    label[n - 1 - i] = "Z"
                    label[n - 1 - j] = "Z"
                    pauli_list.append("".join(label))
                    coeffs.append(coupling / 4)
        return SparsePauliOp.from_list(list(zip(pauli_list, coeffs)))

    def _extract_bitstring(self, result, n: int) -> list[int]:
        try:
            if hasattr(result, 'eigenstate'):
                eigenstate = result.eigenstate
                if hasattr(eigenstate, 'most_likely'):
                    return [int(b) for b in eigenstate.most_likely()]
                elif isinstance(eigenstate, dict):
                    best = max(eigenstate, key=eigenstate.get)
                    return [int(b) for b in best]
            return [0] * n
        except Exception:
            return [0] * n

    def _solve_classical(self, Q: np.ndarray) -> OptimizationResult:
        result = ClassicalFallback.optimize_qubo(Q)
        bitstring = result.result["bitstring"]
        selected = [i for i, bit in enumerate(bitstring) if bit == 1]
        return OptimizationResult(selected_targets=selected, total_value=-result.result["energy"], energy=result.result["energy"], backend_used=f"classical_{result.method}", elapsed_seconds=result.elapsed_seconds)

    @staticmethod
    def generate_random_problem(n_sites: int, n_select: int | None = None, seed: int = 42):
        """Generate a random drill-target optimization problem for benchmarking."""
        rng = np.random.default_rng(seed)
        if n_select is None:
            n_select = max(1, n_sites // 4)
        site_values = rng.uniform(10, 100, size=n_sites)
        coords = rng.uniform(0, 1000, size=(n_sites, 2))
        dist_matrix = np.zeros((n_sites, n_sites))
        for i in range(n_sites):
            for j in range(i + 1, n_sites):
                d = float(np.linalg.norm(coords[i] - coords[j]))
                dist_matrix[i, j] = d
                dist_matrix[j, i] = d
        costs = rng.uniform(5, 30, size=n_sites)
        return site_values, dist_matrix, costs

    def optimize_drill_targets(self, site_values, distance_matrix, cost_per_site, n_select, penalty_weight=10.0) -> OptimizationResult:
        Q = self.build_qubo_matrix(site_values, distance_matrix, cost_per_site, n_select, penalty_weight)
        n_qubits = len(site_values)
        backend = self.config.select_backend("drill_optimization", n_qubits, n_qubits)
        if backend == QuantumBackend.QISKIT:
            return self.solve_with_qaoa(Q)
        return self._solve_classical(Q)
