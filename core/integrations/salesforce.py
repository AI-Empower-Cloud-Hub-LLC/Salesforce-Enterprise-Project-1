"""Salesforce integration connector."""

from typing import Any, Dict, Optional, List
import json
import requests
from datetime import datetime, timedelta

import structlog

from core.integrations.base import IntegrationBackend, IntegrationResult

logger = structlog.get_logger(__name__)


class SalesforceConnector(IntegrationBackend):
    """Salesforce API integration backend."""

    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize Salesforce connector.

        Args:
            name: Integration name
            config: Configuration with instance_url, client_id, client_secret, username, password
        """
        super().__init__(name, config)
        self.instance_url = config.get("instance_url", "https://login.salesforce.com")
        self.client_id = config.get("client_id")
        self.client_secret = config.get("client_secret")
        self.username = config.get("username")
        self.password = config.get("password")
        self.security_token = config.get("security_token", "")

        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        self.api_version = config.get("api_version", "60.0")
        self._rate_limit_remaining = 10000

    def authenticate(self) -> bool:
        """Authenticate with Salesforce OAuth 2.0."""
        try:
            if self.access_token and self.token_expiry and datetime.utcnow() < self.token_expiry:
                return True

            auth_url = f"{self.instance_url}/services/oauth2/token"

            payload = {
                "grant_type": "password",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "username": self.username,
                "password": self.password + self.security_token,
            }

            response = requests.post(auth_url, data=payload, timeout=10)
            response.raise_for_status()

            data = response.json()
            self.access_token = data.get("access_token")
            self.token_expiry = datetime.utcnow() + timedelta(hours=2)
            self._is_healthy = True

            logger.info("salesforce_authenticated", instance_url=self.instance_url)
            return True

        except Exception as e:
            logger.error("salesforce_authentication_failed", error=str(e))
            self._is_healthy = False
            return False

    def execute_query(
        self, query: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> IntegrationResult:
        """
        Execute query or operation against Salesforce.

        Args:
            query: Query specification with 'type' and 'data'
            context: Optional execution context

        Returns:
            IntegrationResult with operation outcome
        """
        if not self.authenticate():
            return IntegrationResult(
                success=False,
                error="Salesforce authentication failed",
            )

        try:
            query_type = query.get("type", "soql")
            query_data = query.get("data", {})

            if query_type == "soql":
                return self._execute_soql(query_data)
            elif query_type == "rest":
                return self._execute_rest_api(query_data)
            elif query_type == "sobject":
                return self._execute_sobject_operation(query_data)
            else:
                return IntegrationResult(
                    success=False,
                    error=f"Unknown query type: {query_type}",
                )

        except Exception as e:
            logger.error("salesforce_query_execution_failed", error=str(e))
            return IntegrationResult(
                success=False,
                error=str(e),
            )

    def _execute_soql(self, query_data: Dict[str, Any]) -> IntegrationResult:
        """Execute SOQL query."""
        soql = query_data.get("soql")
        if not soql:
            return IntegrationResult(success=False, error="Missing SOQL query")

        try:
            url = f"{self.instance_url}/services/data/v{self.api_version}/query"
            headers = self._get_headers()
            params = {"q": soql}

            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()

            self._update_rate_limit(response.headers)
            data = response.json()

            return IntegrationResult(
                success=True,
                data={
                    "records": data.get("records", []),
                    "total_size": data.get("totalSize", 0),
                },
            )

        except Exception as e:
            return IntegrationResult(success=False, error=str(e))

    def _execute_rest_api(self, query_data: Dict[str, Any]) -> IntegrationResult:
        """Execute REST API call."""
        endpoint = query_data.get("endpoint")
        method = query_data.get("method", "GET").upper()
        body = query_data.get("body")

        if not endpoint:
            return IntegrationResult(success=False, error="Missing endpoint")

        try:
            url = f"{self.instance_url}/services/data/v{self.api_version}{endpoint}"
            headers = self._get_headers()

            if method == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=body, timeout=30)
            elif method == "PATCH":
                response = requests.patch(url, headers=headers, json=body, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                return IntegrationResult(success=False, error=f"Unsupported method: {method}")

            response.raise_for_status()
            self._update_rate_limit(response.headers)

            try:
                data = response.json()
            except:
                data = response.text

            return IntegrationResult(success=True, data=data)

        except Exception as e:
            return IntegrationResult(success=False, error=str(e))

    def _execute_sobject_operation(self, query_data: Dict[str, Any]) -> IntegrationResult:
        """Execute SObject CRUD operation."""
        sobject_type = query_data.get("sobject_type")
        operation = query_data.get("operation", "query")
        sobject_id = query_data.get("id")
        fields = query_data.get("fields")
        data = query_data.get("data")

        if not sobject_type:
            return IntegrationResult(success=False, error="Missing sobject_type")

        try:
            if operation == "create":
                return self._sobject_create(sobject_type, data)
            elif operation == "update":
                return self._sobject_update(sobject_type, sobject_id, data)
            elif operation == "delete":
                return self._sobject_delete(sobject_type, sobject_id)
            elif operation == "retrieve":
                return self._sobject_retrieve(sobject_type, sobject_id, fields)
            elif operation == "query":
                return self._sobject_query(sobject_type, query_data.get("where"))
            else:
                return IntegrationResult(success=False, error=f"Unknown operation: {operation}")

        except Exception as e:
            return IntegrationResult(success=False, error=str(e))

    def _sobject_create(self, sobject_type: str, data: Dict[str, Any]) -> IntegrationResult:
        """Create a new SObject record."""
        url = f"{self.instance_url}/services/data/v{self.api_version}/sobjects/{sobject_type}"
        headers = self._get_headers()

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            self._update_rate_limit(response.headers)

            result = response.json()
            return IntegrationResult(
                success=result.get("success", False),
                data=result,
            )
        except Exception as e:
            return IntegrationResult(success=False, error=str(e))

    def _sobject_update(
        self, sobject_type: str, sobject_id: str, data: Dict[str, Any]
    ) -> IntegrationResult:
        """Update an existing SObject record."""
        url = f"{self.instance_url}/services/data/v{self.api_version}/sobjects/{sobject_type}/{sobject_id}"
        headers = self._get_headers()

        try:
            response = requests.patch(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            self._update_rate_limit(response.headers)

            return IntegrationResult(success=True, data={"id": sobject_id})

        except Exception as e:
            return IntegrationResult(success=False, error=str(e))

    def _sobject_delete(self, sobject_type: str, sobject_id: str) -> IntegrationResult:
        """Delete an SObject record."""
        url = f"{self.instance_url}/services/data/v{self.api_version}/sobjects/{sobject_type}/{sobject_id}"
        headers = self._get_headers()

        try:
            response = requests.delete(url, headers=headers, timeout=30)
            response.raise_for_status()
            self._update_rate_limit(response.headers)

            return IntegrationResult(success=True, data={"deleted": True})

        except Exception as e:
            return IntegrationResult(success=False, error=str(e))

    def _sobject_retrieve(
        self, sobject_type: str, sobject_id: str, fields: Optional[List[str]] = None
    ) -> IntegrationResult:
        """Retrieve a specific SObject record."""
        url = f"{self.instance_url}/services/data/v{self.api_version}/sobjects/{sobject_type}/{sobject_id}"
        headers = self._get_headers()

        try:
            params = {}
            if fields:
                params["fields"] = ",".join(fields)

            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            self._update_rate_limit(response.headers)

            return IntegrationResult(success=True, data=response.json())

        except Exception as e:
            return IntegrationResult(success=False, error=str(e))

    def _sobject_query(self, sobject_type: str, where_clause: Optional[str] = None) -> IntegrationResult:
        """Query SObject records."""
        soql = f"SELECT * FROM {sobject_type}"
        if where_clause:
            soql += f" WHERE {where_clause}"

        return self._execute_soql({"soql": soql})

    def health_check(self) -> bool:
        """Check Salesforce API availability."""
        try:
            if not self.authenticate():
                self._is_healthy = False
                return False

            url = f"{self.instance_url}/services/data/v{self.api_version}/"
            headers = self._get_headers()

            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()

            self._is_healthy = True
            return True

        except Exception as e:
            logger.warning("salesforce_health_check_failed", error=str(e))
            self._is_healthy = False
            return False

    def list_resources(self, resource_type: str) -> List[Dict[str, Any]]:
        """
        List available Salesforce resources.

        Args:
            resource_type: Type of resource ('sobjects', 'metadata', etc.)

        Returns:
            List of available resources
        """
        if not self.authenticate():
            return []

        try:
            if resource_type == "sobjects":
                return self._list_sobjects()
            elif resource_type == "metadata":
                return self._list_metadata()
            else:
                return []

        except Exception as e:
            logger.warning(
                "salesforce_list_resources_failed",
                resource_type=resource_type,
                error=str(e),
            )
            return []

    def _list_sobjects(self) -> List[Dict[str, Any]]:
        """List available SObjects."""
        url = f"{self.instance_url}/services/data/v{self.api_version}/sobjects"
        headers = self._get_headers()

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            self._update_rate_limit(response.headers)

            data = response.json()
            sobjects = data.get("sobjects", [])

            return [
                {
                    "name": obj.get("name"),
                    "label": obj.get("label"),
                    "type": "sobject",
                    "queryable": obj.get("queryable", True),
                }
                for obj in sobjects
            ]

        except Exception as e:
            logger.error("salesforce_list_sobjects_failed", error=str(e))
            return []

    def _list_metadata(self) -> List[Dict[str, Any]]:
        """List available metadata types."""
        url = f"{self.instance_url}/services/data/v{self.api_version}/metadata"
        headers = self._get_headers()

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            self._update_rate_limit(response.headers)

            data = response.json()
            return [
                {
                    "name": meta.get("name"),
                    "type": "metadata",
                }
                for meta in data
            ]

        except Exception as e:
            logger.error("salesforce_list_metadata_failed", error=str(e))
            return []

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authorization."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _update_rate_limit(self, headers: Dict[str, str]) -> None:
        """Update rate limit tracking from response headers."""
        remaining = headers.get("sforce-limit-info", "")
        if remaining:
            try:
                parts = remaining.split("/")
                if len(parts) >= 2:
                    self._rate_limit_remaining = int(parts[0].split("=")[1])
            except:
                pass

    def get_status(self) -> Dict[str, Any]:
        """Get integration status."""
        status = super().get_status()
        status.update({
            "api_version": self.api_version,
            "rate_limit_remaining": self._rate_limit_remaining,
            "token_valid": self.access_token is not None
            and (self.token_expiry and datetime.utcnow() < self.token_expiry),
        })
        return status
