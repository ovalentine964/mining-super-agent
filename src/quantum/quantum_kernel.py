"""
Quantum Kernel Methods for Mineral Classification.
Maps spectral/geological data into quantum feature space.
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

_pennylane = None
_qml = None


def _ensure_pennylane():
    global _pennylane, _qml
    if _pennylane is None:
        try:
            import pennylane as qml
            _pennylane = True
            _qml = qml
        except ImportError:
            raise ImportError("PennyLane not installed. Using classical fallback.")


@dataclass
class KernelResult:
    predictions: np.ndarray
    probabilities: np.ndarray | None
    backend_used: str
    elapsed_seconds: float
    accuracy: float | None
    kernel_matrix_train: np.ndarray | None = None


class QuantumKernelClassifier:
    """Quantum kernel SVM for mineral classification."""

    def __init__(self, config: QuantumConfig | None = None):
        self.config = config or DEFAULT_CONFIG

    def _build_quantum_device(self, n_wires: int):
        _ensure_pennylane()
        return _qml.device("default.qubit", wires=n_wires, shots=None)

    def _quantum_feature_map(self, x: np.ndarray, wires: list[int]):
        _ensure_pennylane()
        qml = _qml
        qml.AngleEmbedding(x[:len(wires)], wires=wires, rotation="Y")
        for layer in range(2):
            for i in range(len(wires) - 1):
                qml.CNOT(wires=[wires[i], wires[i + 1]])
            if len(wires) > 1:
                qml.CNOT(wires=[wires[-1], wires[0]])
            for i in range(len(wires)):
                qml.RY(np.pi * x[i % len(x)] * (layer + 1) / 2, wires=wires[i])

    def _build_kernel_circuit(self, n_features: int):
        _ensure_pennylane()
        qml = _qml
        n_wires = min(n_features, self.config.max_qubits)
        dev = self._build_quantum_device(n_wires)

        @qml.qnode(dev, interface="numpy")
        def kernel_circuit(x1, x2):
            self._quantum_feature_map(x1, wires=list(range(n_wires)))
            qml.adjoint(lambda: self._quantum_feature_map(x2, wires=list(range(n_wires))))()
            return qml.probs(wires=range(n_wires))[0]

        return kernel_circuit, n_wires

    def quantum_kernel_matrix(self, X1: np.ndarray, X2: np.ndarray) -> np.ndarray:
        nf = X1.shape[1]
        kernel_fn, n_wires = self._build_kernel_circuit(nf)
        n1, n2 = X1.shape[0], X2.shape[0]
        K = np.zeros((n1, n2))
        for i in range(n1):
            for j in range(n2):
                x1 = X1[i, :n_wires]
                x2 = X2[j, :n_wires]
                if len(x1) < n_wires: x1 = np.pad(x1, (0, n_wires - len(x1)))
                if len(x2) < n_wires: x2 = np.pad(x2, (0, n_wires - len(x2)))
                K[i, j] = kernel_fn(x1, x2)
        return K

    def classify(self, X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray) -> KernelResult:
        backend = self.config.select_backend("kernel_classification", X_train.shape[0], min(X_train.shape[1], self.config.max_qubits))
        if backend == QuantumBackend.PENNYLANE:
            return self._classify_quantum(X_train, y_train, X_test)
        return self._classify_classical(X_train, y_train, X_test)

    def _classify_quantum(self, X_train, y_train, X_test) -> KernelResult:
        start = time.perf_counter()
        try:
            _ensure_pennylane()
            from sklearn.svm import SVC
            K_train = self.quantum_kernel_matrix(X_train, X_train)
            K_test = self.quantum_kernel_matrix(X_test, X_train)
            svm = SVC(kernel="precomputed", C=1.0)
            svm.fit(K_train, y_train)
            predictions = svm.predict(K_test)
            elapsed = time.perf_counter() - start
            return KernelResult(predictions=predictions, probabilities=None, backend_used="pennylane_quantum_kernel", elapsed_seconds=elapsed, accuracy=None, kernel_matrix_train=K_train)
        except Exception as e:
            logger.warning("Quantum kernel failed: %s. Falling back.", e)
            return self._classify_classical(X_train, y_train, X_test)

    def _classify_classical(self, X_train, y_train, X_test) -> KernelResult:
        result = ClassicalFallback.kernel_classification(X_train, y_train, X_test)
        return KernelResult(predictions=result.result, probabilities=None, backend_used=f"classical_{result.method}", elapsed_seconds=result.elapsed_seconds, accuracy=result.accuracy)

    @staticmethod
    def create_gold_pyrite_features(spectral_data: np.ndarray, chemical_data: np.ndarray | None = None) -> np.ndarray:
        features = [spectral_data]
        if chemical_data is not None:
            features.append(chemical_data)
        combined = np.hstack(features)
        mins = combined.min(axis=0)
        maxs = combined.max(axis=0)
        ranges = maxs - mins
        ranges[ranges == 0] = 1
        return np.pi * (combined - mins) / ranges
