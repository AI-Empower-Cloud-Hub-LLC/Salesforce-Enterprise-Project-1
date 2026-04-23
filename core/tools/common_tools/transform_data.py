from typing import Dict, Any, List
from datetime import datetime
import structlog

from core.tools.base import BaseTool, ToolMetadata
from core.integrations.base import IntegrationResult, OperationStatus

logger = structlog.get_logger(__name__)


class TransformDataTool(BaseTool):
    """Applies transformations to data (mapping, aggregation, filtering)."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="TransformDataTool",
            description="Applies transformations to data including mapping, aggregation, and filtering",
            category="common",
            version="1.0.0",
            required_inputs={"data": "list", "transformation": "dict"},
            optional_inputs={"context": "dict"},
            output_schema={
                "transformed_data": "list",
                "record_count": "int",
                "transformation_type": "str",
                "duration_ms": "int",
                "transformed_at": "str",
            },
            auth_required=False,
            rate_limit_per_minute=100,
        )

    async def execute(self, inputs: Dict[str, Any]) -> IntegrationResult:
        """Apply data transformations."""
        is_valid, errors = await self.validate(inputs)
        if not is_valid:
            return IntegrationResult(
                operation_id="transform_data",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=errors,
            )

        try:
            data = inputs.get("data", [])
            transformation = inputs.get("transformation", {})
            context = inputs.get("context", {})

            if not data:
                error = "No data provided for transformation"
                logger.warn("Empty data list")
                return IntegrationResult(
                    operation_id="transform_data",
                    status=OperationStatus.FAILED,
                    timestamp=datetime.utcnow(),
                    data={},
                    errors=[error],
                )

            if not transformation:
                error = "No transformation rules provided"
                logger.warn("No transformation rules")
                return IntegrationResult(
                    operation_id="transform_data",
                    status=OperationStatus.FAILED,
                    timestamp=datetime.utcnow(),
                    data={},
                    errors=[error],
                )

            transformed_data, duration_ms = self._apply_transformation(
                data, transformation, context
            )

            result_data = {
                "transformed_data": transformed_data,
                "record_count": len(transformed_data),
                "transformation_type": transformation.get("type", "unknown"),
                "duration_ms": duration_ms,
                "transformed_at": datetime.utcnow().isoformat(),
                "original_count": len(data),
            }

            logger.info(
                "Data transformation completed",
                original_count=len(data),
                transformed_count=len(transformed_data),
                duration_ms=duration_ms,
            )

            return IntegrationResult(
                operation_id="transform_data",
                status=OperationStatus.SUCCESS,
                timestamp=datetime.utcnow(),
                data=result_data,
                errors=[],
            )

        except Exception as e:
            error_msg = f"Error transforming data: {str(e)}"
            logger.error("Data transformation failed", error=str(e))
            return IntegrationResult(
                operation_id="transform_data",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=[error_msg],
            )

    def _apply_transformation(
        self,
        data: List[Dict[str, Any]],
        transformation: Dict[str, Any],
        context: Dict[str, Any],
    ) -> tuple[List[Dict[str, Any]], int]:
        """Apply transformation rules (mock)."""
        # In production, this would:
        # 1. Parse transformation rules (mapping, aggregation, filtering)
        # 2. Apply field mappings (rename, compute derived fields)
        # 3. Filter records based on conditions
        # 4. Aggregate data if specified
        # 5. Enrich with context if provided
        #
        # Transformation format:
        # {
        #   "type": "mapping|aggregation|filter",
        #   "mappings": {"old_field": "new_field"},
        #   "filters": {"field": {"operator": "value"}},
        #   "aggregations": {"sum": ["amount"], "count": "*"}
        # }
        transformed_data = [
            {
                "id": record.get("id"),
                "name": record.get("name"),
                "transformed": True,
            }
            for record in data
        ]
        duration_ms = 75
        return transformed_data, duration_ms
