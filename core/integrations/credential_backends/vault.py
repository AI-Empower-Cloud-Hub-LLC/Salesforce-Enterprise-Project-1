import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import structlog

from core.integrations.credential_backends.base import CredentialBackend

logger = structlog.get_logger(__name__)


class VaultBackend(CredentialBackend):
    """Retrieve credentials from HashiCorp Vault."""

    def __init__(self, vault_addr: str, vault_token: str = None, auth_role: str = None, auth_secret: str = None):
        """Initialize Vault backend.

        Args:
            vault_addr: Vault server address (e.g. https://vault.example.com:8200)
            vault_token: Static token for authentication
            auth_role: Role for AppRole authentication
            auth_secret: Secret for AppRole authentication
        """
        self.vault_addr = vault_addr.rstrip("/")
        self.vault_token = vault_token
        self.auth_role = auth_role
        self.auth_secret = auth_secret
        self._auth_token = vault_token
        self._token_expiry: Optional[datetime] = None
        self._cache: Dict[str, tuple] = {}
        self.cache_ttl = timedelta(minutes=60)

        if not self._auth_token and (auth_role and auth_secret):
            self._authenticate_with_approle()

    def get_credential(self, service: str, key: str) -> Optional[str]:
        """Get credential from Vault."""
        secret_path = f"secret/{service}/{key}"

        cached = self._get_from_cache(secret_path)
        if cached is not None:
            logger.debug("Credential retrieved from cache", secret_path=secret_path)
            return cached

        try:
            response = self._vault_request("GET", f"/v1/{secret_path}")
            if response.status_code == 200:
                data = response.json().get("data", {}).get("data", {})
                value = data.get("value") or data.get(key)

                if value:
                    self._cache[secret_path] = (value, datetime.utcnow())
                    logger.info("Credential retrieved from Vault", secret_path=secret_path)
                    return value

            return None
        except Exception as e:
            logger.error("Error retrieving from Vault", secret_path=secret_path, error=str(e))
            return None

    def set_credential(self, service: str, key: str, value: str) -> None:
        """Store credential in Vault."""
        secret_path = f"secret/{service}/{key}"

        try:
            payload = {"data": {key: value}}
            response = self._vault_request("POST", f"/v1/{secret_path}", json=payload)

            if response.status_code in [200, 204]:
                self._cache[secret_path] = (value, datetime.utcnow())
                logger.info("Credential stored in Vault", secret_path=secret_path)
            else:
                logger.error("Error storing credential in Vault", status=response.status_code, secret_path=secret_path)
                raise RuntimeError(f"Vault request failed: {response.status_code}")
        except Exception as e:
            logger.error("Error storing in Vault", secret_path=secret_path, error=str(e))
            raise

    def delete_credential(self, service: str, key: str) -> None:
        """Delete credential from Vault."""
        secret_path = f"secret/{service}/{key}"

        try:
            response = self._vault_request("DELETE", f"/v1/{secret_path}")

            if response.status_code in [200, 204]:
                if secret_path in self._cache:
                    del self._cache[secret_path]
                logger.info("Credential deleted from Vault", secret_path=secret_path)
            else:
                logger.error("Error deleting credential from Vault", status=response.status_code, secret_path=secret_path)
                raise RuntimeError(f"Vault request failed: {response.status_code}")
        except Exception as e:
            logger.error("Error deleting from Vault", secret_path=secret_path, error=str(e))
            raise

    def list_services(self) -> List[str]:
        """List all services with credentials in Vault."""
        try:
            response = self._vault_request("LIST", "/v1/secret/")

            if response.status_code == 200:
                keys = response.json().get("data", {}).get("keys", [])
                services = [k.rstrip("/") for k in keys if "/" not in k or k.count("/") == 1]
                logger.info("Services list retrieved from Vault", count=len(services))
                return sorted(services)

            return []
        except Exception as e:
            logger.error("Error listing services from Vault", error=str(e))
            return []

    def _authenticate_with_approle(self) -> None:
        """Authenticate with Vault using AppRole."""
        try:
            payload = {"role_id": self.auth_role, "secret_id": self.auth_secret}
            response = requests.post(f"{self.vault_addr}/v1/auth/approle/login", json=payload)

            if response.status_code == 200:
                auth = response.json().get("auth", {})
                self._auth_token = auth.get("client_token")
                lease_duration = auth.get("lease_duration", 3600)
                self._token_expiry = datetime.utcnow() + timedelta(seconds=lease_duration * 0.8)

                logger.info("Authenticated with Vault using AppRole")
            else:
                logger.error("AppRole authentication failed", status=response.status_code)
                raise RuntimeError(f"Vault authentication failed: {response.status_code}")
        except Exception as e:
            logger.error("Error authenticating with Vault", error=str(e))
            raise

    def _vault_request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Make authenticated request to Vault."""
        if not self._auth_token:
            raise RuntimeError("Not authenticated with Vault")

        if self._token_expiry and datetime.utcnow() > self._token_expiry and self.auth_role:
            self._authenticate_with_approle()

        headers = kwargs.get("headers", {})
        headers["X-Vault-Token"] = self._auth_token
        kwargs["headers"] = headers

        verify = kwargs.pop("verify", True)

        try:
            if method == "LIST":
                method = "GET"
                headers["X-HTTP-Method-Override"] = "LIST"

            response = requests.request(method, f"{self.vault_addr}{path}", verify=verify, timeout=10, **kwargs)
            return response
        except Exception as e:
            logger.error("Vault request failed", method=method, path=path, error=str(e))
            raise

    def _get_from_cache(self, key: str) -> Optional[str]:
        """Get value from cache if not expired."""
        if key not in self._cache:
            return None

        value, timestamp = self._cache[key]
        if datetime.utcnow() - timestamp > self.cache_ttl:
            del self._cache[key]
            return None

        return value
