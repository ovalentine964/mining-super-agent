"""
Quantum Chemistry Simulation for Mineral Formation.

Uses Qiskit VQE (Variational Quantum Eigensolver) to simulate molecular
energies and understand mineral co-location patterns. Falls back to
classical pairwise potential estimation.
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

# ── Mineral database ──────────────────────────────────────────────────────

MINERAL_FORMULAS = {
    "gold": {"atoms": [79], "formula": "Au"},
    "pyrite": {"atoms": [26, 16, 16], "formula": "FeS₂"},
    "chalcopyrite": {"atoms": [29, 26, 16, 16], "formula": "CuFeS₂"},
    "galena": {"atoms": [82, 16], "formula": "PbS"},
    "magnetite": {"atoms": [26, 26, 26, 8, 8, 8, 8], "formula": "Fe₃O₄"},
    "hematite": {"atoms": [26, 26, 8, 8, 8], "formula": "Fe₂O₃"},
    "quartz": {"atoms": [14, 8, 8], "formula": "SiO₂"},
    "calcite": {"atoms": [20, 6, 8, 8, 8], "formula": "CaCO₃"},
    "copper": {"atoms": [29], "formula": "Cu"},
    "malachite": {"atoms": [29, 29, 6, 8, 8, 8, 8, 8], "formula": "Cu₂CO₃(OH)₂"},
}


@dataclass
class ChemistryResult:
    """Result from quantum or classical chemistry simulation."""
    energy_ev: float
    formation_energy_ev: float | None
    backend_used: str
    elapsed_seconds: float
    mineral: str
    atom_count: int
    details: dict[str, Any] | None = None


class QuantumChemistrySimulator:
    """Quantum chemistry simulation for mineral formation energy.

    Uses VQE to find ground-state energy of mineral molecules.
    Understanding formation energies helps predict:
    - Which minerals co-occur (similar formation conditions)
    - Geological history of a site
    - Probability of finding specific minerals together

    Falls back to classical Lennard-Jones potential estimation.
    """

    def __init__(self, config: QuantumConfig | None = None):
        self.config = config or DEFAULT_CONFIG

    # ── VQE solver ────────────────────────────────────────────────────────

    def simulate_mineral(
        self,
        mineral: str,
        coordinates: NDArray | None = None,
    ) -> ChemistryResult:
        """Simulate molecular energy of a mineral.

        Args:
            mineral: Mineral name (must be in MINERAL_FORMULAS).
            coordinates: Optional (n_atoms, 3) positions. If None, generates default.

        Returns:
            ChemistryResult with energy and simulation details.
        """
        if mineral.lower() not in MINERAL_FORMULAS:
            raise ValueError(
                f"Unknown mineral '{mineral}'. Available: {list(MINERAL_FORMULAS.keys())}"
            )

        mineral_data = MINERAL_FORMULAS[mineral.lower()]
        atomic_numbers = mineral_data["atoms"]

        if coordinates is None:
            coordinates = self._generate_default_geometry(atomic_numbers)

        backend = self.config.select_backend(
            problem_type="molecular_simulation",
            problem_size=len(atomic_numbers),
            n_qubits_needed=len(atomic_numbers) * 2,
        )

        if backend == QuantumBackend.QISKIT:
            return self._simulate_vqe(mineral, atomic_numbers, coordinates)
        else:
            return self._simulate_classical(mineral, atomic_numbers, coordinates)

    def _simulate_vqe(
        self,
        mineral: str,
        atomic_numbers: list[int],
        coordinates: NDArray,
    ) -> ChemistryResult:
        """VQE molecular simulation using Qiskit."""
        start = time.perf_counter()
        try:
            from qiskit.quantum_info import SparsePauliOp
            from qiskit_algorithms import VQE as QiskitVQE
            from qiskit_algorithms.optimizers import SPSA
            from qiskit_aer import AerSimulator
            from qiskit.circuit.library import EfficientSU2
            from qiskit.primitives import BackendEstimator

            n_atoms = len(atomic_numbers)
            n_qubits = min(n_atoms * 2, self.config.max_qubits)

            # Build molecular Hamiltonian (simplified)
            hamiltonian = self._build_molecular_hamiltonian(atomic_numbers, coordinates, n_qubits)

            # VQE setup
            backend = AerSimulator()
            estimator = BackendEstimator(backend=backend)
            ansatz = EfficientSU2(num_qubits=n_qubits, reps=2)
            optimizer = SPSA(maxiter=200)

            vqe = QiskitVQE(
                estimator=estimator,
                ansatz=ansatz,
                optimizer=optimizer,
            )

            result = vqe.compute_minimum_eigenvalue(hamiltonian)
            energy = float(result.eigenvalue.real) if hasattr(result.eigenvalue, 'real') else float(result.eigenvalue)

            elapsed = time.perf_counter() - start
            self.config.record_benchmark("molecular_simulation", QuantumBackend.QISKIT, elapsed)

            return ChemistryResult(
                energy_ev=energy,
                formation_energy_ev=energy,  # simplified
                backend_used="qiskit_vqe",
                elapsed_seconds=elapsed,
                mineral=mineral,
                atom_count=n_atoms,
                details={"n_qubits": n_qubits, "optimizer": "SPSA"},
            )

        except Exception as e:
            logger.warning(f"VQE failed: {e}. Falling back to classical.")
            return self._simulate_classical(mineral, atomic_numbers, coordinates)

    def _build_molecular_hamiltonian(
        self,
        atomic_numbers: list[int],
        coordinates: NDArray,
        n_qubits: int,
    ):
        """Build simplified molecular Hamiltonian for VQE.

        Uses a tight-binding-like model mapped to qubits.
        """
        from qiskit.quantum_info import SparsePauliOp

        pauli_list = []
        coeffs = []

        n_atoms = len(atomic_numbers)

        # On-site energies (diagonal)
        for i in range(min(n_atoms, n_qubits)):
            label = ["I"] * n_qubits
            label[n_qubits - 1 - i] = "Z"
            pauli_list.append("".join(label))
            # Approximate on-site energy from atomic number
            coeffs.append(-float(atomic_numbers[i]) * 0.5)

        # Hopping terms (off-diagonal)
        for i in range(min(n_atoms, n_qubits)):
            for j in range(i + 1, min(n_atoms, n_qubits)):
                dist = np.linalg.norm(coordinates[i] - coordinates[j])
                if dist > 0:
                    hopping = -1.0 / dist  # simplified hopping integral

                    # XX term
                    label = ["I"] * n_qubits
                    label[n_qubits - 1 - i] = "X"
                    label[n_qubits - 1 - j] = "X"
                    pauli_list.append("".join(label))
                    coeffs.append(hopping)

                    # YY term
                    label = ["I"] * n_qubits
                    label[n_qubits - 1 - i] = "Y"
                    label[n_qubits - 1 - j] = "Y"
                    pauli_list.append("".join(label))
                    coeffs.append(hopping)

        if not pauli_list:
            # Degenerate case: single atom
            label = ["I"] * n_qubits
            label[0] = "Z"
            pauli_list.append("".join(label))
            coeffs.append(-float(atomic_numbers[0]))

        return SparsePauliOp.from_list(list(zip(pauli_list, coeffs)))

    # ── Classical fallback ─────────────────────────────────────────────────

    def _simulate_classical(
        self,
        mineral: str,
        atomic_numbers: list[int],
        coordinates: NDArray,
    ) -> ChemistryResult:
        """Classical molecular energy estimation using Lennard-Jones potentials."""
        result = ClassicalFallback.molecular_energy(atomic_numbers, coordinates)

        return ChemistryResult(
            energy_ev=result.result,
            formation_energy_ev=result.result,
            backend_used=f"classical_{result.method}",
            elapsed_seconds=result.elapsed_seconds,
            mineral=mineral,
            atom_count=len(atomic_numbers),
        )

    # ── Geometry generation ────────────────────────────────────────────────

    @staticmethod
    def _generate_default_geometry(atomic_numbers: list[int]) -> NDArray:
        """Generate approximate molecular geometry.

        Uses simple bond-length estimates to place atoms.
        """
        n = len(atomic_numbers)
        coords = np.zeros((n, 3))

        if n == 1:
            return coords

        # Place atoms in a chain with approximate bond lengths
        bond_length = 2.0  # Angstroms (typical mineral bond)
        for i in range(1, n):
            angle = 2 * np.pi * i / n  # spread in a circle for > 2 atoms
            if n == 2:
                coords[i] = [bond_length, 0, 0]
            else:
                r = bond_length
                coords[i] = [
                    r * np.cos(angle),
                    r * np.sin(angle),
                    0,
                ]

        return coords

    # ── Batch simulation ──────────────────────────────────────────────────

    def simulate_mineral_pair(
        self, mineral1: str, mineral2: str, separation: float = 3.0
    ) -> dict[str, Any]:
        """Simulate two minerals at a given separation.

        This helps understand mineral co-location: if the combined
        energy is lower than sum of separate energies, they're likely
        to co-occur in the same geological formation.
        """
        data1 = MINERAL_FORMULAS.get(mineral1.lower())
        data2 = MINERAL_FORMULAS.get(mineral2.lower())
        if not data1 or not data2:
            raise ValueError(f"Unknown mineral. Available: {list(MINERAL_FORMULAS.keys())}")

        # Simulate each mineral separately
        result1 = self.simulate_mineral(mineral1)
        result2 = self.simulate_mineral(mineral2)

        # Simulate combined system
        combined_atoms = data1["atoms"] + data2["atoms"]
        coords1 = self._generate_default_geometry(data1["atoms"])
        coords2 = self._generate_default_geometry(data2["atoms"])
        coords2 += np.array([separation, 0, 0])  # offset second mineral
        combined_coords = np.vstack([coords1, coords2])

        combined_result = self._simulate_classical(
            f"{mineral1}+{mineral2}", combined_atoms, combined_coords
        )

        binding_energy = combined_result.energy_ev - (result1.energy_ev + result2.energy_ev)

        return {
            "mineral1": mineral1,
            "mineral2": mineral2,
            "energy1_ev": result1.energy_ev,
            "energy2_ev": result2.energy_ev,
            "combined_energy_ev": combined_result.energy_ev,
            "binding_energy_ev": binding_energy,
            "likely_co_occur": bool(binding_energy < 0),
            "separation_angstroms": separation,
        }

    def get_common_associations(self, mineral: str) -> list[dict[str, Any]]:
        """Find minerals commonly associated with the given mineral.

        Based on formation energy analysis.
        """
        if mineral.lower() not in MINERAL_FORMULAS:
            return []

        associations = []
        for other_mineral in MINERAL_FORMULAS:
            if other_mineral == mineral.lower():
                continue
            try:
                pair_result = self.simulate_mineral_pair(mineral, other_mineral)
                associations.append({
                    "mineral": other_mineral,
                    "formula": MINERAL_FORMULAS[other_mineral]["formula"],
                    "binding_energy_ev": pair_result["binding_energy_ev"],
                    "likely_co_occur": pair_result["likely_co_occur"],
                })
            except Exception:
                continue

        # Sort by binding energy (most negative = most likely to co-occur)
        associations.sort(key=lambda x: x["binding_energy_ev"])
        return associations
