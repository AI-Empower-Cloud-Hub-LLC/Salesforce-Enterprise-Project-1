from typing import Dict, Any
from datetime import datetime
import structlog

from core.tools.base import BaseTool, ToolMetadata
from core.integrations.base import IntegrationResult, OperationStatus

logger = structlog.get_logger(__name__)

PRIORITY_ROUTING = {
    "Critical": "escalation_team",
    "High": "senior_support",
    "Medium": "standard_support",
    "Low": "general_queue",
}


class CreateCaseTool(BaseTool):
    """Creates support cases linked to accounts."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="CreateCaseTool",
            description="Creates a support case linked to an account with auto-routing based on priority",
            category="sales",
            version="1.0.0",
            required_inputs={
                "account_id": "str",
                "subject": "str",
                "description": "str",
            },
            optional_inputs={"priority": "str"},
            output_schema={
                "case_id": "str",
                "case_number": "str",
                "account_id": "str",
                "routed_to": "str",
                "created_at": "str",
            },
            auth_required=True,
            rate_limit_per_minute=60,
        )

    async def execute(self, inputs: Dict[str, Any]) -> IntegrationResult:
        """Create a new support case."""
        is_valid, errors = await self.validate(inputs)
        if not is_valid:
            return IntegrationResult(
                operation_id="create_case",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=errors,
            )

        try:
            account_id = inputs.get("account_id")
            subject = inputs.get("subject")
            description = inputs.get("description")
            priority = inputs.get("priority", "Medium")

            # Validate priority
            if priority not in PRIORITY_ROUTING:
                priority = "Medium"
                logger.warn("Invalid priority, defaulting to Medium", priority=priority)

            # Generate case details
            case_id = f"case_{datetime.utcnow().timestamp()}"
            case_number = f"CS-{int(datetime.utcnow().timestamp())}"
            routed_to = PRIORITY_ROUTING.get(priority, "standard_support")

            result_data = {
                "case_id": case_id,
                "case_number": case_number,
                "account_id": account_id,
                "subject": subject,
                "priority": priority,
                "routed_to": routed_to,
                "created_at": datetime.utcnow().isoformat(),
            }

            logger.info(
                "Case created and routed",
                case_id=case_id,
                account_id=account_id,
                priority=priority,
                routed_to=routed_to,
            )

            return IntegrationResult(
                operation_id="create_case",
                status=OperationStatus.SUCCESS,
                timestamp=datetime.utcnow(),
                data=result_data,
                errors=[],
            )

        except Exception as e:
            error_msg = f"Error creating case: {str(e)}"
            logger.error("Case creation failed", error=str(e))
            return IntegrationResult(
                operation_id="create_case",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=[error_msg],
            )
