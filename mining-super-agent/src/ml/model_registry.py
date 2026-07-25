"""
Model Registry — Versioning, A/B Testing, Performance Tracking, Auto-Rollback
==============================================================================
Manages model lifecycle: version control, deployment, monitoring, and rollback.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)


class ModelStatus(Enum):
    """Model deployment status."""
    TRAINING = "training"
    VALIDATION = "validation"
    STAGED = "staged"           # Ready but not deployed
    ACTIVE = "active"           # Serving predictions
    SHADOW = "shadow"           # Running in parallel, not serving
    ROLLBACK = "rollback"       # Rolled back due to degradation
    ARCHIVED = "archived"


class ABTestStrategy(Enum):
    """A/B testing strategies."""
    PERCENTAGE = "percentage"       # Random percentage split
    ROUND_ROBIN = "round_robin"     # Alternate between models
    CANARY = "canary"               # New model gets small % of traffic


@dataclass
class ModelVersion:
    """A registered model version."""
    model_id: str
    version: str
    status: ModelStatus
    created_at: str
    description: str = ""
    metrics: Dict[str, float] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    artifact_path: Optional[str] = None
    checksum: Optional[str] = None
    training_config: Dict[str, Any] = field(default_factory=dict)
    parent_version: Optional[str] = None
    deployed_at: Optional[str] = None
    rollback_from: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "version": self.version,
            "status": self.status.value,
            "created_at": self.created_at,
            "description": self.description,
            "metrics": self.metrics,
            "tags": self.tags,
            "artifact_path": self.artifact_path,
            "checksum": self.checksum,
            "training_config": self.training_config,
            "parent_version": self.parent_version,
            "deployed_at": self.deployed_at,
            "rollback_from": self.rollback_from,
        }


@dataclass
class PerformanceRecord:
    """Performance tracking record."""
    timestamp: str
    model_id: str
    version: str
    metric_name: str
    metric_value: float
    sample_size: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ABTestConfig:
    """A/B test configuration."""
    test_id: str
    model_a: str               # version
    model_b: str               # version
    strategy: ABTestStrategy
    split_ratio: float = 0.5   # Traffic to model_b (0.0-1.0)
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    winner: Optional[str] = None
    metrics_a: Dict[str, float] = field(default_factory=dict)
    metrics_b: Dict[str, float] = field(default_factory=dict)


class ModelRegistry:
    """
    Model lifecycle management.

    Features:
    - Version tracking with checksums
    - A/B testing with multiple strategies
    - Performance monitoring over time
    - Automatic rollback on metric degradation
    """

    def __init__(
        self,
        registry_dir: Union[str, Path],
        rollback_threshold: float = 0.05,  # 5% metric drop triggers rollback
        min_samples_for_rollback: int = 50,
    ):
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)

        self.rollback_threshold = rollback_threshold
        self.min_samples_for_rollback = min_samples_for_rollback

        # In-memory state
        self.models: Dict[str, Dict[str, ModelVersion]] = {}  # model_id → {version → ModelVersion}
        self.performance_history: List[PerformanceRecord] = []
        self.ab_tests: Dict[str, ABTestConfig] = {}

        # Load existing registry
        self._load_registry()

    # ── Registration ────────────────────────────────────────────────────────

    def register_model(
        self,
        model_id: str,
        version: str,
        artifact_path: Union[str, Path],
        description: str = "",
        metrics: Optional[Dict[str, float]] = None,
        tags: Optional[Dict[str, str]] = None,
        training_config: Optional[Dict[str, Any]] = None,
        parent_version: Optional[str] = None,
    ) -> ModelVersion:
        """
        Register a new model version.
        Computes checksum of the artifact for integrity verification.
        """
        artifact_path = Path(artifact_path)
        if not artifact_path.exists():
            raise FileNotFoundError(f"Model artifact not found: {artifact_path}")

        # Compute checksum
        checksum = self._compute_checksum(artifact_path)

        mv = ModelVersion(
            model_id=model_id,
            version=version,
            status=ModelStatus.STAGED,
            created_at=datetime.now(timezone.utc).isoformat(),
            description=description,
            metrics=metrics or {},
            tags=tags or {},
            artifact_path=str(artifact_path),
            checksum=checksum,
            training_config=training_config or {},
            parent_version=parent_version,
        )

        if model_id not in self.models:
            self.models[model_id] = {}

        self.models[model_id][version] = mv
        self._save_registry()

        logger.info("Registered model %s v%s (checksum: %s)", model_id, version, checksum[:12])
        return mv

    def get_model(self, model_id: str, version: Optional[str] = None) -> ModelVersion:
        """Get a model version. If version is None, returns the active version."""
        if model_id not in self.models:
            raise KeyError(f"Model not found: {model_id}")

        if version is None:
            # Find active version
            for mv in self.models[model_id].values():
                if mv.status == ModelStatus.ACTIVE:
                    return mv
            raise KeyError(f"No active version for model: {model_id}")

        if version not in self.models[model_id]:
            raise KeyError(f"Version {version} not found for model {model_id}")

        return self.models[model_id][version]

    def list_versions(self, model_id: str) -> List[ModelVersion]:
        """List all versions of a model."""
        if model_id not in self.models:
            return []
        return list(self.models[model_id].values())

    # ── Deployment ──────────────────────────────────────────────────────────

    def deploy(
        self,
        model_id: str,
        version: str,
        shadow: bool = False,
    ) -> ModelVersion:
        """
        Deploy a model version. Deactivates the current active version.
        If shadow=True, runs in shadow mode (parallel but not serving).
        """
        mv = self.get_model(model_id, version)

        # Verify integrity
        if mv.artifact_path and not self._verify_checksum(mv.artifact_path, mv.checksum):
            raise ValueError(f"Checksum mismatch for {model_id} v{version} — artifact corrupted!")

        if shadow:
            mv.status = ModelStatus.SHADOW
            logger.info("Deployed %s v%s in SHADOW mode", model_id, version)
        else:
            # Deactivate current active version
            for v in self.models[model_id].values():
                if v.status == ModelStatus.ACTIVE:
                    v.status = ModelStatus.ARCHIVED
                    logger.info("Archived %s v%s", model_id, v.version)

            mv.status = ModelStatus.ACTIVE
            mv.deployed_at = datetime.now(timezone.utc).isoformat()
            logger.info("Deployed %s v%s as ACTIVE", model_id, version)

        self._save_registry()
        return mv

    # ── Performance Tracking ────────────────────────────────────────────────

    def record_performance(
        self,
        model_id: str,
        version: str,
        metric_name: str,
        metric_value: float,
        sample_size: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record a performance metric for a model version."""
        record = PerformanceRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            model_id=model_id,
            version=version,
            metric_name=metric_name,
            metric_value=metric_value,
            sample_size=sample_size,
            metadata=metadata or {},
        )
        self.performance_history.append(record)

        # Update model metrics
        try:
            mv = self.get_model(model_id, version)
            mv.metrics[metric_name] = metric_value
        except KeyError:
            pass

        # Check for degradation
        self._check_degradation(model_id, version, metric_name)

        self._save_registry()

    def get_performance_history(
        self,
        model_id: str,
        version: Optional[str] = None,
        metric_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[PerformanceRecord]:
        """Get performance history with optional filters."""
        records = self.performance_history

        if model_id:
            records = [r for r in records if r.model_id == model_id]
        if version:
            records = [r for r in records if r.version == version]
        if metric_name:
            records = [r for r in records if r.metric_name == metric_name]

        return records[-limit:]

    # ── A/B Testing ─────────────────────────────────────────────────────────

    def start_ab_test(
        self,
        test_id: str,
        model_id: str,
        version_a: str,
        version_b: str,
        strategy: ABTestStrategy = ABTestStrategy.PERCENTAGE,
        split_ratio: float = 0.5,
    ) -> ABTestConfig:
        """Start an A/B test between two model versions."""
        config = ABTestConfig(
            test_id=test_id,
            model_a=version_a,
            model_b=version_b,
            strategy=strategy,
            split_ratio=split_ratio,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self.ab_tests[test_id] = config
        self._save_registry()

        logger.info(
            "A/B test '%s' started: %s v%s vs v%s (%.0f%% split)",
            test_id, model_id, version_a, version_b, split_ratio * 100,
        )
        return config

    def route_ab_test(self, test_id: str, request_id: Optional[str] = None) -> str:
        """
        Route a request to model A or B based on the A/B test strategy.
        Returns the version to use.
        """
        if test_id not in self.ab_tests:
            raise KeyError(f"A/B test not found: {test_id}")

        config = self.ab_tests[test_id]

        if config.ended_at:
            # Test is over, use the winner
            return config.winner or config.model_a

        if config.strategy == ABTestStrategy.PERCENTAGE:
            # Random split
            import random
            return config.model_b if random.random() < config.split_ratio else config.model_a

        elif config.strategy == ABTestStrategy.ROUND_ROBIN:
            # Alternate based on request_id hash
            hash_val = int(hashlib.md5(
                (request_id or str(time.time())).encode()
            ).hexdigest(), 16)
            return config.model_b if hash_val % 2 == 0 else config.model_a

        elif config.strategy == ABTestStrategy.CANARY:
            # Small percentage to new model
            import random
            return config.model_b if random.random() < config.split_ratio else config.model_a

        return config.model_a

    def end_ab_test(self, test_id: str, winner: Optional[str] = None) -> ABTestConfig:
        """End an A/B test and optionally declare a winner."""
        config = self.ab_tests[test_id]
        config.ended_at = datetime.now(timezone.utc).isoformat()

        if winner:
            config.winner = winner
        else:
            # Auto-determine winner based on recorded metrics
            if config.metrics_b.get("accuracy", 0) > config.metrics_a.get("accuracy", 0):
                config.winner = config.model_b
            else:
                config.winner = config.model_a

        logger.info("A/B test '%s' ended. Winner: %s", test_id, config.winner)
        self._save_registry()
        return config

    # ── Automatic Rollback ──────────────────────────────────────────────────

    def _check_degradation(self, model_id: str, version: str, metric_name: str):
        """Check if model performance has degraded and trigger rollback if needed."""
        # Get recent performance records for this version
        recent = [
            r for r in self.performance_history
            if r.model_id == model_id and r.version == version and r.metric_name == metric_name
        ]

        if len(recent) < self.min_samples_for_rollback:
            return

        # Compare recent performance to historical baseline
        current_value = np.mean([r.metric_value for r in recent[-20:]])
        baseline_value = np.mean([r.metric_value for r in recent[:20]])

        if baseline_value <= 0:
            return

        degradation = (baseline_value - current_value) / baseline_value

        if degradation > self.rollback_threshold:
            logger.warning(
                "DEGRADATION DETECTED: %s v%s — %s dropped by %.1f%% (%.4f → %.4f)",
                model_id, version, metric_name, degradation * 100,
                baseline_value, current_value,
            )
            self._auto_rollback(model_id, version, metric_name, degradation)

    def _auto_rollback(self, model_id: str, version: str, metric_name: str, degradation: float):
        """Automatically rollback to the previous version."""
        mv = self.models[model_id].get(version)
        if not mv or mv.status != ModelStatus.ACTIVE:
            return

        # Find the parent version or most recent archived version
        parent = mv.parent_version
        rollback_target = None

        if parent and parent in self.models[model_id]:
            rollback_target = self.models[model_id][parent]
        else:
            # Find most recently archived version
            archived = [
                v for v in self.models[model_id].values()
                if v.status == ModelStatus.ARCHIVED
            ]
            if archived:
                archived.sort(key=lambda v: v.created_at, reverse=True)
                rollback_target = archived[0]

        if rollback_target:
            mv.status = ModelStatus.ROLLBACK
            mv.rollback_from = version
            rollback_target.status = ModelStatus.ACTIVE
            rollback_target.deployed_at = datetime.now(timezone.utc).isoformat()

            logger.critical(
                "AUTO-ROLLBACK: %s v%s → v%s (reason: %s degraded by %.1f%%)",
                model_id, version, rollback_target.version,
                metric_name, degradation * 100,
            )
            self._save_registry()
        else:
            logger.critical(
                "ROLLBACK FAILED: No previous version found for %s. Manual intervention required!",
                model_id,
            )

    # ── Persistence ─────────────────────────────────────────────────────────

    def _save_registry(self):
        """Save registry state to disk."""
        state = {
            "models": {
                mid: {v: mv.to_dict() for v, mv in versions.items()}
                for mid, versions in self.models.items()
            },
            "performance_history": [
                {
                    "timestamp": r.timestamp,
                    "model_id": r.model_id,
                    "version": r.version,
                    "metric_name": r.metric_name,
                    "metric_value": r.metric_value,
                    "sample_size": r.sample_size,
                }
                for r in self.performance_history[-1000:]  # Keep last 1000 records
            ],
            "ab_tests": {
                tid: {
                    "test_id": t.test_id,
                    "model_a": t.model_a,
                    "model_b": t.model_b,
                    "strategy": t.strategy.value,
                    "split_ratio": t.split_ratio,
                    "started_at": t.started_at,
                    "ended_at": t.ended_at,
                    "winner": t.winner,
                }
                for tid, t in self.ab_tests.items()
            },
        }

        registry_file = self.registry_dir / "registry.json"
        with open(registry_file, "w") as f:
            json.dump(state, f, indent=2)

    def _load_registry(self):
        """Load registry state from disk."""
        registry_file = self.registry_dir / "registry.json"
        if not registry_file.exists():
            return

        try:
            with open(registry_file) as f:
                state = json.load(f)

            # Restore models
            for mid, versions in state.get("models", {}).items():
                self.models[mid] = {}
                for v, mv_dict in versions.items():
                    mv = ModelVersion(
                        model_id=mv_dict["model_id"],
                        version=mv_dict["version"],
                        status=ModelStatus(mv_dict["status"]),
                        created_at=mv_dict["created_at"],
                        description=mv_dict.get("description", ""),
                        metrics=mv_dict.get("metrics", {}),
                        tags=mv_dict.get("tags", {}),
                        artifact_path=mv_dict.get("artifact_path"),
                        checksum=mv_dict.get("checksum"),
                        training_config=mv_dict.get("training_config", {}),
                        parent_version=mv_dict.get("parent_version"),
                        deployed_at=mv_dict.get("deployed_at"),
                        rollback_from=mv_dict.get("rollback_from"),
                    )
                    self.models[mid][v] = mv

            # Restore performance history
            for r in state.get("performance_history", []):
                self.performance_history.append(PerformanceRecord(**r))

            # Restore A/B tests
            for tid, t in state.get("ab_tests", {}).items():
                self.ab_tests[tid] = ABTestConfig(
                    test_id=t["test_id"],
                    model_a=t["model_a"],
                    model_b=t["model_b"],
                    strategy=ABTestStrategy(t["strategy"]),
                    split_ratio=t["split_ratio"],
                    started_at=t.get("started_at"),
                    ended_at=t.get("ended_at"),
                    winner=t.get("winner"),
                )

            logger.info("Loaded registry: %d models, %d performance records",
                        sum(len(v) for v in self.models.values()),
                        len(self.performance_history))

        except Exception as exc:
            logger.error("Failed to load registry: %s", exc)

    @staticmethod
    def _compute_checksum(path: Union[str, Path]) -> str:
        """Compute SHA-256 checksum of a file."""
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def _verify_checksum(path: Union[str, Path], expected: Optional[str]) -> bool:
        """Verify file checksum."""
        if not expected:
            return True
        actual = ModelRegistry._compute_checksum(path)
        return actual == expected
