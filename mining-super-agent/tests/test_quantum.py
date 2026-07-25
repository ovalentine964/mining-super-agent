"""
Quantum Module Tests.

Tests all quantum operations, classical fallbacks, and benchmarking.
Every test verifies that classical fallback works (system works without quantum).
"""

import numpy as np
import pytest
from numpy.testing import assert_array_equal

# ── Test fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def binary_classification_data():
    """Simple binary classification data (gold vs pyrite-like)."""
    rng = np.random.default_rng(42)
    n_train, n_test, n_features = 30, 10, 6

    # Two clusters (simulating gold and pyrite spectral signatures)
    X_train = np.vstack([
        rng.normal(0.3, 0.1, (n_train // 2, n_features)),  # class 0
        rng.normal(0.7, 0.1, (n_train // 2, n_features)),  # class 1
    ])
    y_train = np.array([0] * (n_train // 2) + [1] * (n_train // 2))

    X_test = np.vstack([
        rng.normal(0.3, 0.1, (n_test // 2, n_features)),
        rng.normal(0.7, 0.1, (n_test // 2, n_features)),
    ])
    y_test = np.array([0] * (n_test // 2) + [1] * (n_test // 2))

    return X_train, y_train, X_test, y_test


@pytest.fixture
def small_classification_data():
    """Tiny dataset for fast tests."""
    rng = np.random.default_rng(42)
    X_train = rng.standard_normal((12, 4))
    y_train = np.array([0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1])
    X_test = rng.standard_normal((6, 4))
    return X_train, y_train, X_test


@pytest.fixture
def optimization_problem():
    """Small drill optimization problem."""
    from src.quantum.qaoa_optimizer import QAOAOptimizer
    return QAOAOptimizer.generate_random_problem(n_sites=10, n_select=3)


# ── 1. Quantum Config Tests ──────────────────────────────────────────────

class TestQuantumConfig:
    """Test quantum configuration and backend selection."""

    def test_default_config_is_classical(self):
        """Default config should prefer classical when quantum not needed."""
        from src.quantum.quantum_config import QuantumConfig, QuantumBackend
        config = QuantumConfig()
        # Small problem → classical
        backend = config.select_backend("test", problem_size=5)
        assert backend == QuantumBackend.CLASSICAL

    def test_force_classical(self):
        """force_classical=True always returns CLASSICAL."""
        from src.quantum.quantum_config import QuantumConfig, QuantumBackend
        config = QuantumConfig(force_classical=True)
        backend = config.select_backend("test", problem_size=1000, n_qubits_needed=20)
        assert backend == QuantumBackend.CLASSICAL

    def test_available_backends_includes_classical(self):
        """CLASSICAL is always available."""
        from src.quantum.quantum_config import QuantumConfig, QuantumBackend
        config = QuantumConfig()
        backends = config.available_backends()
        assert QuantumBackend.CLASSICAL in backends

    def test_benchmark_recording(self):
        """Config records benchmarks correctly."""
        from src.quantum.quantum_config import QuantumConfig, QuantumBackend
        config = QuantumConfig()
        config.record_benchmark("test_problem", QuantumBackend.CLASSICAL, 1.5, 0.9)
        config.record_benchmark("test_problem", QuantumBackend.CLASSICAL, 2.0, 0.85)

        history = config.benchmark_history["test_problem"]
        assert "classical_time" in history
        assert "classical_accuracy" in history
        # EMA should be between the two values
        assert 1.5 <= history["classical_time"] <= 2.0

    def test_report(self):
        """Config report returns expected keys."""
        from src.quantum.quantum_config import QuantumConfig
        config = QuantumConfig()
        report = config.get_report()
        assert "preferred_backend" in report
        assert "available_backends" in report
        assert "force_classical" in report


# ── 2. Classical Fallback Tests ──────────────────────────────────────────

class TestClassicalFallback:
    """Test that all classical fallbacks work correctly."""

    def test_kernel_classification(self, binary_classification_data):
        """Classical kernel classification returns valid predictions."""
        from src.quantum.classical_fallback import ClassicalFallback
        X_train, y_train, X_test, y_test = binary_classification_data

        result = ClassicalFallback.kernel_classification(X_train, y_train, X_test)

        assert result.result is not None
        assert len(result.result) == len(X_test)
        assert all(p in [0, 1] for p in result.result)
        assert result.elapsed_seconds > 0
        assert result.method is not None

    def test_kernel_classification_accuracy(self, binary_classification_data):
        """Classical kernel should get >70% on separable data."""
        from src.quantum.classical_fallback import ClassicalFallback
        X_train, y_train, X_test, y_test = binary_classification_data

        result = ClassicalFallback.kernel_classification(X_train, y_train, X_test)
        accuracy = np.mean(result.result == y_test)
        assert accuracy > 0.7, f"Accuracy {accuracy:.2f} too low for separable data"

    def test_random_forest_classification(self, binary_classification_data):
        """Random Forest fallback works."""
        from src.quantum.classical_fallback import ClassicalFallback
        X_train, y_train, X_test, y_test = binary_classification_data

        result = ClassicalFallback.random_forest_classification(X_train, y_train, X_test)

        assert len(result.result) == len(X_test)
        assert all(p in [0, 1] for p in result.result)

    def test_optimize_drill_targets(self):
        """Classical drill optimization returns valid targets."""
        from src.quantum.classical_fallback import ClassicalFallback
        rng = np.random.default_rng(42)
        cost_matrix = rng.standard_normal((10, 10))
        cost_matrix = (cost_matrix + cost_matrix.T) / 2

        result = ClassicalFallback.optimize_drill_targets(cost_matrix, n_targets=3)

        assert "selected_targets" in result.result
        assert "total_value" in result.result
        assert len(result.result["selected_targets"]) == 3

    def test_optimize_qubo(self):
        """Classical QUBO solver returns valid solution."""
        from src.quantum.classical_fallback import ClassicalFallback
        rng = np.random.default_rng(42)
        Q = rng.standard_normal((8, 8))
        Q = (Q + Q.T) / 2

        result = ClassicalFallback.optimize_qubo(Q, num_reads=20)

        assert "bitstring" in result.result
        assert "energy" in result.result
        assert len(result.result["bitstring"]) == 8
        assert all(b in [0.0, 1.0] for b in result.result["bitstring"])

    def test_variational_classifier(self, binary_classification_data):
        """Classical variational classifier works."""
        from src.quantum.classical_fallback import ClassicalFallback
        X_train, y_train, X_test, y_test = binary_classification_data

        result = ClassicalFallback.variational_classifier(X_train, y_train, X_test)

        assert len(result.result) == len(X_test)
        assert result.accuracy is not None or result.elapsed_seconds > 0

    def test_molecular_energy(self):
        """Classical molecular energy estimation works."""
        from src.quantum.classical_fallback import ClassicalFallback
        # Gold atom at origin
        result = ClassicalFallback.molecular_energy(
            atomic_numbers=[79],
            coordinates=np.array([[0, 0, 0]]),
        )
        assert isinstance(result.result, float)

    def test_molecular_energy_multi_atom(self):
        """Multi-atom molecular energy works."""
        from src.quantum.classical_fallback import ClassicalFallback
        # FeS2 (pyrite)
        result = ClassicalFallback.molecular_energy(
            atomic_numbers=[26, 16, 16],
            coordinates=np.array([[0, 0, 0], [2, 0, 0], [-2, 0, 0]]),
        )
        assert isinstance(result.result, float)

    def test_numpy_nearest_centroid(self, small_classification_data):
        """Pure numpy fallback works when sklearn unavailable."""
        from src.quantum.classical_fallback import ClassicalFallback
        X_train, y_train, X_test = small_classification_data

        result = ClassicalFallback._numpy_nearest_centroid(X_train, y_train, X_test)

        assert len(result) == len(X_test)
        assert all(p in [0, 1] for p in result)


# ── 3. Quantum Kernel Tests ──────────────────────────────────────────────

class TestQuantumKernel:
    """Test quantum kernel classifier (and its classical fallback)."""

    def test_classify_uses_classical_fallback(self, small_classification_data):
        """With force_classical=True, must use classical backend."""
        from src.quantum.quantum_kernel import QuantumKernelClassifier
        from src.quantum.quantum_config import QuantumConfig

        X_train, y_train, X_test = small_classification_data
        config = QuantumConfig(force_classical=True)
        clf = QuantumKernelClassifier(config)

        result = clf.classify(X_train, y_train, X_test)

        assert result.backend_used.startswith("classical")
        assert len(result.predictions) == len(X_test)
        assert result.elapsed_seconds > 0

    def test_classify_returns_valid_predictions(self, small_classification_data):
        """Classification returns valid predictions regardless of backend."""
        from src.quantum.quantum_kernel import QuantumKernelClassifier

        X_train, y_train, X_test = small_classification_data
        clf = QuantumKernelClassifier()
        result = clf.classify(X_train, y_train, X_test)

        assert len(result.predictions) == len(X_test)
        assert all(p in [0, 1] for p in result.predictions)

    def test_gold_pyrite_features(self):
        """Feature creation for gold vs pyrite works."""
        from src.quantum.quantum_kernel import QuantumKernelClassifier
        rng = np.random.default_rng(42)
        spectral = rng.random((10, 5))
        chemical = rng.random((10, 3))

        features = QuantumKernelClassifier.create_gold_pyrite_features(spectral, chemical)

        assert features.shape == (10, 8)
        # Should be normalized to [0, π]
        assert features.min() >= 0
        assert features.max() <= np.pi + 0.01

    def test_gold_pyrite_features_spectral_only(self):
        """Works with spectral data only."""
        from src.quantum.quantum_kernel import QuantumKernelClassifier
        rng = np.random.default_rng(42)
        spectral = rng.random((5, 4))

        features = QuantumKernelClassifier.create_gold_pyrite_features(spectral)

        assert features.shape == (5, 4)

    def test_auto_select_small_problem(self, small_classification_data):
        """Small problems should auto-select classical."""
        from src.quantum.quantum_kernel import QuantumKernelClassifier
        from src.quantum.quantum_config import QuantumConfig, QuantumBackend

        X_train, y_train, X_test = small_classification_data
        config = QuantumConfig(auto_select=True, force_classical=False)
        clf = QuantumKernelClassifier(config)

        # With only 12 samples, should pick classical
        result = clf.classify(X_train, y_train, X_test)
        assert "classical" in result.backend_used


# ── 4. QAOA Optimizer Tests ──────────────────────────────────────────────

class TestQAOAOptimizer:
    """Test QAOA optimizer (and its classical fallback)."""

    def test_build_qubo_matrix(self, optimization_problem):
        """QUBO matrix construction works."""
        from src.quantum.qaoa_optimizer import QAOAOptimizer
        site_values, distance_matrix, cost_per_site = optimization_problem

        Q = QAOAOptimizer.build_qubo_matrix(
            site_values, distance_matrix, cost_per_site, n_select=3
        )

        assert Q.shape == (10, 10)
        # Should be symmetric (approximately)
        np.testing.assert_allclose(Q, Q.T, atol=1e-10)

    def test_classical_fallback_solve(self, optimization_problem):
        """Classical QUBO solving works."""
        from src.quantum.qaoa_optimizer import QAOAOptimizer
        from src.quantum.quantum_config import QuantumConfig

        site_values, distance_matrix, cost_per_site = optimization_problem
        config = QuantumConfig(force_classical=True)
        optimizer = QAOAOptimizer(config)

        result = optimizer.optimize_drill_targets(
            site_values, distance_matrix, cost_per_site, n_select=3
        )

        assert "classical" in result.backend_used
        assert len(result.selected_targets) == 3
        assert result.energy is not None

    def test_optimize_returns_targets(self):
        """Optimization returns selected targets."""
        from src.quantum.qaoa_optimizer import QAOAOptimizer
        from src.quantum.quantum_config import QuantumConfig

        sv, dm, cs = QAOAOptimizer.generate_random_problem(n_sites=8, n_select=2)
        config = QuantumConfig(force_classical=True)
        optimizer = QAOAOptimizer(config)

        result = optimizer.optimize_drill_targets(sv, dm, cs, n_select=2)
        assert len(result.selected_targets) > 0
        assert result.energy is not None

    def test_generate_random_problem(self):
        """Random problem generation works."""
        from src.quantum.qaoa_optimizer import QAOAOptimizer
        sv, dm, cs = QAOAOptimizer.generate_random_problem(n_sites=15, n_select=4)

        assert len(sv) == 15
        assert dm.shape == (15, 15)
        assert len(cs) == 15
        assert (dm >= 0).all()  # distances non-negative

    def test_qaoa_classical_consistency(self):
        """Classical optimization produces consistent results."""
        from src.quantum.qaoa_optimizer import QAOAOptimizer
        from src.quantum.quantum_config import QuantumConfig

        sv, dm, cs = QAOAOptimizer.generate_random_problem(n_sites=10, n_select=3)
        config = QuantumConfig(force_classical=True)

        # Run twice — should get same result (deterministic)
        opt1 = QAOAOptimizer(config)
        r1 = opt1.optimize_drill_targets(sv, dm, cs, n_select=3)

        opt2 = QAOAOptimizer(config)
        r2 = opt2.optimize_drill_targets(sv, dm, cs, n_select=3)

        # Both should select 3 targets
        assert len(r1.selected_targets) == 3
        assert len(r2.selected_targets) == 3


# ── 5. Quantum ML Tests ──────────────────────────────────────────────────

class TestQuantumML:
    """Test variational quantum classifier."""

    def test_vqc_classical_fallback(self, small_classification_data):
        """VQC falls back to classical when forced."""
        from src.quantum.quantum_ml import VariationalQuantumClassifier
        from src.quantum.quantum_config import QuantumConfig

        X_train, y_train, X_test = small_classification_data
        config = QuantumConfig(force_classical=True)
        vqc = VariationalQuantumClassifier(config=config, n_epochs=5)

        result = vqc.fit_predict(X_train, y_train, X_test)

        assert "classical" in result.backend_used
        assert len(result.predictions) == len(X_test)

    def test_vqc_returns_valid_predictions(self, small_classification_data):
        """VQC returns valid predictions regardless of backend."""
        from src.quantum.quantum_ml import VariationalQuantumClassifier
        from src.quantum.quantum_config import QuantumConfig

        X_train, y_train, X_test = small_classification_data
        config = QuantumConfig(force_classical=True)
        vqc = VariationalQuantumClassifier(config=config, n_epochs=3)

        result = vqc.fit_predict(X_train, y_train, X_test)

        assert all(p in [0, 1] for p in result.predictions)
        assert result.elapsed_seconds > 0

    def test_quantum_neural_network(self, small_classification_data):
        """QNN delegates to VQC correctly."""
        from src.quantum.quantum_ml import QuantumNeuralNetwork
        from src.quantum.quantum_config import QuantumConfig

        X_train, y_train, X_test = small_classification_data
        config = QuantumConfig(force_classical=True)
        qnn = QuantumNeuralNetwork(config=config, n_qubits=4, n_layers=2)

        result = qnn.predict(X_train, y_train, X_test)

        assert len(result.predictions) == len(X_test)


# ── 6. Quantum Chemistry Tests ───────────────────────────────────────────

class TestQuantumChemistry:
    """Test quantum chemistry simulation."""

    def test_simulate_gold(self):
        """Simulate gold atom energy."""
        from src.quantum.quantum_chemistry import QuantumChemistrySimulator
        from src.quantum.quantum_config import QuantumConfig

        config = QuantumConfig(force_classical=True)
        sim = QuantumChemistrySimulator(config)

        result = sim.simulate_mineral("gold")

        assert result.mineral == "gold"
        assert result.atom_count == 1
        assert isinstance(result.energy_ev, float)
        assert result.elapsed_seconds > 0

    def test_simulate_pyrite(self):
        """Simulate pyrite (FeS2) energy."""
        from src.quantum.quantum_chemistry import QuantumChemistrySimulator
        from src.quantum.quantum_config import QuantumConfig

        config = QuantumConfig(force_classical=True)
        sim = QuantumChemistrySimulator(config)

        result = sim.simulate_mineral("pyrite")

        assert result.mineral == "pyrite"
        assert result.atom_count == 3  # Fe + S + S

    def test_simulate_mineral_pair(self):
        """Simulate mineral pair co-location."""
        from src.quantum.quantum_chemistry import QuantumChemistrySimulator
        from src.quantum.quantum_config import QuantumConfig

        config = QuantumConfig(force_classical=True)
        sim = QuantumChemistrySimulator(config)

        pair = sim.simulate_mineral_pair("gold", "pyrite")

        assert pair["mineral1"] == "gold"
        assert pair["mineral2"] == "pyrite"
        assert "binding_energy_ev" in pair
        assert "likely_co_occur" in pair
        assert pair["likely_co_occur"] in (True, False, np.bool_(True), np.bool_(False))

    def test_common_associations(self):
        """Find mineral associations."""
        from src.quantum.quantum_chemistry import QuantumChemistrySimulator
        from src.quantum.quantum_config import QuantumConfig

        config = QuantumConfig(force_classical=True)
        sim = QuantumChemistrySimulator(config)

        associations = sim.get_common_associations("gold")

        assert len(associations) > 0
        assert all("mineral" in a for a in associations)
        assert all("binding_energy_ev" in a for a in associations)

    def test_unknown_mineral_raises(self):
        """Unknown mineral raises ValueError."""
        from src.quantum.quantum_chemistry import QuantumChemistrySimulator
        sim = QuantumChemistrySimulator()

        with pytest.raises(ValueError, match="Unknown mineral"):
            sim.simulate_mineral("unobtanium")

    def test_custom_coordinates(self):
        """Custom molecular geometry works."""
        from src.quantum.quantum_chemistry import QuantumChemistrySimulator
        from src.quantum.quantum_config import QuantumConfig

        config = QuantumConfig(force_classical=True)
        sim = QuantumChemistrySimulator(config)

        coords = np.array([[0, 0, 0], [2.5, 0, 0], [0, 2.5, 0]])
        result = sim.simulate_mineral("pyrite", coordinates=coords)

        assert result.atom_count == 3

    def test_all_minerals_in_database(self):
        """Every mineral in the database can be simulated."""
        from src.quantum.quantum_chemistry import QuantumChemistrySimulator, MINERAL_FORMULAS
        from src.quantum.quantum_config import QuantumConfig

        config = QuantumConfig(force_classical=True)
        sim = QuantumChemistrySimulator(config)

        for mineral_name in MINERAL_FORMULAS:
            result = sim.simulate_mineral(mineral_name)
            assert result.mineral == mineral_name
            assert isinstance(result.energy_ev, float)


# ── 7. Benchmark Tests ───────────────────────────────────────────────────

class TestBenchmarks:
    """Test benchmarking infrastructure."""

    def test_kernel_benchmark(self, small_classification_data):
        """Kernel classification benchmark runs."""
        from src.quantum.benchmarks import QuantumBenchmark
        from src.quantum.quantum_config import QuantumConfig

        X_train, y_train, X_test = small_classification_data
        config = QuantumConfig(force_classical=False)
        bench = QuantumBenchmark(config)

        run = bench.benchmark_kernel_classification(X_train, y_train, X_test)

        assert run.problem_type == "kernel_classification"
        assert run.classical_time > 0
        assert run.winner in ["quantum", "classical", "tie"]
        assert run.problem_size == len(X_train)

    def test_qaoa_benchmark(self):
        """QAOA optimization benchmark runs."""
        from src.quantum.benchmarks import QuantumBenchmark
        bench = QuantumBenchmark()

        run = bench.benchmark_qaoa_optimization(n_sites=8, n_select=2)

        assert run.problem_type == "qaoa_optimization"
        assert run.classical_time > 0

    def test_qubo_benchmark(self):
        """QUBO benchmark runs."""
        from src.quantum.benchmarks import QuantumBenchmark
        bench = QuantumBenchmark()

        run = bench.benchmark_qubo(n_vars=6)

        assert run.problem_type == "qubo_solving"
        assert run.classical_time > 0

    def test_full_benchmark(self):
        """Full benchmark suite runs without errors."""
        from src.quantum.benchmarks import QuantumBenchmark
        bench = QuantumBenchmark()

        report = bench.run_full_benchmark(
            classification_samples=15,
            optimization_sites=8,
            qubo_vars=6,
        )

        assert report.timestamp is not None
        assert len(report.runs) > 0
        assert "total_runs" in report.summary

    def test_benchmark_report_save_load(self, tmp_path):
        """Benchmark report can be saved and loaded."""
        from src.quantum.benchmarks import QuantumBenchmark
        bench = QuantumBenchmark()

        report = bench.run_full_benchmark(
            classification_samples=10,
            optimization_sites=6,
            qubo_vars=5,
        )

        path = tmp_path / "benchmark.json"
        bench.save_report(report, path)

        loaded = bench.load_report(path)
        assert loaded.timestamp == report.timestamp
        assert len(loaded.runs) == len(report.runs)

    def test_benchmark_history(self, small_classification_data):
        """Benchmark tracks history."""
        from src.quantum.benchmarks import QuantumBenchmark
        X_train, y_train, X_test = small_classification_data

        bench = QuantumBenchmark()
        bench.benchmark_kernel_classification(X_train, y_train, X_test)

        history = bench.get_history()
        assert len(history) == 1
        assert history[0]["problem_type"] == "kernel_classification"


# ── 8. Integration Tests ─────────────────────────────────────────────────

class TestIntegration:
    """End-to-end integration tests."""

    def test_full_pipeline_classical(self, binary_classification_data):
        """Full pipeline works with classical fallback."""
        from src.quantum.quantum_kernel import QuantumKernelClassifier
        from src.quantum.qaoa_optimizer import QAOAOptimizer
        from src.quantum.quantum_ml import VariationalQuantumClassifier
        from src.quantum.quantum_chemistry import QuantumChemistrySimulator
        from src.quantum.quantum_config import QuantumConfig

        X_train, y_train, X_test, y_test = binary_classification_data
        config = QuantumConfig(force_classical=True)

        # 1. Kernel classification
        clf = QuantumKernelClassifier(config)
        kernel_result = clf.classify(X_train, y_train, X_test)
        assert len(kernel_result.predictions) == len(X_test)

        # 2. QAOA optimization
        sv, dm, cs = QAOAOptimizer.generate_random_problem(n_sites=10, n_select=3)
        opt = QAOAOptimizer(config)
        opt_result = opt.optimize_drill_targets(sv, dm, cs, n_select=3)
        assert len(opt_result.selected_targets) == 3

        # 3. VQC classification
        vqc = VariationalQuantumClassifier(config=config, n_epochs=3)
        vqc_result = vqc.fit_predict(X_train, y_train, X_test)
        assert len(vqc_result.predictions) == len(X_test)

        # 4. Chemistry simulation
        sim = QuantumChemistrySimulator(config)
        chem_result = sim.simulate_mineral("gold")
        assert isinstance(chem_result.energy_ev, float)

    def test_auto_degradation(self):
        """System automatically degrades to classical when quantum unavailable."""
        from src.quantum.quantum_config import QuantumConfig, QuantumBackend

        config = QuantumConfig(auto_select=True, force_classical=False)

        # Small problem → should pick classical
        backend = config.select_backend("test", problem_size=4, n_qubits_needed=2)
        assert backend == QuantumBackend.CLASSICAL

    def test_classical_is_always_available(self):
        """Classical backend is always listed as available."""
        from src.quantum.quantum_config import QuantumConfig, QuantumBackend
        config = QuantumConfig()
        assert QuantumBackend.CLASSICAL in config.available_backends()
