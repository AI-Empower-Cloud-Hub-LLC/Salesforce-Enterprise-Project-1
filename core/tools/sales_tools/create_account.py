from typing import Dict, Any, Optional
from datetime import datetime
import structlog

from core.tools.base import BaseTool, ToolMetadata
from core.integrations.base import IntegrationResult, OperationStatus

logger = structlog.get_logger(__name__)


class CreateAccountTool(BaseTool):
    """Creates a Salesforce Account with specified details."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="CreateAccountTool",
            description="Creates a new Salesforce Account with name, industry, and revenue range",
            category="sales",
            version="1.0.0",
            required_inputs={"name": "str"},
            optional_inputs={"industry": "str", "revenue_range": "str"},
            output_schema={
                "account_id": "str",
                "created_timestamp": "str",
                "name": "str",
            },
            auth_required=True,
            rate_limit_per_minute=60,
        )

    async def execute(self, inputs: Dict[str, Any]) -> IntegrationResult:
        """Create a new Salesforce account."""
        is_valid, errors = await self.validate(inputs)
        if not is_valid:
            return IntegrationResult(
                operation_id="create_account",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=errors,
            )

        try:
            name = inputs.get("name")
            industry = inputs.get("industry", "Other")
            revenue_range = inputs.get("revenue_range", "Unknown")

            # Check for duplicate account name
            existing_accounts = [
                acc for acc in self._get_mock_accounts() if acc["name"] == name
            ]
            if existing_accounts:
                error = f"Account with name '{name}' already exists"
                logger.warn("Duplicate account name", name=name)
                return IntegrationResult(
                    operation_id="create_account",
                    status=OperationStatus.FAILED,
                    timestamp=datetime.utcnow(),
                    data={},
                    errors=[error],
                )

            account_id = f"acc_{datetime.utcnow().timestamp()}"
            created_timestamp = datetime.utcnow().isoformat()

            result_data = {
                "account_id": account_id,
                "created_timestamp": created_timestamp,
                "name": name,
                "industry": industry,
                "revenue_range": revenue_range,
            }

            logger.info(
                "Account created successfully",
                account_id=account_id,
                name=name,
            )

            return IntegrationResult(
                operation_id="create_account",
                status=OperationStatus.SUCCESS,
                timestamp=datetime.utcnow(),
                data=result_data,
                errors=[],
            )

        except Exception as e:
            error_msg = f"Error creating account: {str(e)}"
            logger.error("Account creation failed", error=str(e))
            return IntegrationResult(
                operation_id="create_account",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=[error_msg],
            )

    def _get_mock_accounts(self) -> list:
        """Get mock accounts for duplicate checking."""
        # In production, this would query Salesforce
        return []
