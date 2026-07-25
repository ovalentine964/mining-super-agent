"""Tests for quantum computing modules."""

import pytest
import numpy as np
from src.quantum.quantum_config import QuantumConfig, QuantumBackend


class TestQuantumConfig:
    def test_default_config(self):
        config = QuantumConfig()
        assert config.max_qubits == 20
        assert config.auto_select is True
        assert config.force_classical is False

    def test_force_classical(self):
        config = QuantumConfig(force_classical=True)
        backend = config.select_backend("classification", problem_size=100)
        assert backend == QuantumBackend.CLASSICAL

    def test_small_problem_classical(self):
        config = QuantumConfig(qubit_threshold=8)
        backend = config.select_backend("classification", problem_size=4)
        assert backend == QuantumBackend.CLASSICAL  # 4 < 8 threshold

    def test_available_backends(self):
        config = QuantumConfig()
        backends = config.available_backends()
        assert QuantumBackend.CLASSICAL in backends


class TestClassicalFallback:
    def test_kernel_classification(self):
        from src.quantum.classical_fallback import ClassicalFallback
        rng = np.random.default_rng(42)
        X_train = rng.random((20, 4))
        y_train = rng.integers(0, 2, size=20)
        X_test = rng.random((5, 4))
        result = ClassicalFallback.kernel_classification(X_train, y_train, X_test)
        assert len(result.result) == 5
        assert result.method == "rbf_svm"

    def test_qubo_optimization(self):
        from src.quantum.classical_fallback import ClassicalFallback
        Q = np.array([[2, -1], [-1, 2]], dtype=float)
        result = ClassicalFallback.optimize_qubo(Q)
        assert "bitstring" in result.result
        assert "energy" in result.result


class TestQAOAOptimizer:
    def test_build_qubo_matrix(self):
        from src.quantum.qaoa_optimizer import QAOAOptimizer
        site_values = np.array([10.0, 20.0, 30.0])
        dist_matrix = np.array([[0, 100, 200], [100, 0, 150], [200, 150, 0]], dtype=float)
        costs = np.array([5.0, 8.0, 12.0])
        Q = QAOAOptimizer.build_qubo_matrix(site_values, dist_matrix, costs, n_select=2)
        assert Q.shape == (3, 3)
        # Diagonal should have -(value - cost) + penalty
        assert Q[0, 0] != 0


class TestBenchmarks:
    def test_run_benchmarks(self):
        from src.quantum.benchmarks import run_full_benchmark
        results = run_full_benchmark()
        assert "kernel_classification" in results
        assert "qubo_optimization" in results
        assert len(results["kernel_classification"]) > 0
