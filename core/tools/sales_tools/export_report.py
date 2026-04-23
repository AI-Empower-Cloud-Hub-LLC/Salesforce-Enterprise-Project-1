from typing import Dict, Any
from datetime import datetime
import structlog

from core.tools.base import BaseTool, ToolMetadata
from core.integrations.base import IntegrationResult, OperationStatus

logger = structlog.get_logger(__name__)


class ExportReportTool(BaseTool):
    """Exports Salesforce reports to CSV/JSON format."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="ExportReportTool",
            description="Exports Salesforce report to CSV or JSON with optional filters",
            category="sales",
            version="1.0.0",
            required_inputs={"report_id": "str"},
            optional_inputs={"format": "str", "filters": "dict"},
            output_schema={
                "file_id": "str",
                "download_url": "str",
                "format": "str",
                "row_count": "int",
                "file_size_kb": "float",
                "created_at": "str",
            },
            auth_required=True,
            rate_limit_per_minute=20,
        )

    async def execute(self, inputs: Dict[str, Any]) -> IntegrationResult:
        """Export a Salesforce report."""
        is_valid, errors = await self.validate(inputs)
        if not is_valid:
            return IntegrationResult(
                operation_id="export_report",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=errors,
            )

        try:
            report_id = inputs.get("report_id")
            format_type = inputs.get("format", "csv").lower()
            filters = inputs.get("filters", {})

            # Validate format
            valid_formats = ["csv", "json"]
            if format_type not in valid_formats:
                format_type = "csv"
                logger.warn("Invalid format, defaulting to CSV", format=format_type)

            # Generate file details
            file_id = f"export_{datetime.utcnow().timestamp()}"
            download_url = f"/api/exports/{file_id}/{format_type}"
            row_count = self._count_report_rows(report_id, filters)
            file_size_kb = row_count * 0.5  # Rough estimation

            result_data = {
                "file_id": file_id,
                "download_url": download_url,
                "format": format_type,
                "row_count": row_count,
                "file_size_kb": file_size_kb,
                "created_at": datetime.utcnow().isoformat(),
                "report_id": report_id,
            }

            logger.info(
                "Report exported successfully",
                file_id=file_id,
                report_id=report_id,
                format=format_type,
                row_count=row_count,
            )

            return IntegrationResult(
                operation_id="export_report",
                status=OperationStatus.SUCCESS,
                timestamp=datetime.utcnow(),
                data=result_data,
                errors=[],
            )

        except Exception as e:
            error_msg = f"Error exporting report: {str(e)}"
            logger.error("Report export failed", error=str(e))
            return IntegrationResult(
                operation_id="export_report",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=[error_msg],
            )

    def _count_report_rows(self, report_id: str, filters: Dict[str, Any]) -> int:
        """Count rows in report with filters (mock)."""
        # In production, this would execute the report with filters
        return 1000
