"""
Quantum vs classical benchmarks for mining operations.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List

import numpy as np

from .quantum_config import QuantumConfig, QuantumBackend, DEFAULT_CONFIG
from .quantum_kernel import QuantumKernelClassifier
from .qaoa_optimizer import QAOAOptimizer
from .classical_fallback import ClassicalFallback

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    problem_type: str
    problem_size: int
    quantum_time: float | None
    classical_time: float
    quantum_accuracy: float | None
    classical_accuracy: float | None
    winner: str  # "quantum", "classical", or "tie"
    speedup: float | None


def benchmark_kernel_classification(n_samples_list: List[int] = None, n_features: int = 4) -> List[BenchmarkResult]:
    """Benchmark quantum vs classical kernel classification."""
    if n_samples_list is None:
        n_samples_list = [10, 20, 50]

    results = []
    quantum_classifier = QuantumKernelClassifier()

    for n_samples in n_samples_list:
        rng = np.random.default_rng(42)
        X_train = rng.random((n_samples, n_features))
        y_train = rng.integers(0, 2, size=n_samples)
        X_test = rng.random((min(10, n_samples), n_features))

        # Classical
        classical = ClassicalFallback.kernel_classification(X_train, y_train, X_test)

        # Quantum (if available)
        quantum_time = None
        quantum_acc = None
        try:
            qr = quantum_classifier._classify_quantum(X_train, y_train, X_test)
            quantum_time = qr.elapsed_seconds
            quantum_acc = qr.accuracy
        except Exception:
            pass

        winner = "classical"
        speedup = None
        if quantum_time is not None:
            speedup = classical.elapsed_seconds / quantum_time if quantum_time > 0 else None
            if quantum_acc and classical.accuracy and quantum_acc > classical.accuracy:
                winner = "quantum"

        results.append(BenchmarkResult(
            problem_type="kernel_classification", problem_size=n_samples,
            quantum_time=quantum_time, classical_time=classical.elapsed_seconds,
            quantum_accuracy=quantum_acc, classical_accuracy=classical.accuracy,
            winner=winner, speedup=speedup,
        ))

    return results


def benchmark_qubo_optimization(n_sites_list: List[int] = None) -> List[BenchmarkResult]:
    """Benchmark quantum vs classical QUBO optimization."""
    if n_sites_list is None:
        n_sites_list = [8, 12, 16]

    results = []
    qaoa = QAOAOptimizer()

    for n_sites in n_sites_list:
        site_values, dist_matrix, costs = QAOAOptimizer.generate_random_problem(n_sites, n_select=n_sites // 4)
        Q = QAOAOptimizer.build_qubo_matrix(site_values, dist_matrix, costs, n_sites // 4)

        # Classical
        classical = ClassicalFallback.optimize_qubo(Q)

        # Quantum (if available)
        quantum_time = None
        try:
            qr = qaoa.solve_with_qaoa(Q)
            quantum_time = qr.elapsed_seconds
        except Exception:
            pass

        speedup = classical.elapsed_seconds / quantum_time if quantum_time and quantum_time > 0 else None

        results.append(BenchmarkResult(
            problem_type="qubo_optimization", problem_size=n_sites,
            quantum_time=quantum_time, classical_time=classical.elapsed_seconds,
            quantum_accuracy=None, classical_accuracy=None,
            winner="quantum" if quantum_time and quantum_time < classical.elapsed_seconds else "classical",
            speedup=speedup,
        ))

    return results


def run_full_benchmark() -> Dict[str, Any]:
    """Run all benchmarks and return results."""
    kernel_results = benchmark_kernel_classification()
    qubo_results = benchmark_qubo_optimization()

    return {
        "kernel_classification": [
            {"size": r.problem_size, "quantum_time": r.quantum_time, "classical_time": r.classical_time, "winner": r.winner, "speedup": r.speedup}
            for r in kernel_results
        ],
        "qubo_optimization": [
            {"size": r.problem_size, "quantum_time": r.quantum_time, "classical_time": r.classical_time, "winner": r.winner, "speedup": r.speedup}
            for r in qubo_results
        ],
    }
