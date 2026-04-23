import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import structlog

from core.integrations.credential_backends.base import CredentialBackend

logger = structlog.get_logger(__name__)


class AWSSecretsBackend(CredentialBackend):
    """Retrieve credentials from AWS Secrets Manager with caching."""

    def __init__(self, region: str = "us-east-1", cache_ttl_minutes: int = 60):
        """Initialize AWS Secrets Manager backend."""
        try:
            import boto3
            self.secrets_client = boto3.client("secretsmanager", region_name=region)
            self.region = region
        except ImportError:
            logger.error("boto3 not installed. Install with: pip install boto3")
            raise RuntimeError("boto3 required for AWSSecretsBackend")

        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        self._cache: Dict[str, tuple] = {}
        self._services_cache: Optional[tuple] = None

    def get_credential(self, service: str, key: str) -> Optional[str]:
        """Get credential from AWS Secrets Manager."""
        secret_name = f"{service}/{key}"

        cached = self._get_from_cache(secret_name)
        if cached is not None:
            logger.debug("Credential retrieved from cache", secret_name=secret_name)
            return cached

        try:
            response = self.secrets_client.get_secret_value(SecretId=secret_name)
            value = response.get("SecretString") or response.get("SecretBinary")

            if value:
                self._cache[secret_name] = (value, datetime.utcnow())
                logger.info("Credential retrieved from AWS Secrets Manager", secret_name=secret_name)
                return value

            return None
        except self.secrets_client.exceptions.ResourceNotFoundException:
            logger.debug("Secret not found in AWS Secrets Manager", secret_name=secret_name)
            return None
        except Exception as e:
            logger.error("Error retrieving from AWS Secrets Manager", secret_name=secret_name, error=str(e))
            return None

    def set_credential(self, service: str, key: str, value: str) -> None:
        """Store credential in AWS Secrets Manager."""
        secret_name = f"{service}/{key}"

        try:
            self.secrets_client.put_secret_value(SecretId=secret_name, SecretString=value)
            self._cache[secret_name] = (value, datetime.utcnow())
            self._services_cache = None
            logger.info("Credential stored in AWS Secrets Manager", secret_name=secret_name)
        except Exception as e:
            logger.error("Error storing in AWS Secrets Manager", secret_name=secret_name, error=str(e))
            raise

    def delete_credential(self, service: str, key: str) -> None:
        """Delete credential from AWS Secrets Manager."""
        secret_name = f"{service}/{key}"

        try:
            self.secrets_client.delete_secret(SecretId=secret_name, ForceDeleteWithoutRecovery=True)
            if secret_name in self._cache:
                del self._cache[secret_name]
            self._services_cache = None
            logger.info("Credential deleted from AWS Secrets Manager", secret_name=secret_name)
        except Exception as e:
            logger.error("Error deleting from AWS Secrets Manager", secret_name=secret_name, error=str(e))
            raise

    def list_services(self) -> List[str]:
        """List all services with credentials in AWS Secrets Manager."""
        cached = self._get_services_from_cache()
        if cached is not None:
            return cached

        try:
            services = set()
            paginator = self.secrets_client.get_paginator("list_secrets")

            for page in paginator.paginate():
                for secret in page.get("SecretList", []):
                    secret_name = secret.get("Name", "")
                    if "/" in secret_name:
                        service = secret_name.split("/")[0].lower()
                        services.add(service)

            services_list = sorted(list(services))
            self._services_cache = (services_list, datetime.utcnow())
            logger.info("Services list retrieved from AWS Secrets Manager", count=len(services_list))
            return services_list
        except Exception as e:
            logger.error("Error listing services from AWS Secrets Manager", error=str(e))
            return []

    def _get_from_cache(self, key: str) -> Optional[str]:
        """Get value from cache if not expired."""
        if key not in self._cache:
            return None

        value, timestamp = self._cache[key]
        if datetime.utcnow() - timestamp > self.cache_ttl:
            del self._cache[key]
            return None

        return value

    def _get_services_from_cache(self) -> Optional[List[str]]:
        """Get services list from cache if not expired."""
        if self._services_cache is None:
            return None

        services, timestamp = self._services_cache
        if datetime.utcnow() - timestamp > self.cache_ttl:
            self._services_cache = None
            return None

        return services
