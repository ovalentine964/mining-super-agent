"""
Classical fallbacks for quantum operations.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    result: Any
    method: str
    elapsed_seconds: float
    accuracy: float | None = None


class ClassicalFallback:
    """Classical algorithms that serve as fallbacks for quantum operations."""

    @staticmethod
    def kernel_classification(X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray) -> BenchmarkResult:
        """Classical RBF kernel SVM classification."""
        start = time.perf_counter()
        from sklearn.svm import SVC
        from sklearn.model_selection import cross_val_score

        svm = SVC(kernel="rbf", C=1.0, gamma="scale")
        svm.fit(X_train, y_train)
        predictions = svm.predict(X_test)

        try:
            cv_scores = cross_val_score(svm, X_train, y_train, cv=min(5, len(np.unique(y_train))))
            accuracy = float(np.mean(cv_scores))
        except Exception:
            accuracy = None

        elapsed = time.perf_counter() - start
        return BenchmarkResult(result=predictions, method="rbf_svm", elapsed_seconds=elapsed, accuracy=accuracy)

    @staticmethod
    def optimize_qubo(Q: np.ndarray, n_restarts: int = 10) -> BenchmarkResult:
        """Classical QUBO optimization via simulated annealing."""
        start = time.perf_counter()
        n = Q.shape[0]

        def energy(x):
            return float(x @ Q @ x)

        def simulated_annealing(n_vars, n_iters=10000, temp_start=10.0, temp_end=0.01):
            rng = np.random.default_rng()
            x = rng.integers(0, 2, size=n_vars).astype(float)
            best_x = x.copy()
            best_e = energy(x)

            for i in range(n_iters):
                temp = temp_start * (temp_end / temp_start) ** (i / n_iters)
                neighbor = x.copy()
                flip = rng.integers(n_vars)
                neighbor[flip] = 1 - neighbor[flip]
                e_neighbor = energy(neighbor)
                delta = e_neighbor - energy(x)
                if delta < 0 or rng.random() < np.exp(-delta / max(temp, 1e-10)):
                    x = neighbor
                    if e_neighbor < best_e:
                        best_e = e_neighbor
                        best_x = x.copy()

            return best_x, best_e

        best_bitstring, best_energy = simulated_annealing(n)
        elapsed = time.perf_counter() - start

        return BenchmarkResult(
            result={"bitstring": best_bitstring.tolist(), "energy": best_energy},
            method="simulated_annealing", elapsed_seconds=elapsed,
        )
