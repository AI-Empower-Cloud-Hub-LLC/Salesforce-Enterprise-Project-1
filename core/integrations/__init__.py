"""Integration layer for external systems and services."""

from core.integrations.base import IntegrationBackend, IntegrationResult
from core.integrations.salesforce import SalesforceConnector
from core.integrations.database import DatabaseConnector
from core.integrations.external_service import ExternalServiceConnector
from core.integrations.registry import IntegrationRegistry

__all__ = [
    "IntegrationBackend",
    "IntegrationResult",
    "SalesforceConnector",
    "DatabaseConnector",
    "ExternalServiceConnector",
    "IntegrationRegistry",
]
