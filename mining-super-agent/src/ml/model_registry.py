"""
Model registry — versioned model storage and loading.
"""

from __future__ import annotations

import json
import logging
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
