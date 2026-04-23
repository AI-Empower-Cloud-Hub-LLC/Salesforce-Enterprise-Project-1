from typing import Dict, Any
from datetime import datetime
import structlog

from core.tools.base import BaseTool, ToolMetadata
from core.integrations.base import IntegrationResult, OperationStatus

logger = structlog.get_logger(__name__)

# Valid sales stages per org config
VALID_STAGES = [
    "Prospecting",
    "Qualification",
    "Needs Analysis",
    "Value Proposition",
    "Negotiation/Review",
    "Closed Won",
    "Closed Lost",
]


class UpdateOpportunityStageTool(BaseTool):
    """Moves opportunities through sales pipeline stages."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="UpdateOpportunityStageTool",
            description="Updates opportunity stage and probability in sales pipeline",
            category="sales",
            version="1.0.0",
            required_inputs={"opportunity_id": "str", "new_stage": "str"},
            optional_inputs={"probability": "float"},
            output_schema={
                "opportunity_id": "str",
                "old_stage": "str",
                "new_stage": "str",
                "probability": "float",
                "changed_at": "str",
            },
            auth_required=True,
            rate_limit_per_minute=60,
        )

    async def execute(self, inputs: Dict[str, Any]) -> IntegrationResult:
        """Update opportunity stage."""
        is_valid, errors = await self.validate(inputs)
        if not is_valid:
            return IntegrationResult(
                operation_id="update_opportunity_stage",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=errors,
            )

        try:
            opportunity_id = inputs.get("opportunity_id")
            new_stage = inputs.get("new_stage")
            probability = inputs.get("probability", 50.0)

            # Validate stage
            if new_stage not in VALID_STAGES:
                error = f"Invalid stage '{new_stage}'. Valid stages: {VALID_STAGES}"
                logger.warn("Invalid stage provided", stage=new_stage)
                return IntegrationResult(
                    operation_id="update_opportunity_stage",
                    status=OperationStatus.FAILED,
                    timestamp=datetime.utcnow(),
                    data={},
                    errors=[error],
                )

            # Validate probability range
            if not (0 <= probability <= 100):
                error = "Probability must be between 0 and 100"
                logger.warn("Invalid probability", probability=probability)
                return IntegrationResult(
                    operation_id="update_opportunity_stage",
                    status=OperationStatus.FAILED,
                    timestamp=datetime.utcnow(),
                    data={},
                    errors=[error],
                )

            # Get current stage (mock)
            old_stage = self._get_current_stage(opportunity_id)

            result_data = {
                "opportunity_id": opportunity_id,
                "old_stage": old_stage,
                "new_stage": new_stage,
                "probability": probability,
                "changed_at": datetime.utcnow().isoformat(),
            }

            logger.info(
                "Opportunity stage updated",
                opportunity_id=opportunity_id,
                old_stage=old_stage,
                new_stage=new_stage,
                probability=probability,
            )

            return IntegrationResult(
                operation_id="update_opportunity_stage",
                status=OperationStatus.SUCCESS,
                timestamp=datetime.utcnow(),
                data=result_data,
                errors=[],
            )

        except Exception as e:
            error_msg = f"Error updating opportunity stage: {str(e)}"
            logger.error("Opportunity stage update failed", error=str(e))
            return IntegrationResult(
                operation_id="update_opportunity_stage",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=[error_msg],
            )

    def _get_current_stage(self, opportunity_id: str) -> str:
        """Get current stage for opportunity (mock)."""
        # In production, this would query Salesforce
        return "Prospecting"
