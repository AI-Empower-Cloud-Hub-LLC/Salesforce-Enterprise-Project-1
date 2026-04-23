from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

from core.tools.base import BaseTool, ToolMetadata
from core.integrations.base import IntegrationResult, OperationStatus

logger = structlog.get_logger(__name__)


class QueryLeadsTool(BaseTool):
    """Queries Salesforce Leads using SOQL with optional filters."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="QueryLeadsTool",
            description="Queries Salesforce Leads using SOQL with status, company, and date filters",
            category="sales",
            version="1.0.0",
            required_inputs={},
            optional_inputs={
                "status": "str",
                "company": "str",
                "created_after": "str",
                "created_before": "str",
                "limit": "int",
                "offset": "int",
            },
            output_schema={
                "leads": "list",
                "total_count": "int",
                "has_more": "bool",
            },
            auth_required=True,
            rate_limit_per_minute=60,
        )

    async def execute(self, inputs: Dict[str, Any]) -> IntegrationResult:
        """Query Salesforce leads with filters."""
        is_valid, errors = await self.validate(inputs)
        if not is_valid:
            return IntegrationResult(
                operation_id="query_leads",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=errors,
            )

        try:
            status = inputs.get("status")
            company = inputs.get("company")
            created_after = inputs.get("created_after")
            created_before = inputs.get("created_before")
            limit = inputs.get("limit", 100)
            offset = inputs.get("offset", 0)

            # Build SOQL query
            soql = "SELECT Id, FirstName, LastName, Company, Status, CreatedDate FROM Lead"
            conditions = []

            if status:
                conditions.append(f"Status = '{status}'")
            if company:
                conditions.append(f"Company LIKE '%{company}%'")
            if created_after:
                conditions.append(f"CreatedDate >= {created_after}")
            if created_before:
                conditions.append(f"CreatedDate <= {created_before}")

            if conditions:
                soql += " WHERE " + " AND ".join(conditions)

            soql += f" LIMIT {limit} OFFSET {offset}"

            # Execute query (mock implementation)
            leads = self._execute_soql(soql)
            total_count = len(leads)
            has_more = total_count == limit

            result_data = {
                "leads": leads,
                "total_count": total_count,
                "has_more": has_more,
                "soql_query": soql,
            }

            logger.info(
                "Leads queried successfully",
                lead_count=total_count,
                filters={"status": status, "company": company},
            )

            return IntegrationResult(
                operation_id="query_leads",
                status=OperationStatus.SUCCESS,
                timestamp=datetime.utcnow(),
                data=result_data,
                errors=[],
            )

        except Exception as e:
            error_msg = f"Error querying leads: {str(e)}"
            logger.error("Lead query failed", error=str(e))
            return IntegrationResult(
                operation_id="query_leads",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=[error_msg],
            )

    def _execute_soql(self, soql: str) -> List[Dict[str, Any]]:
        """Execute SOQL query against Salesforce (mock)."""
        # In production, this would call Salesforce SOQL API
        return [
            {
                "id": "lead_1",
                "firstName": "John",
                "lastName": "Doe",
                "company": "Acme Corp",
                "status": "Open",
                "createdDate": datetime.utcnow().isoformat(),
            },
        ]
