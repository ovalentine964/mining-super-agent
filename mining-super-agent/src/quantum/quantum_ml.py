"""
Quantum ML module — PennyLane quantum circuits for mining-specific ML tasks.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class QuantumMineralClassifier:
    """PennyLane quantum kernel for mineral classification."""

    def __init__(self, n_qubits: int = 4):
        self.n_qubits = n_qubits
        self._dev = None
        self._kernel_fn = None

    def _ensure_device(self):
        if self._dev is not None:
            return
        try:
            import pennylane as qml
            self._dev = qml.device("default.qubit", wires=self.n_qubits, shots=None)

            @qml.qnode(self._dev)
            def kernel(x1, x2):
                qml.AngleEmbedding(x1[:self.n_qubits], wires=range(self.n_qubits))
                qml.adjoint(qml.AngleEmbedding)(x2[:self.n_qubits], wires=range(self.n_qubits))
                return qml.probs(wires=range(self.n_qubits))

            self._kernel_fn = kernel
        except ImportError:
            raise ImportError("PennyLane not installed")

    def classify(
        self,
        data_point: List[float],
        reference_points: Dict[str, List[float]],
    ) -> Dict[str, Any]:
        """Classify a mineral using quantum kernel similarity."""
        self._ensure_device()
        import numpy as np

        padded = data_point[:self.n_qubits] + [0.0] * max(0, self.n_qubits - len(data_point))
        similarities = {}

        for label, ref in reference_points.items():
            padded_ref = ref[:self.n_qubits] + [0.0] * max(0, self.n_qubits - len(ref))
            kernel_val = self._kernel_fn(
                np.array(padded, dtype=np.float64),
                np.array(padded_ref, dtype=np.float64),
            )
            similarities[label] = float(kernel_val[0])

        total = sum(similarities.values())
        probabilities = {k: v / total for k, v in similarities.items()} if total > 0 else {k: 1.0 / len(similarities) for k in similarities}
        best_match = max(probabilities, key=probabilities.get)

        return {
            "success": True,
            "method": "pennylane_quantum_kernel",
            "n_qubits": self.n_qubits,
            "probabilities": {k: round(v, 4) for k, v in probabilities.items()},
            "best_match": best_match,
            "confidence": round(probabilities[best_match], 4),
        }


class QuantumDrillOptimizer:
    """Qiskit QAOA for drill target optimization."""

    def __init__(self, max_qubits: int = 16):
        self.max_qubits = max_qubits

    def optimize(
        self,
        cost_matrix: List[List[float]],
        num_select: int,
        p_layers: int = 2,
    ) -> Dict[str, Any]:
        """Run QAOA optimization for drill target selection."""
        n_items = len(cost_matrix)
        n_qubits = min(n_items, self.max_qubits)

        try:
            from qiskit import QuantumCircuit, transpile
            from qiskit_aer import AerSimulator

            qc = QuantumCircuit(n_qubits)
            for i in range(n_qubits):
                qc.h(i)

            for _ in range(p_layers):
                for i in range(n_qubits):
                    cost_i = cost_matrix[i][i] if i < len(cost_matrix) else 0
                    qc.rz(2 * cost_i, i)
                for i in range(min(n_qubits - 1, n_items - 1)):
                    for j in range(i + 1, min(n_qubits, n_items)):
                        if i < len(cost_matrix) and j < len(cost_matrix[i]):
                            coupling = cost_matrix[i][j]
                            if abs(coupling) > 1e-6:
                                qc.cx(i, j)
                                qc.rz(2 * coupling, j)
                                qc.cx(i, j)
                for i in range(n_qubits):
                    qc.rx(np.pi / 4, i)

            qc.measure_all()
            simulator = AerSimulator()
            compiled = transpile(qc, simulator)
            result = simulator.run(compiled, shots=2048).result()
            counts = result.get_counts()

            best_solution, best_score = None, -float('inf')
            for bitstring, count in counts.items():
                if bitstring.count("1") == num_select:
                    score = sum(cost_matrix[i][i] for i, b in enumerate(reversed(bitstring)) if b == "1" and i < len(cost_matrix))
                    if score > best_score:
                        best_score = score
                        best_solution = bitstring

            if best_solution:
                selected = [i for i, b in enumerate(reversed(best_solution)) if b == "1"]
            else:
                scores = sorted(enumerate(range(min(n_items, n_qubits))), key=lambda x: cost_matrix[x[1]][x[1]], reverse=True)
                selected = [s[1] for s in scores[:num_select]]

            return {
                "success": True, "method": "qiskit_qaoa", "n_qubits": n_qubits,
                "p_layers": p_layers, "selected_indices": selected,
                "total_score": round(best_score, 4), "shots": 2048,
            }
        except ImportError:
            return {"success": False, "error": "Qiskit not installed", "fallback": "Use greedy_optimization"}
        except Exception as e:
            return {"success": False, "error": str(e)}
