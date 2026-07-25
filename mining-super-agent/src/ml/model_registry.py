"""
Model registry — versioned model storage and loading.
"""

from __future__ import annotations

import json
import logging
import random
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Registry for managing trained model versions."""

    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.models_dir / "registry.json"
        self.ab_tests: dict[str, dict[str, Any]] = {}  # model_name -> {opponent, ratio, started_at}
        self.rollback_log: list[dict[str, Any]] = []   # chronological rollback history
        self.performance_history: dict[str, list[dict[str, Any]]] = {}  # model_name -> [{version, metrics, ts}]
        self._registry = self._load_registry()

    def _load_registry(self) -> dict:
        if self.registry_file.exists():
            return json.loads(self.registry_file.read_text())
        return {"models": {}, "active": {}}

    def _save_registry(self):
        self.registry_file.write_text(json.dumps(self._registry, indent=2, default=str))

    def register(
        self,
        name: str,
        version: str,
        model_path: str,
        metrics: Optional[dict[str, Any]] = None,
        description: str = "",
    ) -> dict:
        """Register a new model version."""
        entry = {
            "version": version,
            "path": model_path,
            "metrics": metrics or {},
            "description": description,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }

        if name not in self._registry["models"]:
            self._registry["models"][name] = []
        self._registry["models"][name].append(entry)
        self._registry["active"][name] = version
        self._save_registry()

        logger.info("Registered model %s v%s", name, version)
        return entry

    def get_active(self, name: str) -> Optional[dict]:
        """Get the active version of a model."""
        version = self._registry["active"].get(name)
        if not version:
            return None
        for entry in self._registry["models"].get(name, []):
            if entry["version"] == version:
                return entry
        return None

    def list_models(self) -> dict[str, list[str]]:
        """List all models and their versions."""
        return {
            name: [e["version"] for e in versions]
            for name, versions in self._registry["models"].items()
        }

    def set_active(self, name: str, version: str) -> bool:
        """Set the active version for a model."""
        for entry in self._registry["models"].get(name, []):
            if entry["version"] == version:
                self._registry["active"][name] = version
                self._save_registry()
                return True
        return False

    def get_model_path(self, name: str) -> Optional[Path]:
        """Get the file path for the active version of a model."""
        entry = self.get_active(name)
        if entry:
            return Path(entry["path"])
        return None

    # ------------------------------------------------------------------ #
    #  A/B Testing
    # ------------------------------------------------------------------ #

    def split_traffic(
        self,
        model_a: str,
        model_b: str,
        split_ratio: float = 0.5,
    ) -> dict[str, Any]:
        """Set up an A/B test: route *split_ratio* of traffic to model_a, rest to model_b.

        Args:
            model_a: Primary model name.
            model_b: Challenger model name.
            split_ratio: Fraction of requests routed to model_a (0.0–1.0).

        Returns:
            The A/B test configuration dict.
        """
        if not (0.0 <= split_ratio <= 1.0):
            raise ValueError(f"split_ratio must be between 0 and 1, got {split_ratio}")
        if model_a not in self._registry["models"]:
            raise ValueError(f"Model '{model_a}' not found in registry")
        if model_b not in self._registry["models"]:
            raise ValueError(f"Model '{model_b}' not found in registry")

        config = {
            "opponent": model_b,
            "ratio": split_ratio,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        self.ab_tests[model_a] = config
        logger.info(
            "A/B test started: %s (%.0f%%) vs %s (%.0f%%)",
            model_a, split_ratio * 100, model_b, (1 - split_ratio) * 100,
        )
        return config

    def route_request(self, model_name: str) -> str:
        """Decide which model to use for a request based on active A/B tests.

        Args:
            model_name: The logical model name requested.

        Returns:
            The actual model name to use (may be the original or its A/B opponent).
        """
        if model_name in self.ab_tests:
            test = self.ab_tests[model_name]
            chosen = model_name if random.random() < test["ratio"] else test["opponent"]
            logger.debug("A/B route: %s -> %s", model_name, chosen)
            return chosen
        return model_name

    def stop_ab_test(self, model_name: str) -> bool:
        """Stop an active A/B test for a model.

        Args:
            model_name: The primary model name of the test.

        Returns:
            True if a test was removed, False if none was active.
        """
        removed = self.ab_tests.pop(model_name, None)
        if removed:
            logger.info("A/B test stopped for %s", model_name)
            return True
        return False

    def get_ab_tests(self) -> dict[str, dict[str, Any]]:
        """Return a snapshot of all active A/B tests."""
        return dict(self.ab_tests)

    # ------------------------------------------------------------------ #
    #  Rollback
    # ------------------------------------------------------------------ #

    def rollback(self, model_name: str, to_version: str, reason: str = "manual") -> bool:
        """Rollback a model to a specific previous version.

        Args:
            model_name: Name of the model to rollback.
            to_version: Target version string.
            reason: Audit reason ("manual" or "auto_degradation").

        Returns:
            True if rollback succeeded, False if version not found.
        """
        versions = self._registry["models"].get(model_name, [])
        for entry in versions:
            if entry["version"] == to_version:
                previous_version = self._registry["active"].get(model_name)
                self._registry["active"][model_name] = to_version
                self._save_registry()
                self._log_rollback(model_name, to_version, previous_version, reason=reason)
                logger.info(
                    "Rolled back %s from v%s to v%s (reason=%s)",
                    model_name, previous_version, to_version, reason,
                )
                return True
        logger.warning(
            "Rollback failed: version %s not found for model %s",
            to_version, model_name,
        )
        return False

    def _log_rollback(
        self,
        model_name: str,
        to_version: str,
        from_version: Optional[str] = None,
        reason: str = "manual",
    ) -> None:
        """Append an entry to the rollback audit log."""
        self.rollback_log.append({
            "model": model_name,
            "from_version": from_version,
            "to_version": to_version,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_previous_version(self, model_name: str) -> Optional[str]:
        """Return the version string that was active *before* the current one.

        Looks at the rollback log first, then falls back to second-to-last entry
        in the model's version list.
        """
        # Check rollback log for prior version
        for entry in reversed(self.rollback_log):
            if entry["model"] == model_name:
                return entry["from_version"]
        # Fall back: second-to-last registered version
        versions = self._registry["models"].get(model_name, [])
        if len(versions) >= 2:
            return versions[-2]["version"]
        return None

    def get_rollback_history(self, model_name: Optional[str] = None) -> list[dict[str, Any]]:
        """Return rollback log entries, optionally filtered by model name."""
        if model_name:
            return [e for e in self.rollback_log if e["model"] == model_name]
        return list(self.rollback_log)

    # ------------------------------------------------------------------ #
    #  Performance Tracking & Auto-Rollback
    # ------------------------------------------------------------------ #

    def record_performance(
        self,
        model_name: str,
        metrics: dict[str, float],
        version: Optional[str] = None,
    ) -> None:
        """Record a performance measurement for a model version.

        Args:
            model_name: Model name.
            metrics: Dict of metric name -> value (e.g. {"accuracy": 0.95, "latency_ms": 12}).
            version: Specific version (defaults to current active version).
        """
        if version is None:
            version = self._registry["active"].get(model_name)
        if model_name not in self.performance_history:
            self.performance_history[model_name] = []
        self.performance_history[model_name].append({
            "version": version,
            "metrics": metrics,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_performance(
        self,
        model_name: str,
        metric_name: Optional[str] = None,
        last_n: int = 5,
    ) -> Optional[float]:
        """Get average performance for the current active version.

        Args:
            model_name: Model name.
            metric_name: Specific metric to return (first metric if None).
            last_n: Number of recent measurements to average.

        Returns:
            Average metric value, or None if no data.
        """
        history = self.performance_history.get(model_name, [])
        if not history:
            return None
        active_version = self._registry["active"].get(model_name)
        relevant = [
            h for h in history if h["version"] == active_version
        ][-last_n:]
        if not relevant:
            return None
        if metric_name:
            values = [h["metrics"][metric_name] for h in relevant if metric_name in h["metrics"]]
        else:
            # Use the first available metric
            values = [list(h["metrics"].values())[0] for h in relevant if h["metrics"]]
        return sum(values) / len(values) if values else None

    def auto_rollback_on_degradation(
        self,
        model_name: str,
        metric_name: str,
        metric_threshold: float,
        last_n: int = 5,
    ) -> Optional[str]:
        """Auto-rollback if the active model's performance drops below a threshold.

        Args:
            model_name: Model name.
            metric_name: Metric to check (e.g. "accuracy").
            metric_threshold: Minimum acceptable value.
            last_n: Number of recent measurements to average.

        Returns:
            The version rolled back to, or None if no rollback was needed.
        """
        current_perf = self.get_performance(model_name, metric_name, last_n)
        if current_perf is None:
            logger.warning(
                "No performance data for %s; skipping auto-rollback check.", model_name,
            )
            return None

        if current_perf >= metric_threshold:
            logger.debug(
                "%s performance (%.4f) is above threshold (%.4f); no rollback.",
                model_name, current_perf, metric_threshold,
            )
            return None

        logger.warning(
            "%s performance (%.4f) dropped below threshold (%.4f); initiating rollback.",
            model_name, current_perf, metric_threshold,
        )
        previous = self.get_previous_version(model_name)
        if previous is None:
            logger.error("No previous version found for %s; cannot rollback.", model_name)
            return None

        self.rollback(model_name, previous, reason="auto_degradation")
        return previous
