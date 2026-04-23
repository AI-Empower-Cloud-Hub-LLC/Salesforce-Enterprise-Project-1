import os
from typing import Dict, List, Optional
import structlog

from core.integrations.credential_backends.base import CredentialBackend

logger = structlog.get_logger(__name__)


class EnvVarsBackend(CredentialBackend):
    """Retrieve credentials from environment variables using CRED_SERVICE_KEY pattern."""

    def get_credential(self, service: str, key: str) -> Optional[str]:
        """Get credential from environment variable: CRED_{SERVICE}_{KEY}."""
        env_var = f"CRED_{service.upper()}_{key.upper()}"
        value = os.environ.get(env_var)

        if value is None:
            logger.debug("Credential not found in environment", env_var=env_var)
            return None

        logger.debug("Credential retrieved from environment", env_var=env_var)
        return value

    def set_credential(self, service: str, key: str, value: str) -> None:
        """Set credential in environment variable (runtime only, not persistent)."""
        env_var = f"CRED_{service.upper()}_{key.upper()}"
        os.environ[env_var] = value
        logger.info("Credential set in environment", env_var=env_var)

    def delete_credential(self, service: str, key: str) -> None:
        """Delete credential from environment (runtime only)."""
        env_var = f"CRED_{service.upper()}_{key.upper()}"
        if env_var in os.environ:
            del os.environ[env_var]
            logger.info("Credential deleted from environment", env_var=env_var)

    def list_services(self) -> List[str]:
        """List all services with credentials in environment."""
        services = set()

        for env_var in os.environ:
            if env_var.startswith("CRED_"):
                parts = env_var.split("_")
                if len(parts) >= 3:
                    service = parts[1].lower()
                    services.add(service)

        return sorted(list(services))

    def _get_service_keys(self, service: str) -> List[str]:
        """Get all keys for a service from environment variables."""
        keys = set()
        prefix = f"CRED_{service.upper()}_"

        for env_var in os.environ:
            if env_var.startswith(prefix):
                key = env_var[len(prefix):].lower()
                keys.add(key)

        return sorted(list(keys))
