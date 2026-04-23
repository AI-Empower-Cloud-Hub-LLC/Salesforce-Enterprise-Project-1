from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import structlog

logger = structlog.get_logger(__name__)


class CredentialBackend(ABC):
    """Abstract base class for credential storage backends."""

    @abstractmethod
    def get_credential(self, service: str, key: str) -> Optional[str]:
        """Retrieve a credential for a service."""
        pass

    @abstractmethod
    def set_credential(self, service: str, key: str, value: str) -> None:
        """Store a credential for a service."""
        pass

    @abstractmethod
    def delete_credential(self, service: str, key: str) -> None:
        """Delete a credential for a service."""
        pass

    @abstractmethod
    def list_services(self) -> List[str]:
        """List all services with stored credentials."""
        pass

    def get_config(self, service: str) -> Dict[str, str]:
        """Get all credentials for a service as a config dict."""
        config = {}
        services = self.list_services()

        if service not in services:
            logger.warn("Service not found in credentials backend", service=service)
            return config

        for key_name in self._get_service_keys(service):
            try:
                value = self.get_credential(service, key_name)
                if value:
                    config[key_name] = value
            except Exception as e:
                logger.error("Error retrieving credential", service=service, key=key_name, error=str(e))

        return config

    def _get_service_keys(self, service: str) -> List[str]:
        """Get all keys for a service. Subclasses should override if needed."""
        return []
