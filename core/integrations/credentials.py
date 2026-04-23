from typing import Dict, Any, Optional, Type
import structlog

from core.integrations.credential_backends.base import CredentialBackend
from core.integrations.credential_backends.env_vars import EnvVarsBackend

logger = structlog.get_logger(__name__)


class CredentialsManager:
    """Centralized credential storage with pluggable backends."""

    def __init__(self, backend: Optional[CredentialBackend] = None, backend_type: str = "env_vars", **backend_kwargs):
        """Initialize CredentialsManager with specified backend.

        Args:
            backend: CredentialBackend instance (if provided, backend_type and kwargs are ignored)
            backend_type: Type of backend to use ('env_vars', 'aws_secrets', 'vault')
            **backend_kwargs: Arguments to pass to backend constructor
        """
        if backend:
            self.backend = backend
        else:
            self.backend = self._create_backend(backend_type, **backend_kwargs)

        logger.info("CredentialsManager initialized", backend_type=type(self.backend).__name__)

    def get(self, service: str, key: str) -> Optional[str]:
        """Get a credential for a service."""
        credential = self.backend.get_credential(service, key)

        if credential is None:
            logger.warn("Credential not found", service=service, key=key)

        return credential

    def set(self, service: str, key: str, value: str) -> None:
        """Set a credential for a service."""
        self.backend.set_credential(service, key, value)
        logger.info("Credential set", service=service, key=key)

    def delete(self, service: str, key: str) -> None:
        """Delete a credential for a service."""
        self.backend.delete_credential(service, key)
        logger.info("Credential deleted", service=service, key=key)

    def get_config(self, service: str) -> Dict[str, str]:
        """Get all credentials for a service as a config dict."""
        config = self.backend.get_config(service)
        logger.info("Config retrieved for service", service=service, key_count=len(config))
        return config

    def list_services(self) -> list:
        """List all services with stored credentials."""
        services = self.backend.list_services()
        logger.info("Services listed", count=len(services))
        return services

    def _create_backend(self, backend_type: str, **kwargs) -> CredentialBackend:
        """Create and return a backend instance based on type."""
        if backend_type == "env_vars":
            return EnvVarsBackend()

        elif backend_type == "aws_secrets":
            try:
                from core.integrations.credential_backends.aws_secrets import AWSSecretsBackend
                region = kwargs.get("region", "us-east-1")
                cache_ttl = kwargs.get("cache_ttl_minutes", 60)
                return AWSSecretsBackend(region=region, cache_ttl_minutes=cache_ttl)
            except ImportError:
                logger.error("boto3 not installed for AWSSecretsBackend")
                raise RuntimeError("boto3 required for aws_secrets backend")

        elif backend_type == "vault":
            try:
                from core.integrations.credential_backends.vault import VaultBackend
                vault_addr = kwargs.get("vault_addr")
                if not vault_addr:
                    raise ValueError("vault_addr required for vault backend")

                vault_token = kwargs.get("vault_token")
                auth_role = kwargs.get("auth_role")
                auth_secret = kwargs.get("auth_secret")

                return VaultBackend(
                    vault_addr=vault_addr,
                    vault_token=vault_token,
                    auth_role=auth_role,
                    auth_secret=auth_secret,
                )
            except ImportError:
                logger.error("requests not installed for VaultBackend")
                raise RuntimeError("requests required for vault backend")

        else:
            logger.error("Unknown backend type", backend_type=backend_type)
            raise ValueError(f"Unknown backend type: {backend_type}")
