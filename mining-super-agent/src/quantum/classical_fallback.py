"""
Classical Fallback — always-available alternatives for every quantum operation.

Every quantum method has a classical counterpart here. The system works fully
without any quantum libraries installed.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

# Try importing sklearn — required for classical fallbacks
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.svm import SVC
    from sklearn.kernel_approximation import RBFSampler, Nystroem
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import cross_val_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available — classical fallbacks will use numpy only")

try:
    from scipy.optimize import minimize, differential_evolution
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logger.warning("scipy not available — optimization fallbacks will be basic")


@dataclass
class BenchmarkResult:
    """Result from a classical computation with timing."""
    result: Any
    elapsed_seconds: float
    method: str
    accuracy: float | None = None


class ClassicalFallback:
    """Classical alternatives for every quantum operation.

    Methods:
        kernel_classification: RBF kernel SVM for mineral classification.
        random_forest_classification: Random Forest for mineral classification.
        optimize_drill_targets: scipy.optimize for drill target selection.
        optimize_qubo: Simulated annealing for QUBO problems.
        variational_classifier: Classical neural-network-like classifier.
        molecular_energy: Classical molecular energy estimation.
    """

    # ── 1. Kernel Classification (replaces quantum kernel SVM) ────────────

    @staticmethod
    def kernel_classification(
        X_train: NDArray,
        y_train: NDArray,
        X_test: NDArray,
        gamma: float = 1.0,
        n_components: int = 100,
    ) -> BenchmarkResult:
        """RBF kernel SVM via Nystroem approximation.

        Equivalent to quantum kernel methods but in classical feature space.
        Uses kernel approximation to mimic the higher-dimensional mapping
        that quantum feature maps provide.
        """
        start = time.perf_counter()

        if not SKLEARN_AVAILABLE:
            # Pure numpy fallback — simple nearest-centroid
            result = ClassicalFallback._numpy_nearest_centroid(X_train, y_train, X_test)
            elapsed = time.perf_counter() - start
            return BenchmarkResult(
                result=result, elapsed_seconds=elapsed, method="numpy_nearest_centroid"
            )

        # Nystroem approximation of RBF kernel (classical analogue of quantum feature map)
        n_comp = min(n_components, X_train.shape[0], X_train.shape[1] * 2)
        pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("kernel_map", Nystroem(kernel="rbf", gamma=gamma, n_components=n_comp, random_state=42)),
            ("svm", SVC(kernel="linear", C=1.0, random_state=42)),
        ])
        pipeline.fit(X_train, y_train)
        predictions = pipeline.predict(X_test)

        # Cross-val accuracy estimate
        try:
            cv_scores = cross_val_score(pipeline, X_train, y_train, cv=min(5, len(np.unique(y_train))))
            accuracy = float(np.mean(cv_scores))
        except Exception:
            accuracy = None

        elapsed = time.perf_counter() - start
        logger.info(f"Classical kernel classification done in {elapsed:.3f}s, accuracy={accuracy}")
        return BenchmarkResult(
            result=predictions, elapsed_seconds=elapsed,
            method="nystroem_rbf_svm", accuracy=accuracy,
        )

    # ── 2. Random Forest Classification ───────────────────────────────────

    @staticmethod
    def random_forest_classification(
        X_train: NDArray,
        y_train: NDArray,
        X_test: NDArray,
        n_estimators: int = 200,
        max_depth: int | None = None,
    ) -> BenchmarkResult:
        """Random Forest classifier — strong classical baseline for mineral classification."""
        start = time.perf_counter()

        if not SKLEARN_AVAILABLE:
            result = ClassicalFallback._numpy_nearest_centroid(X_train, y_train, X_test)
            elapsed = time.perf_counter() - start
            return BenchmarkResult(
                result=result, elapsed_seconds=elapsed, method="numpy_nearest_centroid"
            )

        clf = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=42,
            n_jobs=-1,
        )
        clf.fit(X_train, y_train)
        predictions = clf.predict(X_test)

        try:
            cv_scores = cross_val_score(clf, X_train, y_train, cv=min(5, len(np.unique(y_train))))
            accuracy = float(np.mean(cv_scores))
        except Exception:
            accuracy = None

        elapsed = time.perf_counter() - start
        logger.info(f"Random Forest done in {elapsed:.3f}s, accuracy={accuracy}")
        return BenchmarkResult(
            result=predictions, elapsed_seconds=elapsed,
            method="random_forest", accuracy=accuracy,
        )

    # ── 3. Drill Target Optimization (replaces QAOA) ──────────────────────

    @staticmethod
    def optimize_drill_targets(
        cost_matrix: NDArray,
        n_targets: int,
        method: str = "differential_evolution",
    ) -> BenchmarkResult:
        """Select optimal drill targets using classical optimization.

        Args:
            cost_matrix: NxN matrix where entry (i,j) is cost/value of drilling at site i
                with configuration j. Flattened for optimization.
            n_targets: Number of drill targets to select.
            method: 'differential_evolution' or 'simulated_annealing'.

        Returns:
            Selected target indices and total cost.
        """
        start = time.perf_counter()
        n_sites = cost_matrix.shape[0]

        if not SCIPY_AVAILABLE:
            # Greedy fallback
            result = ClassicalFallback._greedy_selection(cost_matrix, n_targets)
            elapsed = time.perf_counter() - start
            return BenchmarkResult(
                result=result, elapsed_seconds=elapsed, method="greedy_selection"
            )

        def objective(selected_indices_flat):
            """Minimize negative total value (maximize value)."""
            indices = np.argsort(selected_indices_flat)[:n_targets]
            total = sum(cost_matrix[i, i] for i in indices)
            return -total

        # Differential evolution — global optimizer
        bounds = [(0, 1)] * n_sites
        de_result = differential_evolution(
            objective, bounds, maxiter=200, seed=42, tol=1e-6,
            popsize=15, mutation=(0.5, 1.0),
        )
        selected = np.argsort(de_result.x)[:n_targets]
        total_value = -de_result.fun

        elapsed = time.perf_counter() - start
        logger.info(f"Drill optimization done in {elapsed:.3f}s, value={total_value:.2f}")
        return BenchmarkResult(
            result={"selected_targets": selected.tolist(), "total_value": total_value},
            elapsed_seconds=elapsed,
            method="differential_evolution",
        )

    # ── 4. QUBO Solver (replaces QAOA for combinatorial problems) ─────────

    @staticmethod
    def optimize_qubo(
        Q: NDArray,
        num_reads: int = 100,
    ) -> BenchmarkResult:
        """Solve a QUBO (Quadratic Unconstrained Binary Optimization) problem.

        Uses simulated annealing as classical alternative to QAOA.

        Args:
            Q: QUBO matrix (upper triangular).
            num_reads: Number of restarts for simulated annealing.

        Returns:
            Best bitstring and its energy.
        """
        start = time.perf_counter()
        n = Q.shape[0]

        best_x = None
        best_energy = float("inf")

        for _ in range(num_reads):
            # Random initial state
            x = np.random.randint(0, 2, size=n).astype(float)

            # Simulated annealing
            energy = x @ Q @ x
            temperature = 1.0
            cooling = 0.995

            for step in range(1000):
                # Flip a random bit
                idx = np.random.randint(n)
                x_new = x.copy()
                x_new[idx] = 1 - x_new[idx]
                energy_new = x_new @ Q @ x_new

                # Accept or reject
                delta = energy_new - energy
                if delta < 0 or np.random.random() < np.exp(-delta / max(temperature, 1e-10)):
                    x = x_new
                    energy = energy_new

                temperature *= cooling

                if energy < best_energy:
                    best_energy = energy
                    best_x = x.copy()

        elapsed = time.perf_counter() - start
        logger.info(f"QUBO solved in {elapsed:.3f}s, energy={best_energy:.4f}")
        return BenchmarkResult(
            result={"bitstring": best_x.tolist(), "energy": best_energy},
            elapsed_seconds=elapsed,
            method="simulated_annealing",
        )

    # ── 5. Variational Classifier (replaces quantum variational classifier) ──

    @staticmethod
    def variational_classifier(
        X_train: NDArray,
        y_train: NDArray,
        X_test: NDArray,
        hidden_dim: int = 64,
        n_estimators: int = 100,
    ) -> BenchmarkResult:
        """Gradient Boosting as classical variational classifier analogue.

        Mimics the hybrid quantum-classical training loop with an
        iterative boosting approach.
        """
        start = time.perf_counter()

        if not SKLEARN_AVAILABLE:
            result = ClassicalFallback._numpy_nearest_centroid(X_train, y_train, X_test)
            elapsed = time.perf_counter() - start
            return BenchmarkResult(
                result=result, elapsed_seconds=elapsed, method="numpy_nearest_centroid"
            )

        pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", GradientBoostingClassifier(
                n_estimators=n_estimators,
                max_depth=5,
                learning_rate=0.1,
                random_state=42,
            )),
        ])
        pipeline.fit(X_train, y_train)
        predictions = pipeline.predict(X_test)

        try:
            cv_scores = cross_val_score(pipeline, X_train, y_train, cv=min(5, len(np.unique(y_train))))
            accuracy = float(np.mean(cv_scores))
        except Exception:
            accuracy = None

        elapsed = time.perf_counter() - start
        logger.info(f"Variational classifier done in {elapsed:.3f}s, accuracy={accuracy}")
        return BenchmarkResult(
            result=predictions, elapsed_seconds=elapsed,
            method="gradient_boosting", accuracy=accuracy,
        )

    # ── 6. Molecular Energy Estimation (replaces quantum chemistry) ───────

    @staticmethod
    def molecular_energy(
        atomic_numbers: list[int],
        coordinates: NDArray,
        method: str = "simple_pairwise",
    ) -> BenchmarkResult:
        """Classical molecular energy estimation.

        Uses pairwise Lennard-Jones-like potentials as a simplified
        alternative to quantum VQE molecular simulation.

        Args:
            atomic_numbers: List of atomic numbers for each atom.
            coordinates: (N, 3) array of atomic positions in Angstroms.
            method: 'simple_pairwise' or 'coulomb'.

        Returns:
            Estimated energy in eV.
        """
        start = time.perf_counter()

        n_atoms = len(atomic_numbers)
        total_energy = 0.0

        # Lennard-Jones parameters (simplified, in eV and Angstroms)
        # sigma ~ ionic radius, epsilon ~ bond strength
        lj_params = {
            79: (2.5, 0.5),   # Au — gold
            16: (3.5, 0.3),   # S  — sulfur (pyrite FeS2)
            26: (2.8, 0.4),   # Fe — iron
            29: (2.6, 0.45),  # Cu — copper
            8:  (3.0, 0.2),   # O  — oxygen
            14: (3.8, 0.15),  # Si — silicon
        }
        default_params = (3.0, 0.2)

        for i in range(n_atoms):
            for j in range(i + 1, n_atoms):
                ri = np.array(coordinates[i])
                rj = np.array(coordinates[j])
                dist = np.linalg.norm(ri - rj)

                if dist < 0.1:
                    dist = 0.1  # avoid singularity

                sigma_i, eps_i = lj_params.get(atomic_numbers[i], default_params)
                sigma_j, eps_j = lj_params.get(atomic_numbers[j], default_params)
                sigma = (sigma_i + sigma_j) / 2
                eps = np.sqrt(eps_i * eps_j)

                # Lennard-Jones potential
                sr6 = (sigma / dist) ** 6
                sr12 = sr6 ** 2
                lj_energy = 4 * eps * (sr12 - sr6)

                # Optional Coulomb term
                if method == "coulomb":
                    charge_i = float(atomic_numbers[i]) * 0.1
                    charge_j = float(atomic_numbers[j]) * 0.1
                    coulomb = 14.4 * charge_i * charge_j / dist  # eV
                    total_energy += lj_energy + coulomb
                else:
                    total_energy += lj_energy

        elapsed = time.perf_counter() - start
        logger.info(f"Molecular energy ({method}) = {total_energy:.4f} eV in {elapsed:.3f}s")
        return BenchmarkResult(
            result=total_energy, elapsed_seconds=elapsed, method=method,
        )

    # ── Internal helpers ──────────────────────────────────────────────────

    @staticmethod
    def _numpy_nearest_centroid(
        X_train: NDArray, y_train: NDArray, X_test: NDArray
    ) -> NDArray:
        """Simplest fallback: nearest centroid classifier using pure numpy."""
        classes = np.unique(y_train)
        centroids = {}
        for c in classes:
            centroids[c] = X_train[y_train == c].mean(axis=0)

        predictions = []
        for x in X_test:
            dists = {c: np.linalg.norm(x - centroid) for c, centroid in centroids.items()}
            predictions.append(min(dists, key=dists.get))
        return np.array(predictions)

    @staticmethod
    def _greedy_selection(cost_matrix: NDArray, n_targets: int) -> dict:
        """Greedy fallback for drill target selection."""
        n_sites = cost_matrix.shape[0]
        diag = np.diag(cost_matrix)
        selected = np.argsort(diag)[-n_targets:][::-1]
        total = float(diag[selected].sum())
        return {"selected_targets": selected.tolist(), "total_value": total}
