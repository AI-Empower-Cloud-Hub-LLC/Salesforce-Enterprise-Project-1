"""External service integration connector."""

from typing import Any, Dict, Optional, List
import requests
from datetime import datetime
import hashlib
import hmac

import structlog

from core.integrations.base import IntegrationBackend, IntegrationResult

logger = structlog.get_logger(__name__)


class ExternalServiceConnector(IntegrationBackend):
    """Generic external service API integration backend."""

    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize external service connector.

        Args:
            name: Integration name
            config: Configuration with base_url, auth_type, api_key, headers, etc.
        """
        super().__init__(name, config)
        self.base_url = config.get("base_url", "").rstrip("/")
        self.auth_type = config.get("auth_type", "none").lower()
        self.api_key = config.get("api_key")
        self.api_secret = config.get("api_secret")
        self.username = config.get("username")
        self.password = config.get("password")
        self.token = config.get("token")
        self.custom_headers = config.get("headers", {})
        self.timeout = config.get("timeout", 30)
        self.verify_ssl = config.get("verify_ssl", True)

        self._session = None
        self._request_count = 0
        self._last_request_time: Optional[datetime] = None

    def authenticate(self) -> bool:
        """Authenticate with external service based on auth type."""
        try:
            self._setup_session()

            # Test connection with a simple request
            headers = self._get_headers()
            response = requests.head(
                self.base_url,
                headers=headers,
                timeout=5,
                verify=self.verify_ssl,
            )

            if response.status_code < 400:
                self._is_healthy = True
                logger.info(
                    "external_service_authenticated",
                    service_name=self.name,
                    base_url=self.base_url,
                    auth_type=self.auth_type,
                )
                return True
            else:
                logger.warning(
                    "external_service_authentication_failed",
                    service_name=self.name,
                    status_code=response.status_code,
                )
                self._is_healthy = False
                return False

        except Exception as e:
            logger.error(
                "external_service_authentication_failed",
                service_name=self.name,
                error=str(e),
            )
            self._is_healthy = False
            return False

    def execute_query(
        self, query: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> IntegrationResult:
        """
        Execute query or operation against external service.

        Args:
            query: Query specification with 'endpoint', 'method', 'params', 'data'
            context: Optional execution context

        Returns:
            IntegrationResult with operation outcome
        """
        if not self.authenticate():
            return IntegrationResult(
                success=False,
                error="External service authentication failed",
            )

        try:
            endpoint = query.get("endpoint", "")
            method = query.get("method", "GET").upper()
            params = query.get("params", {})
            data = query.get("data")
            headers = query.get("headers", {})

            return self._execute_request(endpoint, method, params, data, headers)

        except Exception as e:
            logger.error("external_service_query_execution_failed", error=str(e))
            return IntegrationResult(
                success=False,
                error=str(e),
            )

    def _execute_request(
        self,
        endpoint: str,
        method: str,
        params: Dict[str, Any],
        data: Optional[Dict[str, Any]],
        additional_headers: Optional[Dict[str, str]] = None,
    ) -> IntegrationResult:
        """Execute HTTP request to external service."""
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            headers = self._get_headers()

            if additional_headers:
                headers.update(additional_headers)

            method = method.upper()
            if method == "GET":
                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                )
            elif method == "POST":
                response = requests.post(
                    url,
                    params=params,
                    json=data,
                    headers=headers,
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                )
            elif method == "PUT":
                response = requests.put(
                    url,
                    params=params,
                    json=data,
                    headers=headers,
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                )
            elif method == "PATCH":
                response = requests.patch(
                    url,
                    params=params,
                    json=data,
                    headers=headers,
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                )
            elif method == "DELETE":
                response = requests.delete(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                )
            elif method == "HEAD":
                response = requests.head(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                )
            else:
                return IntegrationResult(
                    success=False,
                    error=f"Unsupported HTTP method: {method}",
                )

            response.raise_for_status()

            self._request_count += 1
            self._last_request_time = datetime.utcnow()

            try:
                response_data = response.json()
            except:
                response_data = response.text

            return IntegrationResult(
                success=True,
                data={
                    "status_code": response.status_code,
                    "response": response_data,
                    "headers": dict(response.headers),
                },
            )

        except requests.exceptions.HTTPError as e:
            try:
                error_data = e.response.json()
            except:
                error_data = e.response.text

            return IntegrationResult(
                success=False,
                error=f"HTTP {e.response.status_code}",
                error_details={
                    "status_code": e.response.status_code,
                    "response": error_data,
                },
            )

        except Exception as e:
            return IntegrationResult(success=False, error=str(e))

    def health_check(self) -> bool:
        """Check external service availability."""
        try:
            if not self.authenticate():
                self._is_healthy = False
                return False

            self._is_healthy = True
            return True

        except Exception as e:
            logger.warning(
                "external_service_health_check_failed",
                service_name=self.name,
                error=str(e),
            )
            self._is_healthy = False
            return False

    def list_resources(self, resource_type: str) -> List[Dict[str, Any]]:
        """
        List available resources from external service.

        Args:
            resource_type: Type of resource to list

        Returns:
            List of available resources
        """
        if not self.authenticate():
            return []

        try:
            endpoints = self.config.get("resource_endpoints", {})
            endpoint = endpoints.get(resource_type)

            if not endpoint:
                return []

            result = self._execute_request(endpoint, "GET", {}, None)

            if result.success and result.data:
                data = result.data.get("response", [])
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    items = data.get("items", data.get("data", data.get("results", [])))
                    return items if isinstance(items, list) else []

            return []

        except Exception as e:
            logger.warning(
                "external_service_list_resources_failed",
                resource_type=resource_type,
                error=str(e),
            )
            return []

    def _setup_session(self) -> None:
        """Set up requests session with connection pooling."""
        if self._session:
            return

        self._session = requests.Session()

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authorization."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        headers.update(self.custom_headers)

        if self.auth_type == "api_key":
            if self.api_key:
                key_header = self.config.get("api_key_header", "X-API-Key")
                headers[key_header] = self.api_key

        elif self.auth_type == "bearer":
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

        elif self.auth_type == "basic":
            if self.username and self.password:
                import base64

                credentials = base64.b64encode(
                    f"{self.username}:{self.password}".encode()
                ).decode()
                headers["Authorization"] = f"Basic {credentials}"

        elif self.auth_type == "hmac":
            if self.api_key and self.api_secret:
                timestamp = str(int(datetime.utcnow().timestamp()))
                message = f"{self.api_key}{timestamp}"
                signature = hmac.new(
                    self.api_secret.encode(),
                    message.encode(),
                    hashlib.sha256,
                ).hexdigest()
                headers["X-API-Key"] = self.api_key
                headers["X-Signature"] = signature
                headers["X-Timestamp"] = timestamp

        elif self.auth_type == "custom":
            custom_auth = self.config.get("custom_auth", {})
            for key, value in custom_auth.items():
                headers[key] = value

        return headers

    def get_status(self) -> Dict[str, Any]:
        """Get integration status."""
        status = super().get_status()
        status.update({
            "service_name": self.name,
            "base_url": self.base_url,
            "auth_type": self.auth_type,
            "request_count": self._request_count,
            "last_request_time": self._last_request_time.isoformat()
            if self._last_request_time
            else None,
        })
        return status
