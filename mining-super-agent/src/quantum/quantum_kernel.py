"""
Quantum Kernel Methods for Mineral Classification.

Maps spectral/geological data into quantum feature space where gold and pyrite
become separable. Uses PennyLane quantum feature maps with classical fallback.
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

# Lazy imports — only loaded when quantum backend is selected
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
    """Result from quantum or classical kernel classification."""
    predictions: NDArray
    probabilities: NDArray | None
    backend_used: str
    elapsed_seconds: float
    accuracy: float | None
    kernel_matrix_train: NDArray | None = None


class QuantumKernelClassifier:
    """Quantum kernel SVM for mineral classification.

    Maps input features into quantum Hilbert space using parameterized
    quantum circuits. In this space, minerals with similar spectral
    signatures cluster together, enabling gold-vs-pyrite separation
    that classical methods cannot achieve.

    Architecture:
        1. Encode features → quantum state (AngleEmbedding / StronglyEntanglingLayers)
        2. Compute kernel matrix via overlap measurements
        3. Classical SVM on quantum kernel matrix

    Falls back to classical RBF kernel SVM when quantum unavailable.
    """

    def __init__(self, config: QuantumConfig | None = None):
        self.config = config or DEFAULT_CONFIG
        self._kernel_matrix_cache: NDArray | None = None
        self._trained = False
        self._backend: QuantumBackend | None = None

    # ── Quantum feature map ───────────────────────────────────────────────

    def _build_quantum_device(self, n_wires: int):
        """Create PennyLane quantum device."""
        _ensure_pennylane()
        return _qml.device("default.qubit", wires=n_wires, shots=None)

    def _quantum_feature_map(self, x: NDArray, wires: list[int]):
        """Encode classical data into quantum state.

        Uses angle embedding + entangling layers for expressive feature map.
        This is where the "quantum advantage" lives — the feature space
        has exponentially more dimensions than classical.
        """
        _ensure_pennylane()
        qml = _qml

        # Angle embedding: encode each feature as a rotation
        qml.AngleEmbedding(x[:len(wires)], wires=wires, rotation="Y")

        # Entangling layers for expressivity
        n_layers = 2
        for layer in range(n_layers):
            for i in range(len(wires) - 1):
                qml.CNOT(wires=[wires[i], wires[i + 1]])
            if len(wires) > 1:
                qml.CNOT(wires=[wires[-1], wires[0]])  # circular entanglement
            # Additional rotations for each layer
            for i in range(len(wires)):
                qml.RY(np.pi * x[i % len(x)] * (layer + 1) / n_layers, wires=wires[i])

    def _build_kernel_circuit(self, n_features: int):
        """Build the quantum kernel evaluation circuit."""
        _ensure_pennylane()
        qml = _qml
        n_wires = min(n_features, self.config.max_qubits)
        dev = self._build_quantum_device(n_wires)

        @qml.qnode(dev, interface="numpy")
        def kernel_circuit(x1: NDArray, x2: NDArray) -> float:
            """Compute quantum kernel k(x1, x2) = |<φ(x1)|φ(x2)>|².

            Encodes both inputs, then measures overlap.
            """
            # Encode x1
            self._quantum_feature_map(x1, wires=list(range(n_wires)))
            # Adjoint encode x2 (reverse the encoding)
            qml.adjoint(lambda: self._quantum_feature_map(x2, wires=list(range(n_wires))))()
            # Measure probability of all-zero state (= overlap)
            return qml.probs(wires=range(n_wires))[0]

        return kernel_circuit, n_wires

    def quantum_kernel_matrix(
        self, X1: NDArray, X2: NDArray, n_features: int | None = None
    ) -> NDArray:
        """Compute quantum kernel matrix K[i,j] = k(X1[i], X2[j]).

        This is the core quantum operation — maps pairs of data points
        into quantum space and measures their similarity.
        """
        _ensure_pennylane()
        nf = n_features or X1.shape[1]
        kernel_fn, n_wires = self._build_kernel_circuit(nf)

        n1, n2 = X1.shape[0], X2.shape[0]
        K = np.zeros((n1, n2))

        for i in range(n1):
            for j in range(n2):
                # Truncate features to fit qubits
                x1 = X1[i, :n_wires]
                x2 = X2[j, :n_wires]
                # Pad if needed
                if len(x1) < n_wires:
                    x1 = np.pad(x1, (0, n_wires - len(x1)))
                if len(x2) < n_wires:
                    x2 = np.pad(x2, (0, n_wires - len(x2)))
                K[i, j] = kernel_fn(x1, x2)

        return K

    # ── High-level classification API ─────────────────────────────────────

    def classify(
        self,
        X_train: NDArray,
        y_train: NDArray,
        X_test: NDArray,
    ) -> KernelResult:
        """Classify minerals using quantum (or classical) kernel methods.

        Automatically selects quantum or classical backend based on config.

        Args:
            X_train: Training features (n_samples, n_features).
            y_train: Training labels.
            X_test: Test features.

        Returns:
            KernelResult with predictions, timing, and backend info.
        """
        backend = self.config.select_backend(
            problem_type="kernel_classification",
            problem_size=X_train.shape[0],
            n_qubits_needed=min(X_train.shape[1], self.config.max_qubits),
        )
        self._backend = backend

        if backend == QuantumBackend.PENNYLANE:
            return self._classify_quantum(X_train, y_train, X_test)
        else:
            return self._classify_classical(X_train, y_train, X_test)

    def _classify_quantum(
        self, X_train: NDArray, y_train: NDArray, X_test: NDArray
    ) -> KernelResult:
        """Quantum kernel classification."""
        start = time.perf_counter()
        try:
            _ensure_pennylane()
            from sklearn.svm import SVC
            from sklearn.model_selection import cross_val_score

            # Compute quantum kernel matrices
            logger.info("Computing quantum kernel matrix (train x train)...")
            K_train = self.quantum_kernel_matrix(X_train, X_train)
            logger.info("Computing quantum kernel matrix (test x train)...")
            K_test = self.quantum_kernel_matrix(X_test, X_train)

            # SVM with precomputed quantum kernel
            svm = SVC(kernel="precomputed", C=1.0)
            svm.fit(K_train, y_train)
            predictions = svm.predict(K_test)

            # Cross-val on training kernel
            try:
                cv_scores = cross_val_score(svm, K_train, y_train, cv=min(5, len(np.unique(y_train))))
                accuracy = float(np.mean(cv_scores))
            except Exception:
                accuracy = None

            elapsed = time.perf_counter() - start
            self.config.record_benchmark("kernel_classification", QuantumBackend.PENNYLANE, elapsed, accuracy)

            return KernelResult(
                predictions=predictions,
                probabilities=None,
                backend_used="pennylane_quantum_kernel",
                elapsed_seconds=elapsed,
                accuracy=accuracy,
                kernel_matrix_train=K_train,
            )

        except Exception as e:
            logger.warning(f"Quantum kernel failed: {e}. Falling back to classical.")
            return self._classify_classical(X_train, y_train, X_test)

    def _classify_classical(
        self, X_train: NDArray, y_train: NDArray, X_test: NDArray
    ) -> KernelResult:
        """Classical kernel classification fallback."""
        result = ClassicalFallback.kernel_classification(X_train, y_train, X_test)
        self.config.record_benchmark(
            "kernel_classification", QuantumBackend.CLASSICAL,
            result.elapsed_seconds, result.accuracy,
        )
        return KernelResult(
            predictions=result.result,
            probabilities=None,
            backend_used=f"classical_{result.method}",
            elapsed_seconds=result.elapsed_seconds,
            accuracy=result.accuracy,
        )

    # ── Gold vs Pyrite specialist ──────────────────────────────────────────

    @staticmethod
    def create_gold_pyrite_features(
        spectral_data: NDArray,
        chemical_data: NDArray | None = None,
        structural_data: NDArray | None = None,
    ) -> NDArray:
        """Create feature vectors for gold vs pyrite classification.

        Combines spectral (XRF/optical), chemical, and structural features
        into a single feature matrix optimized for quantum kernel mapping.

        Args:
            spectral_data: (n_samples, n_bands) spectral measurements.
            chemical_data: Optional (n_samples, n_elements) chemical composition.
            structural_data: Optional (n_samples, n_features) crystal structure data.

        Returns:
            Combined feature matrix (n_samples, total_features).
        """
        features = [spectral_data]
        if chemical_data is not None:
            features.append(chemical_data)
        if structural_data is not None:
            features.append(structural_data)

        combined = np.hstack(features)

        # Normalize to [0, π] range (best for quantum angle embedding)
        mins = combined.min(axis=0)
        maxs = combined.max(axis=0)
        ranges = maxs - mins
        ranges[ranges == 0] = 1  # avoid division by zero
        normalized = np.pi * (combined - mins) / ranges

        return normalized
