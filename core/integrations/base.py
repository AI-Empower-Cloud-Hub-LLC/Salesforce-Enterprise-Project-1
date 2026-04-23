"""Abstract base classes for integrations."""

from typing import Any, Dict, Optional, List
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class IntegrationResult:
    """Result of an integration operation."""

    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    timestamp: str = None
    operation_id: Optional[str] = None

    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


class IntegrationBackend(ABC):
    """Abstract base for integration backends."""

    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize integration backend.

        Args:
            name: Name of the integration
            config: Configuration dictionary
        """
        self.name = name
        self.config = config
        self._is_healthy = True

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the external service."""
        pass

    @abstractmethod
    def execute_query(
        self, query: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> IntegrationResult:
        """
        Execute a query or operation.

        Args:
            query: Query/operation specification
            context: Optional execution context

        Returns:
            IntegrationResult with operation outcome
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if integration is healthy.

        Returns:
            True if healthy, False otherwise
        """
        pass

    @abstractmethod
    def list_resources(self, resource_type: str) -> List[Dict[str, Any]]:
        """
        List available resources of a given type.

        Args:
            resource_type: Type of resource to list

        Returns:
            List of available resources
        """
        pass

    def get_status(self) -> Dict[str, Any]:
        """
        Get integration status.

        Returns:
            Status dictionary
        """
        return {
            "name": self.name,
            "healthy": self.health_check(),
            "authenticated": self._is_healthy,
            "last_check": datetime.utcnow().isoformat(),
        }


class MultiBackendIntegration:
    """Base class for integrations with primary/fallback backends."""

    def __init__(
        self,
        primary_backend: IntegrationBackend,
        name: str = "integration",
    ):
        """
        Initialize multi-backend integration.

        Args:
            primary_backend: Primary integration backend
            name: Integration name
        """
        self.name = name
        self.primary_backend = primary_backend
        self.fallback_backends: List[IntegrationBackend] = []
        self._operation_history: List[Dict[str, Any]] = []

    def add_fallback_backend(self, backend: IntegrationBackend) -> None:
        """
        Add fallback backend for redundancy.

        Args:
            backend: Fallback backend to add
        """
        self.fallback_backends.append(backend)
        logger.info(
            "fallback_backend_added",
            integration=self.name,
            backend_name=backend.name,
        )

    def execute(
        self, query: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> IntegrationResult:
        """
        Execute query with fallback support.

        Args:
            query: Query specification
            context: Optional context

        Returns:
            IntegrationResult
        """
        operation_id = f"{self.name}_{datetime.utcnow().timestamp()}"

        # Try primary backend
        if self.primary_backend.health_check():
            try:
                result = self.primary_backend.execute_query(query, context)
                result.operation_id = operation_id
                self._log_operation(operation_id, result, "primary")
                return result
            except Exception as e:
                logger.warning(
                    "primary_backend_failed",
                    integration=self.name,
                    error=str(e),
                )

        # Try fallback backends
        for backend in self.fallback_backends:
            try:
                if backend.health_check():
                    result = backend.execute_query(query, context)
                    result.operation_id = operation_id
                    self._log_operation(operation_id, result, backend.name)
                    logger.info(
                        "fallback_backend_succeeded",
                        integration=self.name,
                        backend_name=backend.name,
                    )
                    return result
            except Exception as e:
                logger.warning(
                    "fallback_backend_failed",
                    integration=self.name,
                    backend_name=backend.name,
                    error=str(e),
                )

        logger.error(
            "all_backends_failed",
            integration=self.name,
            operation_id=operation_id,
        )
        return IntegrationResult(
            success=False,
            error="All integration backends failed",
            operation_id=operation_id,
        )

    def authenticate(self) -> bool:
        """
        Authenticate primary backend (and fallbacks if needed).

        Returns:
            True if at least primary backend authenticated
        """
        try:
            if self.primary_backend.authenticate():
                logger.info("primary_backend_authenticated", integration=self.name)
                return True
        except Exception as e:
            logger.warning(
                "primary_backend_auth_failed",
                integration=self.name,
                error=str(e),
            )

        return False

    def health_check(self) -> Dict[str, bool]:
        """
        Check health of all backends.

        Returns:
            Dictionary with backend health status
        """
        status = {
            "primary": self.primary_backend.health_check(),
        }

        for backend in self.fallback_backends:
            try:
                status[backend.name] = backend.health_check()
            except Exception as e:
                logger.warning(
                    "backend_health_check_failed",
                    backend_name=backend.name,
                    error=str(e),
                )
                status[backend.name] = False

        return status

    def _log_operation(
        self, operation_id: str, result: IntegrationResult, backend_name: str
    ) -> None:
        """
        Log operation to history.

        Args:
            operation_id: Operation identifier
            result: Operation result
            backend_name: Backend that executed operation
        """
        self._operation_history.append(
            {
                "operation_id": operation_id,
                "success": result.success,
                "backend": backend_name,
                "timestamp": result.timestamp,
                "error": result.error,
            }
        )

    def get_operation_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get operation history.

        Args:
            limit: Maximum number of operations to return

        Returns:
            List of recent operations
        """
        return self._operation_history[-limit:]

    def reset(self) -> None:
        """Reset integration state."""
        self._operation_history.clear()
        logger.info("integration_reset", integration=self.name)
