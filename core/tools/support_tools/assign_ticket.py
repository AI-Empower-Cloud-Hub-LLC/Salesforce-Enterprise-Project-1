from typing import Dict, Any
from datetime import datetime
import structlog

from core.tools.base import BaseTool, ToolMetadata
from core.integrations.base import IntegrationResult, OperationStatus

logger = structlog.get_logger(__name__)


class AssignTicketToAgentTool(BaseTool):
    """Assigns support tickets to agents based on availability and expertise."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="AssignTicketToAgentTool",
            description="Routes tickets to support agents based on availability and skill level",
            category="support",
            version="1.0.0",
            required_inputs={"ticket_id": "str"},
            optional_inputs={"priority": "str", "required_skill": "str"},
            output_schema={
                "ticket_id": "str",
                "assigned_to": "str",
                "agent_email": "str",
                "assigned_at": "str",
                "sla_time": "int",
            },
            auth_required=True,
            rate_limit_per_minute=60,
        )

    async def execute(self, inputs: Dict[str, Any]) -> IntegrationResult:
        """Assign ticket to an agent."""
        is_valid, errors = await self.validate(inputs)
        if not is_valid:
            return IntegrationResult(
                operation_id="assign_ticket",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=errors,
            )

        try:
            ticket_id = inputs.get("ticket_id")
            priority = inputs.get("priority", "Normal")
            required_skill = inputs.get("required_skill", "general")

            # Find best available agent
            agent = self._find_available_agent(priority, required_skill)

            if not agent:
                error = "No available agents for this ticket"
                logger.warn("No agents available", ticket_id=ticket_id)
                return IntegrationResult(
                    operation_id="assign_ticket",
                    status=OperationStatus.FAILED,
                    timestamp=datetime.utcnow(),
                    data={},
                    errors=[error],
                )

            # Calculate SLA time in hours based on priority
            sla_times = {"Critical": 1, "High": 4, "Normal": 24, "Low": 48}
            sla_time = sla_times.get(priority, 24)

            result_data = {
                "ticket_id": ticket_id,
                "assigned_to": agent["name"],
                "agent_email": agent["email"],
                "assigned_at": datetime.utcnow().isoformat(),
                "sla_time": sla_time,
                "priority": priority,
            }

            logger.info(
                "Ticket assigned to agent",
                ticket_id=ticket_id,
                agent=agent["name"],
                priority=priority,
            )

            return IntegrationResult(
                operation_id="assign_ticket",
                status=OperationStatus.SUCCESS,
                timestamp=datetime.utcnow(),
                data=result_data,
                errors=[],
            )

        except Exception as e:
            error_msg = f"Error assigning ticket: {str(e)}"
            logger.error("Ticket assignment failed", error=str(e))
            return IntegrationResult(
                operation_id="assign_ticket",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=[error_msg],
            )

    def _find_available_agent(
        self, priority: str, required_skill: str
    ) -> Dict[str, Any]:
        """Find best available agent (mock)."""
        # In production, this would query agent availability and skills
        return {"name": "John Smith", "email": "john@support.com", "skill": "general"}
