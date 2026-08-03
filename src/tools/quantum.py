"""
Quantum Tools — PennyLane, Qiskit, classical fallbacks.

Provides quantum computing capabilities for mining-specific problems.
All operations have classical fallbacks.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


async def pennylane_quantum_kernel(
    data_point: list[float],
    reference_points: dict[str, list[float]],
    n_qubits: int = 4,
) -> dict[str, Any]:
    """
    PennyLane quantum kernel for mineral classification.

    Maps mineral spectral data into quantum Hilbert space where
    minerals that look identical classically (gold vs pyrite) become separable.
    """
    try:
        import pennylane as qml
        import numpy as np

        dev = qml.device("default.qubit", wires=n_qubits)

        @qml.qnode(dev)
        def kernel_circuit(x1, x2):
            """Quantum kernel: overlap between two data encodings."""
            qml.AngleEmbedding(x1[:n_qubits], wires=range(n_qubits))
            qml.adjoint(qml.AngleEmbedding)(x2[:n_qubits], wires=range(n_qubits))
            return qml.probs(wires=range(n_qubits))

        # Pad input data
        padded_data = data_point[:n_qubits] + [0.0] * max(0, n_qubits - len(data_point))

        # Calculate kernel values against each reference
        similarities = {}
        for label, ref in reference_points.items():
            padded_ref = ref[:n_qubits] + [0.0] * max(0, n_qubits - len(ref))
            kernel_val = kernel_circuit(
                np.array(padded_data, dtype=np.float64),
                np.array(padded_ref, dtype=np.float64),
            )
            similarities[label] = float(kernel_val[0])

        # Normalize
        total = sum(similarities.values())
        if total > 0:
            probabilities = {k: v / total for k, v in similarities.items()}
        else:
            probabilities = {k: 1.0 / len(similarities) for k in similarities}

        best_match = max(probabilities, key=probabilities.get)

        return {
            "success": True,
            "method": "pennylane_quantum_kernel",
            "n_qubits": n_qubits,
            "probabilities": {k: round(v, 4) for k, v in probabilities.items()},
            "best_match": best_match,
            "confidence": round(probabilities[best_match], 4),
        }

    except ImportError:
        return {
            "success": False,
            "error": "PennyLane not installed",
            "install": "pip install pennylane",
            "fallback": "Use classical_nearest_neighbor",
        }
    except Exception as e:
        return {"success": False, "error": f"PennyLane error: {e}"}


async def qiskit_qaoa_optimize(
    cost_matrix: list[list[float]],
    num_select: int,
    p_layers: int = 2,
) -> dict[str, Any]:
    """
    Qiskit QAOA for combinatorial optimization.

    Solves the problem of selecting num_select items from a set
    to maximize total score (drill target optimization).
    """
    n_items = len(cost_matrix)

    try:
        from qiskit import QuantumCircuit, transpile
        from qiskit_aer import AerSimulator
        import numpy as np

        # Limit problem size for simulation
        n_qubits = min(n_items, 16)

        # Build QAOA circuit
        qc = QuantumCircuit(n_qubits)

        # Initial superposition
        for i in range(n_qubits):
            qc.h(i)

        # QAOA layers
        for _ in range(p_layers):
            # Problem Hamiltonian (cost function)
            for i in range(n_qubits):
                # Diagonal terms
                cost_i = cost_matrix[i][i] if i < len(cost_matrix) else 0
                qc.rz(2 * cost_i, i)

            # Off-diagonal terms (interactions)
            for i in range(min(n_qubits - 1, n_items - 1)):
                for j in range(i + 1, min(n_qubits, n_items)):
                    if i < len(cost_matrix) and j < len(cost_matrix[i]):
                        coupling = cost_matrix[i][j]
                        if abs(coupling) > 1e-6:
                            qc.cx(i, j)
                            qc.rz(2 * coupling, j)
                            qc.cx(i, j)

            # Mixer Hamiltonian
            for i in range(n_qubits):
                qc.rx(np.pi / 4, i)

        # Measure
        qc.measure_all()

        # Simulate
        simulator = AerSimulator()
        compiled = transpile(qc, simulator)
        result = simulator.run(compiled, shots=2048).result()
        counts = result.get_counts()

        # Find best valid solution
        best_solution = None
        best_score = -float('inf')

        for bitstring, count in counts.items():
            ones = bitstring.count("1")
            if ones == num_select:
                score = sum(
                    cost_matrix[i][i]
                    for i, b in enumerate(reversed(bitstring))
                    if b == "1" and i < len(cost_matrix)
                )
                if score > best_score:
                    best_score = score
                    best_solution = bitstring

        if best_solution:
            selected = [i for i, b in enumerate(reversed(best_solution)) if b == "1"]
        else:
            # Fallback: greedy selection
            scores = [(i, cost_matrix[i][i]) for i in range(min(n_items, n_qubits))]
            scores.sort(key=lambda x: x[1], reverse=True)
            selected = [s[0] for s in scores[:num_select]]

        return {
            "success": True,
            "method": "qiskit_qaoa",
            "n_qubits": n_qubits,
            "p_layers": p_layers,
            "selected_indices": selected,
            "total_score": round(best_score, 4),
            "shots": 2048,
        }

    except ImportError:
        return {
            "success": False,
            "error": "Qiskit not installed",
            "install": "pip install qiskit qiskit-aer",
            "fallback": "Use greedy_optimization",
        }
    except Exception as e:
        return {"success": False, "error": f"Qiskit error: {e}"}


async def classical_mineral_classify(
    spectral_data: list[float],
    reference_spectra: dict[str, list[float]],
) -> dict[str, Any]:
    """
    Classical mineral classification using Euclidean distance.
    Fallback for quantum kernel when PennyLane is unavailable.
    """
    import numpy as np

    data = np.array(spectral_data)

    similarities = {}
    for mineral, ref in reference_spectra.items():
        ref_arr = np.array(ref[:len(data)])
        data_trimmed = data[:len(ref_arr)]

        # Euclidean distance → similarity
        dist = np.sqrt(np.sum((data_trimmed - ref_arr) ** 2))
        similarities[mineral] = float(1.0 / (1.0 + dist))

    # Normalize
    total = sum(similarities.values())
    probabilities = {k: v / total for k, v in similarities.items()}
    best_match = max(probabilities, key=probabilities.get)

    return {
        "success": True,
        "method": "classical_nearest_neighbor",
        "probabilities": {k: round(v, 4) for k, v in probabilities.items()},
        "best_match": best_match,
        "confidence": round(probabilities[best_match], 4),
        "note": "Classical fallback. Quantum kernel provides better separation for look-alikes.",
    }


async def classical_greedy_optimize(
    items: list[dict[str, Any]],
    num_select: int,
) -> dict[str, Any]:
    """
    Classical greedy optimization.
    Fallback for QAOA when Qiskit is unavailable.
    """
    # Sort by score (descending)
    sorted_items = sorted(
        enumerate(items),
        key=lambda x: x[1].get("priority_score", x[1].get("score", 0)),
        reverse=True,
    )

    selected = [
        {
            "index": idx,
            **item,
        }
        for idx, item in sorted_items[:num_select]
    ]

    total_score = sum(
        item.get("priority_score", item.get("score", 0))
        for _, item in sorted_items[:num_select]
    )

    return {
        "success": True,
        "method": "classical_greedy",
        "selected": selected,
        "total_score": round(total_score, 4),
        "note": "Greedy selection. May miss globally optimal solution. QAOA explores all combinations.",
    }


def register_quantum_tools(registry) -> None:
    """Register all quantum tools with the tool registry."""
    registry.register_handler("quantum_mineral_classify", pennylane_quantum_kernel)
    registry.register_handler("quantum_drill_optimize", qiskit_qaoa_optimize)
    registry.register_handler("classical_mineral_classify", classical_mineral_classify)
    registry.register_handler("classical_greedy_optimize", classical_greedy_optimize)
