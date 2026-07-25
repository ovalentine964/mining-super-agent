"""
Quantum vs Classical Benchmarks.

Compares quantum and classical approaches for each problem type,
tracks performance over time, and automatically selects the better approach.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .quantum_config import QuantumConfig, QuantumBackend, DEFAULT_CONFIG
from .classical_fallback import ClassicalFallback

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkRun:
    """Single benchmark comparison."""
    problem_type: str
    quantum_time: float | None
    classical_time: float
    quantum_accuracy: float | None
    classical_accuracy: float | None
    quantum_backend: str
    classical_method: str
    problem_size: int
    winner: str  # "quantum", "classical", or "tie"
    quantum_advantage: float | None  # speedup ratio (quantum_time / classical_time)


@dataclass
class BenchmarkReport:
    """Full benchmark report across problem types."""
    timestamp: str
    runs: list[BenchmarkRun] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


class QuantumBenchmark:
    """Benchmark suite comparing quantum vs classical performance.

    Runs both quantum and classical on the same problems and compares:
    - Speed (wall-clock time)
    - Accuracy (classification) or optimality (optimization)
    - Resource usage (qubits, memory)

    Results feed back into QuantumConfig for automatic backend selection.
    """

    def __init__(self, config: QuantumConfig | None = None):
        self.config = config or DEFAULT_CONFIG
        self._history: list[BenchmarkRun] = []

    # ── Benchmark: Kernel Classification ──────────────────────────────────

    def benchmark_kernel_classification(
        self,
        X_train: NDArray,
        y_train: NDArray,
        X_test: NDArray,
        y_test: NDArray | None = None,
    ) -> BenchmarkRun:
        """Compare quantum kernel vs classical kernel for mineral classification."""
        from .quantum_kernel import QuantumKernelClassifier

        problem_size = X_train.shape[0]
        classifier = QuantumKernelClassifier(self.config)

        # Classical run (always)
        self.config.force_classical = True
        classical_result = classifier.classify(X_train, y_train, X_test)
        self.config.force_classical = False

        # Quantum run (if available)
        quantum_time = None
        quantum_accuracy = None
        quantum_backend_name = "unavailable"

        try:
            quantum_config = QuantumConfig(
                preferred_backend=QuantumBackend.PENNYLANE,
                force_classical=False,
                auto_select=False,
            )
            quantum_classifier = QuantumKernelClassifier(quantum_config)
            quantum_result = quantum_classifier.classify(X_train, y_train, X_test)
            quantum_time = quantum_result.elapsed_seconds
            quantum_accuracy = quantum_result.accuracy
            quantum_backend_name = quantum_result.backend_used
        except Exception as e:
            logger.info(f"Quantum kernel benchmark skipped: {e}")

        # Determine winner
        winner = self._compare(
            quantum_time, classical_result.elapsed_seconds,
            quantum_accuracy, classical_result.accuracy,
        )

        run = BenchmarkRun(
            problem_type="kernel_classification",
            quantum_time=quantum_time,
            classical_time=classical_result.elapsed_seconds,
            quantum_accuracy=quantum_accuracy,
            classical_accuracy=classical_result.accuracy,
            quantum_backend=quantum_backend_name,
            classical_method=classical_result.backend_used,
            problem_size=problem_size,
            winner=winner,
            quantum_advantage=(
                classical_result.elapsed_seconds / quantum_time
                if quantum_time and quantum_time > 0 else None
            ),
        )
        self._history.append(run)
        self._update_config_benchmarks(run)
        return run

    # ── Benchmark: QAOA Optimization ──────────────────────────────────────

    def benchmark_qaoa_optimization(
        self,
        n_sites: int = 15,
        n_select: int = 3,
    ) -> BenchmarkRun:
        """Compare QAOA vs classical optimization for drill target selection."""
        from .qaoa_optimizer import QAOAOptimizer

        # Generate problem
        site_values, distance_matrix, cost_per_site = QAOAOptimizer.generate_random_problem(
            n_sites=n_sites, n_select=n_select,
        )

        # Classical run
        self.config.force_classical = True
        classical_optimizer = QAOAOptimizer(self.config)
        Q = classical_optimizer.build_qubo_matrix(
            site_values, distance_matrix, cost_per_site, n_select,
        )
        classical_result = classical_optimizer._solve_classical(Q)
        self.config.force_classical = False

        # Quantum run
        quantum_time = None
        quantum_energy = None
        quantum_backend_name = "unavailable"

        try:
            quantum_config = QuantumConfig(
                preferred_backend=QuantumBackend.QISKIT,
                force_classical=False,
                auto_select=False,
                max_qubits=n_sites,
            )
            quantum_optimizer = QAOAOptimizer(quantum_config)
            quantum_result = quantum_optimizer.solve_with_qaoa(Q)
            quantum_time = quantum_result.elapsed_seconds
            quantum_energy = quantum_result.energy
            quantum_backend_name = quantum_result.backend_used
        except Exception as e:
            logger.info(f"QAOA benchmark skipped: {e}")

        # For optimization, lower energy = better
        classical_energy = classical_result.energy
        winner = "tie"
        if quantum_energy is not None:
            if quantum_energy < classical_energy * 0.95:
                winner = "quantum"
            elif classical_energy < quantum_energy * 0.95:
                winner = "classical"

        run = BenchmarkRun(
            problem_type="qaoa_optimization",
            quantum_time=quantum_time,
            classical_time=classical_result.elapsed_seconds,
            quantum_accuracy=None,
            classical_accuracy=None,
            quantum_backend=quantum_backend_name,
            classical_method=classical_result.backend_used,
            problem_size=n_sites,
            winner=winner,
            quantum_advantage=(
                classical_result.elapsed_seconds / quantum_time
                if quantum_time and quantum_time > 0 else None
            ),
        )
        self._history.append(run)
        self._update_config_benchmarks(run)
        return run

    # ── Benchmark: QUBO Solving ───────────────────────────────────────────

    def benchmark_qubo(self, n_vars: int = 10) -> BenchmarkRun:
        """Compare quantum vs classical QUBO solving."""
        # Random QUBO matrix
        rng = np.random.default_rng(42)
        Q = rng.standard_normal((n_vars, n_vars))
        Q = (Q + Q.T) / 2  # symmetric

        # Classical
        classical_result = ClassicalFallback.optimize_qubo(Q, num_reads=50)

        # Quantum (Qiskit)
        quantum_time = None
        quantum_energy = None
        quantum_backend_name = "unavailable"

        try:
            from .qaoa_optimizer import QAOAOptimizer
            quantum_config = QuantumConfig(
                preferred_backend=QuantumBackend.QISKIT,
                force_classical=False,
                auto_select=False,
                max_qubits=n_vars,
            )
            optimizer = QAOAOptimizer(quantum_config)
            result = optimizer.solve_with_qaoa(Q, depth=2, maxiter=100)
            quantum_time = result.elapsed_seconds
            quantum_energy = result.energy
            quantum_backend_name = result.backend_used
        except Exception as e:
            logger.info(f"QUBO quantum benchmark skipped: {e}")

        classical_energy = classical_result.result["energy"]
        winner = "tie"
        if quantum_energy is not None:
            if quantum_energy < classical_energy * 0.95:
                winner = "quantum"
            elif classical_energy < quantum_energy * 0.95:
                winner = "classical"

        run = BenchmarkRun(
            problem_type="qubo_solving",
            quantum_time=quantum_time,
            classical_time=classical_result.elapsed_seconds,
            quantum_accuracy=None,
            classical_accuracy=None,
            quantum_backend=quantum_backend_name,
            classical_method=classical_result.method,
            problem_size=n_vars,
            winner=winner,
            quantum_advantage=(
                classical_result.elapsed_seconds / quantum_time
                if quantum_time and quantum_time > 0 else None
            ),
        )
        self._history.append(run)
        self._update_config_benchmarks(run)
        return run

    # ── Full benchmark suite ──────────────────────────────────────────────

    def run_full_benchmark(
        self,
        classification_samples: int = 50,
        optimization_sites: int = 15,
        qubo_vars: int = 8,
    ) -> BenchmarkReport:
        """Run benchmarks across all problem types.

        Args:
            classification_samples: Number of samples for classification benchmark.
            optimization_sites: Number of sites for optimization benchmark.
            qubo_vars: Number of variables for QUBO benchmark.

        Returns:
            BenchmarkReport with all results.
        """
        import datetime

        report = BenchmarkReport(
            timestamp=datetime.datetime.now().isoformat(),
        )

        # Generate classification data
        rng = np.random.default_rng(42)
        n_features = 8
        X_train = rng.standard_normal((classification_samples, n_features))
        y_train = rng.integers(0, 2, size=classification_samples)
        X_test = rng.standard_normal((classification_samples // 2, n_features))
        y_test = rng.integers(0, 2, size=classification_samples // 2)

        # 1. Kernel classification
        logger.info("Benchmarking kernel classification...")
        try:
            run = self.benchmark_kernel_classification(X_train, y_train, X_test, y_test)
            report.runs.append(run)
        except Exception as e:
            logger.error(f"Kernel benchmark failed: {e}")

        # 2. QAOA optimization
        logger.info("Benchmarking QAOA optimization...")
        try:
            run = self.benchmark_qaoa_optimization(optimization_sites)
            report.runs.append(run)
        except Exception as e:
            logger.error(f"QAOA benchmark failed: {e}")

        # 3. QUBO solving
        logger.info("Benchmarking QUBO solving...")
        try:
            run = self.benchmark_qubo(qubo_vars)
            report.runs.append(run)
        except Exception as e:
            logger.error(f"QUBO benchmark failed: {e}")

        # Summary
        report.summary = self._build_summary(report.runs)
        return report

    # ── Reporting ─────────────────────────────────────────────────────────

    def _build_summary(self, runs: list[BenchmarkRun]) -> dict[str, Any]:
        """Build summary statistics from benchmark runs."""
        if not runs:
            return {}

        quantum_wins = sum(1 for r in runs if r.winner == "quantum")
        classical_wins = sum(1 for r in runs if r.winner == "classical")
        ties = sum(1 for r in runs if r.winner == "tie")

        advantages = [r.quantum_advantage for r in runs if r.quantum_advantage is not None]
        avg_advantage = float(np.mean(advantages)) if advantages else None

        return {
            "total_runs": len(runs),
            "quantum_wins": quantum_wins,
            "classical_wins": classical_wins,
            "ties": ties,
            "avg_quantum_speedup": avg_advantage,
            "recommendation": (
                "quantum" if quantum_wins > classical_wins else
                "classical" if classical_wins > quantum_wins else
                "use_both"
            ),
            "per_problem": {
                r.problem_type: {
                    "winner": r.winner,
                    "quantum_time": r.quantum_time,
                    "classical_time": r.classical_time,
                }
                for r in runs
            },
        }

    def _compare(
        self,
        quantum_time: float | None,
        classical_time: float,
        quantum_accuracy: float | None,
        classical_accuracy: float | None,
    ) -> str:
        """Compare quantum vs classical results."""
        if quantum_time is None:
            return "classical"

        # Accuracy matters more than speed
        if quantum_accuracy is not None and classical_accuracy is not None:
            acc_diff = quantum_accuracy - classical_accuracy
            if acc_diff > 0.02:  # quantum >2% more accurate
                return "quantum"
            elif acc_diff < -0.02:
                return "classical"

        # If accuracy similar, speed breaks tie
        if quantum_time < classical_time * 0.8:
            return "quantum"
        elif classical_time < quantum_time * 0.8:
            return "classical"

        return "tie"

    def _update_config_benchmarks(self, run: BenchmarkRun) -> None:
        """Feed benchmark results back into config for auto-selection."""
        if run.quantum_time is not None:
            self.config.record_benchmark(
                run.problem_type, QuantumBackend.PENNYLANE,
                run.quantum_time, run.quantum_accuracy,
            )
        self.config.record_benchmark(
            run.problem_type, QuantumBackend.CLASSICAL,
            run.classical_time, run.classical_accuracy,
        )

    # ── Persistence ───────────────────────────────────────────────────────

    def save_report(self, report: BenchmarkReport, path: str | Path) -> None:
        """Save benchmark report to JSON."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "timestamp": report.timestamp,
            "summary": report.summary,
            "runs": [asdict(r) for r in report.runs],
        }
        path.write_text(json.dumps(data, indent=2))
        logger.info(f"Benchmark report saved to {path}")

    def load_report(self, path: str | Path) -> BenchmarkReport:
        """Load benchmark report from JSON."""
        path = Path(path)
        data = json.loads(path.read_text())

        report = BenchmarkReport(timestamp=data["timestamp"])
        for run_data in data.get("runs", []):
            report.runs.append(BenchmarkRun(**run_data))
        report.summary = data.get("summary", {})
        return report

    def get_history(self) -> list[dict[str, Any]]:
        """Return benchmark history as dicts."""
        from dataclasses import asdict
        return [asdict(r) for r in self._history]
