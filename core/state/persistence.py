"""Workflow state persistence to database and cache."""

from typing import Any, Dict, Optional
from abc import ABC, abstractmethod
import json
from datetime import datetime

import structlog

logger = structlog.get_logger(__name__)


class PersistenceBackend(ABC):
    """Abstract base for persistence backends."""

    @abstractmethod
    def save(self, key: str, data: Dict[str, Any]) -> bool:
        """Save data to backend."""
        pass

    @abstractmethod
    def load(self, key: str) -> Optional[Dict[str, Any]]:
        """Load data from backend."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete data from backend."""
        pass

    @abstractmethod
    def list_keys(self, pattern: Optional[str] = None) -> list:
        """List all keys, optionally filtered by pattern."""
        pass


class InMemoryBackend(PersistenceBackend):
    """In-memory persistence backend for development/testing."""

    def __init__(self):
        """Initialize in-memory storage."""
        self._storage: Dict[str, Dict[str, Any]] = {}

    def save(self, key: str, data: Dict[str, Any]) -> bool:
        """Save data to memory."""
        self._storage[key] = data.copy()
        return True

    def load(self, key: str) -> Optional[Dict[str, Any]]:
        """Load data from memory."""
        return self._storage.get(key)

    def delete(self, key: str) -> bool:
        """Delete data from memory."""
        if key in self._storage:
            del self._storage[key]
            return True
        return False

    def list_keys(self, pattern: Optional[str] = None) -> list:
        """List all keys."""
        keys = list(self._storage.keys())
        if pattern:
            keys = [k for k in keys if pattern in k]
        return keys


class FileBackend(PersistenceBackend):
    """File-based persistence backend using JSON."""

    def __init__(self, base_path: str = "/tmp/workflow_states"):
        """
        Initialize file-based backend.

        Args:
            base_path: Base directory for state files
        """
        import os

        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    def _get_file_path(self, key: str) -> str:
        """Get file path for a key."""
        import os

        return os.path.join(self.base_path, f"{key}.json")

    def save(self, key: str, data: Dict[str, Any]) -> bool:
        """Save data to file."""
        try:
            file_path = self._get_file_path(key)
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
            return True
        except Exception as e:
            logger.error("file_persistence_save_failed", key=key, error=str(e))
            return False

    def load(self, key: str) -> Optional[Dict[str, Any]]:
        """Load data from file."""
        try:
            file_path = self._get_file_path(key)
            with open(file_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.error("file_persistence_load_failed", key=key, error=str(e))
            return None

    def delete(self, key: str) -> bool:
        """Delete data from file."""
        try:
            import os

            file_path = self._get_file_path(key)
            if os.path.exists(file_path):
                os.remove(file_path)
            return True
        except Exception as e:
            logger.error("file_persistence_delete_failed", key=key, error=str(e))
            return False

    def list_keys(self, pattern: Optional[str] = None) -> list:
        """List all keys from files."""
        try:
            import os

            files = os.listdir(self.base_path)
            keys = [f[:-5] for f in files if f.endswith(".json")]
            if pattern:
                keys = [k for k in keys if pattern in k]
            return keys
        except Exception as e:
            logger.error("file_persistence_list_failed", error=str(e))
            return []


class StatePersistence:
    """Manages persistence of workflow state to multiple backends."""

    def __init__(self, primary_backend: Optional[PersistenceBackend] = None):
        """
        Initialize state persistence.

        Args:
            primary_backend: Primary persistence backend
        """
        self.primary_backend = primary_backend or InMemoryBackend()
        self.secondary_backends = []
        self._cache = {}

    def add_secondary_backend(self, backend: PersistenceBackend) -> None:
        """
        Add a secondary persistence backend for redundancy.

        Args:
            backend: Backend to add
        """
        self.secondary_backends.append(backend)
        logger.info("secondary_backend_added")

    def save_workflow_state(self, workflow_id: str, state_data: Dict[str, Any]) -> bool:
        """
        Save workflow state to persistence backends.

        Args:
            workflow_id: Workflow identifier
            state_data: State data to save

        Returns:
            True if save successful
        """
        key = f"workflow_{workflow_id}"
        data = {
            "workflow_id": workflow_id,
            "state": state_data,
            "persisted_at": datetime.utcnow().isoformat(),
        }

        success = self.primary_backend.save(key, data)

        # Save to secondary backends for redundancy
        for backend in self.secondary_backends:
            try:
                backend.save(key, data)
            except Exception as e:
                logger.warning(
                    "secondary_backend_save_failed",
                    backend_type=type(backend).__name__,
                    error=str(e),
                )

        if success:
            self._cache[workflow_id] = state_data

        logger.info("workflow_state_persisted", workflow_id=workflow_id)
        return success

    def load_workflow_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Load workflow state from persistence.

        Args:
            workflow_id: Workflow identifier

        Returns:
            State data or None if not found
        """
        # Check cache first
        if workflow_id in self._cache:
            return self._cache[workflow_id]

        key = f"workflow_{workflow_id}"

        # Try primary backend first
        data = self.primary_backend.load(key)

        if data:
            state_data = data.get("state")
            if state_data:
                self._cache[workflow_id] = state_data
                logger.info("workflow_state_loaded", workflow_id=workflow_id)
                return state_data

        # Try secondary backends if primary fails
        for backend in self.secondary_backends:
            try:
                data = backend.load(key)
                if data:
                    state_data = data.get("state")
                    if state_data:
                        # Write back to primary for resilience
                        self.primary_backend.save(key, data)
                        self._cache[workflow_id] = state_data
                        logger.info(
                            "workflow_state_recovered_from_secondary",
                            workflow_id=workflow_id,
                        )
                        return state_data
            except Exception as e:
                logger.warning(
                    "secondary_backend_load_failed",
                    backend_type=type(backend).__name__,
                    error=str(e),
                )

        logger.warning("workflow_state_not_found", workflow_id=workflow_id)
        return None

    def delete_workflow_state(self, workflow_id: str) -> bool:
        """
        Delete workflow state from persistence.

        Args:
            workflow_id: Workflow identifier

        Returns:
            True if deletion successful
        """
        key = f"workflow_{workflow_id}"
        success = self.primary_backend.delete(key)

        for backend in self.secondary_backends:
            try:
                backend.delete(key)
            except Exception as e:
                logger.warning(
                    "secondary_backend_delete_failed",
                    backend_type=type(backend).__name__,
                    error=str(e),
                )

        if workflow_id in self._cache:
            del self._cache[workflow_id]

        logger.info("workflow_state_deleted", workflow_id=workflow_id)
        return success

    def list_workflow_states(self) -> list:
        """
        List all persisted workflow states.

        Returns:
            List of workflow IDs
        """
        keys = self.primary_backend.list_keys("workflow_")
        return [k.replace("workflow_", "") for k in keys]

    def clear_cache(self) -> None:
        """Clear in-memory cache."""
        self._cache.clear()
        logger.info("persistence_cache_cleared")

    def cleanup_old_states(self, days_old: int = 30) -> int:
        """
        Clean up old workflow states.

        Args:
            days_old: Age threshold in days

        Returns:
            Number of states deleted
        """
        deleted_count = 0
        threshold = datetime.utcnow().timestamp() - (days_old * 24 * 3600)

        for workflow_id in self.list_workflow_states():
            state = self.load_workflow_state(workflow_id)
            if state:
                # Parse timestamp and check age
                created_at_str = state.get("created_at")
                if created_at_str:
                    created_at = datetime.fromisoformat(created_at_str)
                    if created_at.timestamp() < threshold:
                        if self.delete_workflow_state(workflow_id):
                            deleted_count += 1

        logger.info("old_states_cleaned_up", deleted_count=deleted_count)
        return deleted_count
