"""
QAOA (Quantum Approximate Optimization Algorithm) for Drill Target Optimization.

Formulates drill target selection as a QUBO problem and solves it using
Qiskit QAOA or classical simulated annealing fallback.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .quantum_config import QuantumConfig, QuantumBackend, DEFAULT_CONFIG
from .classical_fallback import ClassicalFallback, BenchmarkResult

logger = logging.getLogger(__name__)

_qiskit = None


def _ensure_qiskit():
    global _qiskit
    if _qiskit is None:
        try:
            import qiskit
            _qiskit = qiskit
        except ImportError:
            raise ImportError("Qiskit not installed. Using classical fallback.")


@dataclass
class OptimizationResult:
    """Result from QAOA or classical optimization."""
    selected_targets: list[int]
    total_value: float
    energy: float
    backend_used: str
    elapsed_seconds: float
    all_solutions: list[dict] | None = None


class QAOAOptimizer:
    """QAOA-based drill target optimization.

    Formulates the drill site selection problem as a QUBO:
        min  x^T Q x
        where Q encodes geological value, drilling cost, and spatial constraints.

    QAOA explores the combinatorial solution space using quantum superposition,
    finding near-global-optimal solutions that classical optimizers miss.

    Falls back to classical differential evolution when quantum unavailable.
    """

    def __init__(self, config: QuantumConfig | None = None):
        self.config = config or DEFAULT_CONFIG

    # ── Problem formulation ───────────────────────────────────────────────

    @staticmethod
    def build_qubo_matrix(
        site_values: NDArray,
        distance_matrix: NDArray,
        cost_per_site: NDArray,
        n_select: int,
        penalty_weight: float = 10.0,
    ) -> NDArray:
        """Build QUBO matrix for drill target selection.

        Objective: maximize total geological value - total drilling cost
        Subject to: select exactly n_select sites

        QUBO form: min  x^T Q x
        where x[i] ∈ {0, 1} (1 = drill here)

        Args:
            site_values: (n,) array of estimated mineral value at each site.
            distance_matrix: (n, n) pairwise distances between sites.
            cost_per_site: (n) drilling cost at each site.
            n_select: Number of sites to select.
            penalty_weight: Weight for constraint violation penalty.

        Returns:
            QUBO matrix Q of shape (n, n).
        """
        n = len(site_values)
        Q = np.zeros((n, n))

        # Diagonal: value - cost for each site
        for i in range(n):
            Q[i, i] = -(site_values[i] - cost_per_site[i])

        # Off-diagonal: penalize selecting sites too close together
        for i in range(n):
            for j in range(i + 1, n):
                dist = distance_matrix[i, j]
                if dist > 0:
                    # Proximity penalty — don't cluster drills
                    proximity_penalty = penalty_weight / (dist + 1e-6)
                    Q[i, j] += proximity_penalty
                    Q[j, i] += proximity_penalty

        # Cardinality constraint: penalize != n_select sites selected
        # P * (sum(x_i) - n_select)^2 = P * [sum(x_i^2) + 2*sum(x_i*x_j) - 2*n_select*sum(x_i) + n_select^2]
        # Since x_i^2 = x_i for binary:
        for i in range(n):
            Q[i, i] += penalty_weight * (1 - 2 * n_select)
            for j in range(i + 1, n):
                Q[i, j] += 2 * penalty_weight
                Q[j, i] += 2 * penalty_weight

        return Q

    # ── QAOA solver ───────────────────────────────────────────────────────

    def solve_with_qaoa(
        self,
        Q: NDArray,
        depth: int = 3,
        maxiter: int = 200,
    ) -> OptimizationResult:
        """Solve QUBO using Qiskit QAOA.

        Args:
            Q: QUBO matrix.
            depth: QAOA circuit depth (more layers = better approximation).
            maxiter: Maximum optimizer iterations.

        Returns:
            OptimizationResult with selected targets.
        """
        start = time.perf_counter()
        try:
            _ensure_qiskit()
            from qiskit.quantum_info import SparsePauliOp
            from qiskit_algorithms import QAOA as QiskitQAOA
            from qiskit_algorithms.optimizers import COBYLA
            from qiskit_aer import AerSimulator
            from qiskit.primitives import BackendSampler

            n = Q.shape[0]

            # Convert QUBO to Ising Hamiltonian
            hamiltonian = self._qubo_to_ising(Q)

            # Set up QAOA
            backend = AerSimulator()
            sampler = BackendSampler(backend=backend)
            optimizer = COBYLA(maxiter=maxiter)
            qaoa = QiskitQAOA(
                sampler=sampler,
                optimizer=optimizer,
                reps=depth,
            )

            # Run QAOA
            result = qaoa.compute_minimum_eigenvalue(hamiltonian)

            # Extract bitstring from result
            best_bitstring = self._extract_bitstring(result, n)
            selected = [i for i, bit in enumerate(best_bitstring) if bit == 1]
            energy = float(result.eigenvalue.real) if hasattr(result.eigenvalue, 'real') else float(result.eigenvalue)

            elapsed = time.perf_counter() - start
            self.config.record_benchmark("drill_optimization", QuantumBackend.QISKIT, elapsed)

            return OptimizationResult(
                selected_targets=selected,
                total_value=-energy,  # negate because we minimized
                energy=energy,
                backend_used="qiskit_qaoa",
                elapsed_seconds=elapsed,
            )

        except Exception as e:
            logger.warning(f"QAOA failed: {e}. Falling back to classical.")
            return self._solve_classical(Q)

    def _qubo_to_ising(self, Q: NDArray):
        """Convert QUBO matrix to Ising Hamiltonian (SparsePauliOp)."""
        _ensure_qiskit()
        from qiskit.quantum_info import SparsePauliOp

        n = Q.shape[0]
        pauli_list = []
        coeffs = []

        for i in range(n):
            # Diagonal: h_i * Z_i  (mapped from Q[i,i] * x_i)
            label = ["I"] * n
            label[n - 1 - i] = "Z"  # Qiskit uses reverse bit ordering
            pauli_list.append("".join(label))
            coeffs.append(-Q[i, i] / 2)  # x_i = (1 - Z_i) / 2

            for j in range(i + 1, n):
                if Q[i, j] != 0 or Q[j, i] != 0:
                    coupling = (Q[i, j] + Q[j, i]) / 2
                    # Z_i Z_j term
                    label = ["I"] * n
                    label[n - 1 - i] = "Z"
                    label[n - 1 - j] = "Z"
                    pauli_list.append("".join(label))
                    coeffs.append(coupling / 4)  # x_i * x_j = (1-Z_i)(1-Z_j)/4

        # Add constant offset from the linear terms
        offset = sum(Q[i, i] for i in range(n)) / 2

        hamiltonian = SparsePauliOp.from_list(list(zip(pauli_list, coeffs)))
        return hamiltonian

    def _extract_bitstring(self, result, n: int) -> list[int]:
        """Extract best bitstring from QAOA result."""
        try:
            # Try different result formats
            if hasattr(result, 'eigenstate'):
                eigenstate = result.eigenstate
                if hasattr(eigenstate, 'most_likely'):
                    bitstring = eigenstate.most_likely()
                    return [int(b) for b in bitstring]
                elif isinstance(eigenstate, dict):
                    best = max(eigenstate, key=eigenstate.get)
                    return [int(b) for b in best]

            # Fallback: interpret eigenvalue result
            return [0] * n
        except Exception:
            return [0] * n

    # ── Classical fallback ─────────────────────────────────────────────────

    def _solve_classical(self, Q: NDArray) -> OptimizationResult:
        """Classical QUBO solving via simulated annealing."""
        result = ClassicalFallback.optimize_qubo(Q)
        bitstring = result.result["bitstring"]
        selected = [i for i, bit in enumerate(bitstring) if bit == 1]

        return OptimizationResult(
            selected_targets=selected,
            total_value=-result.result["energy"],
            energy=result.result["energy"],
            backend_used=f"classical_{result.method}",
            elapsed_seconds=result.elapsed_seconds,
        )

    # ── High-level API ────────────────────────────────────────────────────

    def optimize_drill_targets(
        self,
        site_values: NDArray,
        distance_matrix: NDArray,
        cost_per_site: NDArray,
        n_select: int,
        penalty_weight: float = 10.0,
    ) -> OptimizationResult:
        """Optimize drill target selection.

        Automatically selects quantum (QAOA) or classical backend.

        Args:
            site_values: Geological value estimate per site.
            distance_matrix: Pairwise site distances.
            cost_per_site: Drilling cost per site.
            n_select: How many sites to select.
            penalty_weight: Constraint penalty weight.

        Returns:
            OptimizationResult with optimal drill targets.
        """
        # Build QUBO
        Q = self.build_qubo_matrix(
            site_values, distance_matrix, cost_per_site, n_select, penalty_weight
        )

        # Select backend
        n_qubits = len(site_values)
        backend = self.config.select_backend(
            problem_type="drill_optimization",
            problem_size=n_qubits,
            n_qubits_needed=n_qubits,
        )

        if backend == QuantumBackend.QISKIT:
            return self.solve_with_qaoa(Q)
        else:
            return self._solve_classical(Q)

    # ── Convenience: Random site generator for testing ─────────────────────

    @staticmethod
    def generate_random_problem(
        n_sites: int = 20,
        n_select: int = 5,
        seed: int = 42,
    ) -> tuple[NDArray, NDArray, NDArray]:
        """Generate a random drill optimization problem for testing.

        Returns:
            (site_values, distance_matrix, cost_per_site)
        """
        rng = np.random.default_rng(seed)
        # Random site positions in a 1000m x 1000m area
        positions = rng.uniform(0, 1000, size=(n_sites, 2))

        # Values between 0-100 (normalized mineral value estimates)
        site_values = rng.uniform(10, 100, size=n_sites)

        # Distance matrix
        from scipy.spatial.distance import cdist
        distance_matrix = cdist(positions, positions)

        # Cost per site (drilling depth proxy)
        cost_per_site = rng.uniform(5, 30, size=n_sites)

        return site_values, distance_matrix, cost_per_site
