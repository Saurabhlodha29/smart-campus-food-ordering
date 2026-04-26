"""
model_registry.py — In-memory + disk model registry for all ML models.

Design:
  - All trained model objects live in a Python dict keyed by (name, scope_id).
    scope_id is typically campus_id or outlet_id depending on the model.
  - Models are serialised to disk with joblib so they survive service restarts.
  - A threading.RLock protects concurrent reads/writes from APScheduler + HTTP handlers.

Usage:
    from model_registry import registry

    registry.save("recommender", campus_id=2, model=my_model)
    model = registry.load("recommender", campus_id=2)   # None if not trained yet
    registry.list_models()                               # all model names + timestamps
"""

import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import joblib

logger = logging.getLogger(__name__)

# Models are saved here — relative to the ml-service directory
MODELS_DIR = Path(os.getenv("MODELS_DIR", "./saved_models"))
METRICS_FILE = MODELS_DIR / "metrics.json"


class ModelRegistry:
    """
    Thread-safe singleton registry for trained ML models.

    Key format: "<name>__<scope_id>"  (e.g. "recommender__2", "wait_time__45")
    Use scope_id=0 for global models (e.g. no-show classifier).
    """

    _lock = threading.RLock()

    def __init__(self):
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        # In-memory cache: key → {"model": ..., "trained_at": ..., "metrics": ...}
        self._cache: dict[str, dict] = {}
        # Load all previously saved models from disk on startup
        self._load_all_from_disk()

    # ── Save ──────────────────────────────────────────────────────────────────

    def save(
        self,
        name: str,
        model: Any,
        scope_id: int = 0,
        metrics: Optional[dict] = None,
    ) -> None:
        """
        Save a model to memory and disk.

        Args:
            name:     Model identifier (e.g. "recommender", "wait_time")
            model:    Any pickle-able Python object (sklearn model, dict, etc.)
            scope_id: campus_id or outlet_id. Use 0 for global models.
            metrics:  Optional dict of performance metrics (RMSE, AUC, etc.)
        """
        key = self._key(name, scope_id)
        timestamp = datetime.now().isoformat()
        entry = {
            "model": model,
            "trained_at": timestamp,
            "metrics": metrics or {},
            "name": name,
            "scope_id": scope_id,
        }

        with self._lock:
            self._cache[key] = entry
            # Persist to disk
            disk_path = MODELS_DIR / f"{key}.joblib"
            joblib.dump(entry, disk_path)
            logger.info("[registry] Saved model '%s' (scope=%s) → %s", name, scope_id, disk_path)

        # Update metrics file
        self._append_metrics(name, scope_id, timestamp, metrics or {})

    # ── Load ──────────────────────────────────────────────────────────────────

    def load(self, name: str, scope_id: int = 0) -> Optional[Any]:
        """
        Load a model. Returns None if model hasn't been trained yet.
        Checks memory cache first, then disk.
        """
        key = self._key(name, scope_id)

        with self._lock:
            if key in self._cache:
                return self._cache[key]["model"]

            # Try loading from disk (happens after restart)
            disk_path = MODELS_DIR / f"{key}.joblib"
            if disk_path.exists():
                try:
                    entry = joblib.load(disk_path)
                    self._cache[key] = entry
                    logger.info("[registry] Loaded '%s' (scope=%s) from disk", name, scope_id)
                    return entry["model"]
                except Exception as exc:
                    logger.error("[registry] Failed to load %s from disk: %s", disk_path, exc)

        return None

    # ── Check ─────────────────────────────────────────────────────────────────

    def is_trained(self, name: str, scope_id: int = 0) -> bool:
        """Return True if a trained model exists (memory or disk)."""
        return self.load(name, scope_id) is not None

    def trained_at(self, name: str, scope_id: int = 0) -> Optional[str]:
        """Return ISO timestamp of when the model was last trained, or None."""
        key = self._key(name, scope_id)
        with self._lock:
            entry = self._cache.get(key)
            if entry:
                return entry.get("trained_at")
        return None

    # ── List ──────────────────────────────────────────────────────────────────

    def list_models(self) -> list[dict]:
        """Return summary of all models in memory."""
        with self._lock:
            return [
                {
                    "name": v["name"],
                    "scope_id": v["scope_id"],
                    "trained_at": v["trained_at"],
                    "metrics": v.get("metrics", {}),
                }
                for v in self._cache.values()
            ]

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _key(name: str, scope_id: int) -> str:
        return f"{name}__{scope_id}"

    def _load_all_from_disk(self) -> None:
        """Load all .joblib files from disk into memory cache on startup."""
        count = 0
        for path in MODELS_DIR.glob("*.joblib"):
            try:
                entry = joblib.load(path)
                key = path.stem  # filename without .joblib
                with self._lock:
                    self._cache[key] = entry
                count += 1
            except Exception as exc:
                logger.warning("[registry] Could not load %s: %s", path, exc)
        if count:
            logger.info("[registry] Loaded %d models from disk on startup", count)

    def _append_metrics(
        self, name: str, scope_id: int, timestamp: str, metrics: dict
    ) -> None:
        """Append model performance metrics to metrics.json for monitoring."""
        try:
            existing = {}
            if METRICS_FILE.exists():
                with open(METRICS_FILE) as f:
                    existing = json.load(f)

            key = self._key(name, scope_id)
            if key not in existing:
                existing[key] = []

            existing[key].append({"trained_at": timestamp, **metrics})
            # Keep only last 50 entries per model
            existing[key] = existing[key][-50:]

            with open(METRICS_FILE, "w") as f:
                json.dump(existing, f, indent=2)
        except Exception as exc:
            logger.warning("[registry] Could not update metrics.json: %s", exc)


# Singleton — import this in all routers
registry = ModelRegistry()