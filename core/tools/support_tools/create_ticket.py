from typing import Dict, Any
from datetime import datetime
import structlog

from core.tools.base import BaseTool, ToolMetadata
from core.integrations.base import IntegrationResult, OperationStatus

logger = structlog.get_logger(__name__)


class CreateTicketTool(BaseTool):
    """Creates support tickets in external ticketing system."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="CreateTicketTool",
            description="Creates a support ticket in external ticketing system",
            category="support",
            version="1.0.0",
            required_inputs={"title": "str", "description": "str"},
            optional_inputs={"customer_email": "str", "priority": "str"},
            output_schema={
                "ticket_id": "str",
                "ticket_number": "str",
                "created_at": "str",
                "status": "str",
                "customer_email": "str",
            },
            auth_required=True,
            rate_limit_per_minute=60,
        )

    async def execute(self, inputs: Dict[str, Any]) -> IntegrationResult:
        """Create a new support ticket."""
        is_valid, errors = await self.validate(inputs)
        if not is_valid:
            return IntegrationResult(
                operation_id="create_ticket",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=errors,
            )

        try:
            title = inputs.get("title")
            description = inputs.get("description")
            customer_email = inputs.get("customer_email", "unknown@example.com")
            priority = inputs.get("priority", "Normal")

            ticket_id = f"ticket_{datetime.utcnow().timestamp()}"
            ticket_number = f"TKT-{int(datetime.utcnow().timestamp())}"

            result_data = {
                "ticket_id": ticket_id,
                "ticket_number": ticket_number,
                "created_at": datetime.utcnow().isoformat(),
                "status": "Open",
                "title": title,
                "priority": priority,
                "customer_email": customer_email,
            }

            logger.info(
                "Support ticket created",
                ticket_id=ticket_id,
                ticket_number=ticket_number,
                priority=priority,
            )

            return IntegrationResult(
                operation_id="create_ticket",
                status=OperationStatus.SUCCESS,
                timestamp=datetime.utcnow(),
                data=result_data,
                errors=[],
            )

        except Exception as e:
            error_msg = f"Error creating ticket: {str(e)}"
            logger.error("Ticket creation failed", error=str(e))
            return IntegrationResult(
                operation_id="create_ticket",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=[error_msg],
            )
