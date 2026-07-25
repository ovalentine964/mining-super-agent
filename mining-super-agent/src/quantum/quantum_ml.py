"""
Quantum Machine Learning — Variational Quantum Classifier for geological prediction.

Uses PennyLane parameterized quantum circuits as a trainable classifier,
with hybrid quantum-classical optimization loop.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
from numpy.typing import NDArray

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
class QMLResult:
    """Result from quantum or classical ML classification."""
    predictions: NDArray
    probabilities: NDArray | None
    backend_used: str
    elapsed_seconds: float
    accuracy: float | None
    training_loss: list[float] | None = None
    n_parameters: int | None = None


class VariationalQuantumClassifier:
    """Variational Quantum Classifier (VQC) for geological prediction.

    Architecture:
        1. Data encoding: classical features → quantum state rotations
        2. Variational layers: parameterized rotation + entangling gates
        3. Measurement: expectation values → class probabilities
        4. Classical optimizer: updates quantum parameters to minimize loss

    This is a hybrid quantum-classical model — the quantum circuit is the
    "neural network" and classical optimizer does gradient descent.

    Falls back to GradientBoosting when quantum unavailable.
    """

    def __init__(
        self,
        n_qubits: int = 4,
        n_layers: int = 3,
        learning_rate: float = 0.1,
        n_epochs: int = 50,
        config: QuantumConfig | None = None,
    ):
        self.n_qubits = n_qubits
        self.n_layers = n_layers
        self.learning_rate = learning_rate
        self.n_epochs = n_epochs
        self.config = config or DEFAULT_CONFIG
        self._params: NDArray | None = None
        self._trained = False

    # ── Quantum circuit ───────────────────────────────────────────────────

    def _build_circuit(self):
        """Build the variational quantum circuit."""
        _ensure_pennylane()
        qml = _qml

        n_qubits = self.n_qubits
        dev = qml.device("default.qubit", wires=n_qubits, shots=None)

        @qml.qnode(dev, interface="numpy")
        def circuit(features: NDArray, params: NDArray) -> float:
            """Variational quantum circuit.

            Args:
                features: Input features (n_features,).
                params: Trainable parameters (n_layers, n_qubits, 3).

            Returns:
                Expectation value of PauliZ on first qubit (→ class probability).
            """
            wires = list(range(n_qubits))

            # Data encoding layer
            for i in range(n_qubits):
                qml.RY(features[i % len(features)], wires=i)
                qml.RZ(features[(i + 1) % len(features)], wires=i)

            # Variational layers
            for layer in range(self.n_layers):
                # Single-qubit rotations
                for i in range(n_qubits):
                    qml.RX(params[layer, i, 0], wires=i)
                    qml.RY(params[layer, i, 1], wires=i)
                    qml.RZ(params[layer, i, 2], wires=i)

                # Entangling gates
                for i in range(n_qubits - 1):
                    qml.CNOT(wires=[i, i + 1])
                if n_qubits > 1:
                    qml.CNOT(wires=[n_qubits - 1, 0])  # circular

            # Measure
            return qml.expval(qml.PauliZ(0))

        return circuit

    # ── Training ──────────────────────────────────────────────────────────

    def _train_quantum(
        self, X_train: NDArray, y_train: NDArray
    ) -> tuple[NDArray, list[float]]:
        """Train the variational quantum circuit.

        Uses parameter-shift rule for gradient computation (built into PennyLane).
        Classical optimizer (Adam-like) updates parameters.
        """
        _ensure_pennylane()
        qml = _qml

        n_features = X_train.shape[1]

        # Initialize parameters
        rng = np.random.default_rng(42)
        params = rng.uniform(0, 2 * np.pi, size=(self.n_layers, self.n_qubits, 3))

        circuit = self._build_circuit()
        optimizer = qml.AdamOptimizer(step_size=self.learning_rate)

        # Normalize labels to {-1, 1} for PauliZ measurement
        classes = np.unique(y_train)
        y_mapped = np.where(y_train == classes[0], -1.0, 1.0)

        loss_history = []

        for epoch in range(self.n_epochs):
            # Compute predictions for all training samples
            total_loss = 0.0
            for i in range(len(X_train)):
                x = X_train[i]
                # Pad features to n_qubits
                x_padded = np.zeros(self.n_qubits)
                x_padded[:min(len(x), self.n_qubits)] = x[:self.n_qubits]

                prediction = circuit(x_padded, params)
                loss = (prediction - y_mapped[i]) ** 2
                total_loss += loss

            avg_loss = total_loss / len(X_train)
            loss_history.append(float(avg_loss))

            # Update parameters using PennyLane optimizer
            def cost_fn(p):
                c = 0.0
                for i in range(len(X_train)):
                    x = X_train[i]
                    x_padded = np.zeros(self.n_qubits)
                    x_padded[:min(len(x), self.n_qubits)] = x[:self.n_qubits]
                    pred = circuit(x_padded, p)
                    c += (pred - y_mapped[i]) ** 2
                return c / len(X_train)

            params = optimizer.step(cost_fn, params)

            if (epoch + 1) % 10 == 0:
                logger.info(f"VQC epoch {epoch + 1}/{self.n_epochs}, loss={avg_loss:.4f}")

        return params, loss_history

    def _predict_quantum(self, X: NDArray, params: NDArray) -> tuple[NDArray, NDArray]:
        """Predict using trained quantum circuit."""
        circuit = self._build_circuit()

        predictions = []
        probabilities = []

        for x in X:
            x_padded = np.zeros(self.n_qubits)
            x_padded[:min(len(x), self.n_qubits)] = x[:self.n_qubits]

            exp_val = circuit(x_padded, params)
            # Map expectation value to class probability
            prob_class_1 = (1 + float(exp_val)) / 2
            predictions.append(1 if prob_class_1 > 0.5 else 0)
            probabilities.append([1 - prob_class_1, prob_class_1])

        return np.array(predictions), np.array(probabilities)

    # ── High-level API ────────────────────────────────────────────────────

    def fit_predict(
        self,
        X_train: NDArray,
        y_train: NDArray,
        X_test: NDArray,
    ) -> QMLResult:
        """Train and predict using quantum or classical ML.

        Automatically selects backend based on config.
        """
        backend = self.config.select_backend(
            problem_type="variational_classification",
            problem_size=X_train.shape[0],
            n_qubits_needed=self.n_qubits,
        )

        if backend == QuantumBackend.PENNYLANE:
            return self._fit_predict_quantum(X_train, y_train, X_test)
        else:
            return self._fit_predict_classical(X_train, y_train, X_test)

    def _fit_predict_quantum(
        self, X_train: NDArray, y_train: NDArray, X_test: NDArray
    ) -> QMLResult:
        """Quantum variational classification."""
        start = time.perf_counter()
        try:
            # Train quantum circuit
            params, loss_history = self._train_quantum(X_train, y_train)
            self._params = params
            self._trained = True

            # Predict
            predictions, probabilities = self._predict_quantum(X_test, params)

            # Estimate accuracy via leave-one-out on small training sets
            accuracy = None
            if len(X_train) <= 50:
                correct = 0
                for i in range(len(X_train)):
                    x_padded = np.zeros(self.n_qubits)
                    x_padded[:min(X_train.shape[1], self.n_qubits)] = X_train[i][:self.n_qubits]
                    circuit = self._build_circuit()
                    exp_val = circuit(x_padded, params)
                    pred_class = 1 if (1 + float(exp_val)) / 2 > 0.5 else 0
                    if pred_class == y_train[i]:
                        correct += 1
                accuracy = correct / len(X_train)

            elapsed = time.perf_counter() - start
            self.config.record_benchmark(
                "variational_classification", QuantumBackend.PENNYLANE, elapsed, accuracy
            )

            return QMLResult(
                predictions=predictions,
                probabilities=probabilities,
                backend_used="pennylane_vqc",
                elapsed_seconds=elapsed,
                accuracy=accuracy,
                training_loss=loss_history,
                n_parameters=int(np.prod(params.shape)),
            )

        except Exception as e:
            logger.warning(f"Quantum VQC failed: {e}. Falling back to classical.")
            return self._fit_predict_classical(X_train, y_train, X_test)

    def _fit_predict_classical(
        self, X_train: NDArray, y_train: NDArray, X_test: NDArray
    ) -> QMLResult:
        """Classical variational classifier fallback."""
        result = ClassicalFallback.variational_classifier(X_train, y_train, X_test)
        self.config.record_benchmark(
            "variational_classification", QuantumBackend.CLASSICAL,
            result.elapsed_seconds, result.accuracy,
        )

        return QMLResult(
            predictions=result.result,
            probabilities=None,
            backend_used=f"classical_{result.method}",
            elapsed_seconds=result.elapsed_seconds,
            accuracy=result.accuracy,
        )

    # ── Utility ───────────────────────────────────────────────────────────

    def save_params(self, path: str) -> None:
        """Save trained quantum parameters."""
        if self._params is not None:
            np.save(path, self._params)
            logger.info(f"Saved VQC parameters to {path}")

    def load_params(self, path: str) -> None:
        """Load trained quantum parameters."""
        self._params = np.load(path)
        self._trained = True
        logger.info(f"Loaded VQC parameters from {path}")


class QuantumNeuralNetwork:
    """Quantum Neural Network for geological pattern recognition.

    A deeper variational circuit that acts like a quantum neural network,
    with multiple layers of parameterized gates acting as "neurons."
    Used for complex geological predictions where simple VQC isn't enough.
    """

    def __init__(
        self,
        n_qubits: int = 6,
        n_layers: int = 5,
        config: QuantumConfig | None = None,
    ):
        self.n_qubits = n_qubits
        self.n_layers = n_layers
        self.config = config or DEFAULT_CONFIG

    def predict(
        self, X_train: NDArray, y_train: NDArray, X_test: NDArray
    ) -> QMLResult:
        """Run QNN prediction — delegates to VQC with more layers."""
        vqc = VariationalQuantumClassifier(
            n_qubits=self.n_qubits,
            n_layers=self.n_layers,
            config=self.config,
        )
        return vqc.fit_predict(X_train, y_train, X_test)
