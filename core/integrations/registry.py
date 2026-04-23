import structlog
from typing import Dict, List, Any, Optional, Type
from threading import RLock
from dataclasses import dataclass, field
from datetime import datetime

from core.integrations.base import IntegrationBackend, IntegrationResult

logger = structlog.get_logger(__name__)


@dataclass
class ConnectorRegistration:
    name: str
    connector_class: Type[IntegrationBackend]
    config: Dict[str, Any]
    instance: Optional[IntegrationBackend] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class HealthStatus:
    name: str
    is_healthy: bool
    last_check: datetime
    error_message: Optional[str] = None
    uptime_percentage: float = 100.0


class IntegrationRegistry:
    """Central registry for all integration connectors with lazy initialization and thread-safety."""

    def __init__(self):
        self._lock = RLock()
        self._connectors: Dict[str, ConnectorRegistration] = {}
        self._operation_history: List[Dict[str, Any]] = []

    def register(self, name: str, connector_class: Type[IntegrationBackend], config: Dict[str, Any]) -> None:
        """Register a new connector class with configuration. Lazy instantiation on first get()."""
        with self._lock:
            if name in self._connectors:
                logger.warn(f"Connector '{name}' already registered, overwriting", name=name)

            validation = self._validate_config(name, connector_class, config)
            if not validation.is_valid:
                logger.error(
                    "Invalid connector config",
                    name=name,
                    errors=validation.errors,
                )
                raise ValueError(f"Invalid config for '{name}': {', '.join(validation.errors)}")

            self._connectors[name] = ConnectorRegistration(
                name=name,
                connector_class=connector_class,
                config=config,
                instance=None,
            )

            logger.info(
                "Connector registered",
                name=name,
                connector_class=connector_class.__name__,
            )

            self._record_operation("register", name, {"connector_class": connector_class.__name__})

    def get(self, name: str) -> IntegrationBackend:
        """Get connector instance, creating it lazily on first access."""
        with self._lock:
            if name not in self._connectors:
                logger.error("Connector not found", name=name, available=list(self._connectors.keys()))
                raise ValueError(f"Connector '{name}' not registered")

            registration = self._connectors[name]
            registration.last_accessed = datetime.utcnow()
            registration.access_count += 1

            if registration.instance is None:
                logger.info("Instantiating connector", name=name)
                registration.instance = registration.connector_class(registration.config)

            self._record_operation("get", name, {"access_count": registration.access_count})
            return registration.instance

    def list_all(self) -> List[str]:
        """List all registered connector names."""
        with self._lock:
            return list(self._connectors.keys())

    def validate_config(self, name: str, config: Dict[str, Any]) -> ValidationResult:
        """Validate configuration for a registered connector type."""
        with self._lock:
            if name not in self._connectors:
                return ValidationResult(
                    is_valid=False,
                    errors=[f"Connector type '{name}' not registered"],
                )

            registration = self._connectors[name]
            return self._validate_config(name, registration.connector_class, config)

    def _validate_config(self, name: str, connector_class: Type[IntegrationBackend], config: Dict[str, Any]) -> ValidationResult:
        """Internal validation logic for connector configs."""
        errors = []
        warnings = []

        if not isinstance(config, dict):
            errors.append("Config must be a dictionary")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        required_keys = getattr(connector_class, "REQUIRED_CONFIG_KEYS", [])
        for key in required_keys:
            if key not in config:
                errors.append(f"Missing required config key: {key}")

        if not errors and hasattr(connector_class, "validate_config"):
            result = connector_class.validate_config(config)
            if isinstance(result, ValidationResult):
                return result

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    async def health_check(self) -> Dict[str, HealthStatus]:
        """Check health of all registered connectors."""
        health_results = {}

        with self._lock:
            connector_names = list(self._connectors.keys())

        for name in connector_names:
            try:
                connector = self.get(name)
                is_healthy = await connector.health_check()

                health_results[name] = HealthStatus(
                    name=name,
                    is_healthy=is_healthy,
                    last_check=datetime.utcnow(),
                    error_message=None,
                )

                logger.info("Health check passed", name=name, is_healthy=is_healthy)
            except Exception as e:
                logger.error("Health check failed", name=name, error=str(e))

                health_results[name] = HealthStatus(
                    name=name,
                    is_healthy=False,
                    last_check=datetime.utcnow(),
                    error_message=str(e),
                    uptime_percentage=0.0,
                )

        self._record_operation("health_check", "all", {"results": {k: v.is_healthy for k, v in health_results.items()}})
        return health_results

    def get_connector_info(self, name: str) -> Dict[str, Any]:
        """Get metadata about a registered connector."""
        with self._lock:
            if name not in self._connectors:
                raise ValueError(f"Connector '{name}' not registered")

            registration = self._connectors[name]
            return {
                "name": name,
                "connector_class": registration.connector_class.__name__,
                "created_at": registration.created_at.isoformat(),
                "last_accessed": registration.last_accessed.isoformat(),
                "access_count": registration.access_count,
                "is_instantiated": registration.instance is not None,
            }

    def get_operation_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get operation history for audit trail."""
        with self._lock:
            return self._operation_history[-limit:]

    def _record_operation(self, operation: str, target: str, details: Dict[str, Any] = None) -> None:
        """Record operation for audit trail."""
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "target": target,
            "details": details or {},
        }
        self._operation_history.append(record)

        if len(self._operation_history) > 10000:
            self._operation_history = self._operation_history[-5000:]

    async def cleanup(self) -> None:
        """Gracefully cleanup all connector instances."""
        with self._lock:
            for registration in self._connectors.values():
                if registration.instance is not None:
                    try:
                        if hasattr(registration.instance, "cleanup"):
                            await registration.instance.cleanup()
                        logger.info("Connector cleaned up", name=registration.name)
                    except Exception as e:
                        logger.error("Error cleaning up connector", name=registration.name, error=str(e))
