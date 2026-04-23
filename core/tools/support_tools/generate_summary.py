from typing import Dict, Any, List
from datetime import datetime
import structlog

from core.tools.base import BaseTool, ToolMetadata
from core.integrations.base import IntegrationResult, OperationStatus

logger = structlog.get_logger(__name__)


class GenerateSummaryTool(BaseTool):
    """Generates summaries of ticket interactions using LLM."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="GenerateSummaryTool",
            description="Generates AI-powered summaries of ticket interactions and conversations",
            category="support",
            version="1.0.0",
            required_inputs={"ticket_id": "str"},
            optional_inputs={"max_length": "int", "tone": "str"},
            output_schema={
                "ticket_id": "str",
                "summary": "str",
                "key_issues": "list",
                "sentiment": "str",
                "generated_at": "str",
                "word_count": "int",
            },
            auth_required=False,
            rate_limit_per_minute=30,
        )

    async def execute(self, inputs: Dict[str, Any]) -> IntegrationResult:
        """Generate summary of ticket interactions."""
        is_valid, errors = await self.validate(inputs)
        if not is_valid:
            return IntegrationResult(
                operation_id="generate_summary",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=errors,
            )

        try:
            ticket_id = inputs.get("ticket_id")
            max_length = inputs.get("max_length", 500)
            tone = inputs.get("tone", "professional")

            # Get ticket interactions
            interactions = self._get_ticket_interactions(ticket_id)

            if not interactions:
                error = f"No interactions found for ticket {ticket_id}"
                logger.warn("No interactions found", ticket_id=ticket_id)
                return IntegrationResult(
                    operation_id="generate_summary",
                    status=OperationStatus.FAILED,
                    timestamp=datetime.utcnow(),
                    data={},
                    errors=[error],
                )

            # Generate summary
            summary, key_issues, sentiment = self._generate_summary_text(
                interactions, max_length, tone
            )

            result_data = {
                "ticket_id": ticket_id,
                "summary": summary,
                "key_issues": key_issues,
                "sentiment": sentiment,
                "generated_at": datetime.utcnow().isoformat(),
                "word_count": len(summary.split()),
                "tone": tone,
            }

            logger.info(
                "Ticket summary generated",
                ticket_id=ticket_id,
                sentiment=sentiment,
                word_count=len(summary.split()),
            )

            return IntegrationResult(
                operation_id="generate_summary",
                status=OperationStatus.SUCCESS,
                timestamp=datetime.utcnow(),
                data=result_data,
                errors=[],
            )

        except Exception as e:
            error_msg = f"Error generating summary: {str(e)}"
            logger.error("Summary generation failed", error=str(e))
            return IntegrationResult(
                operation_id="generate_summary",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=[error_msg],
            )

    def _get_ticket_interactions(self, ticket_id: str) -> List[Dict[str, Any]]:
        """Get ticket interactions (mock)."""
        # In production, this would fetch from ticketing system
        return [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "author": "customer",
                "message": "I am unable to access my account",
            },
        ]

    def _generate_summary_text(
        self, interactions: List[Dict[str, Any]], max_length: int, tone: str
    ) -> tuple[str, List[str], str]:
        """Generate summary text from interactions (mock)."""
        # In production, this would call LLM API
        summary = "Customer reported account access issues. Issue was resolved by resetting password."
        key_issues = ["account access", "authentication"]
        sentiment = "resolved"
        return summary, key_issues, sentiment
