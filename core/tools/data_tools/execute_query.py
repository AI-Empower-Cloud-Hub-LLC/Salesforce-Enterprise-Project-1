from typing import Dict, Any, List
from datetime import datetime
import structlog

from core.tools.base import BaseTool, ToolMetadata
from core.integrations.base import IntegrationResult, OperationStatus

logger = structlog.get_logger(__name__)


class ExecuteQueryTool(BaseTool):
    """Executes read-only SQL queries against the database."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="ExecuteQueryTool",
            description="Executes read-only SQL queries and returns results",
            category="data",
            version="1.0.0",
            required_inputs={"query": "str"},
            optional_inputs={"limit": "int", "timeout_seconds": "int"},
            output_schema={
                "rows": "list",
                "row_count": "int",
                "columns": "list",
                "execution_time_ms": "int",
                "executed_at": "str",
            },
            auth_required=True,
            rate_limit_per_minute=60,
        )

    async def execute(self, inputs: Dict[str, Any]) -> IntegrationResult:
        """Execute a read-only SQL query."""
        is_valid, errors = await self.validate(inputs)
        if not is_valid:
            return IntegrationResult(
                operation_id="execute_query",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=errors,
            )

        try:
            query = inputs.get("query")
            limit = inputs.get("limit", 1000)
            timeout_seconds = inputs.get("timeout_seconds", 30)

            if not query:
                error = "No query provided"
                logger.warn("Empty query", limit=limit)
                return IntegrationResult(
                    operation_id="execute_query",
                    status=OperationStatus.FAILED,
                    timestamp=datetime.utcnow(),
                    data={},
                    errors=[error],
                )

            if not query.strip().upper().startswith("SELECT"):
                error = "Only SELECT queries are allowed"
                logger.warn("Non-SELECT query attempted", query=query[:50])
                return IntegrationResult(
                    operation_id="execute_query",
                    status=OperationStatus.FAILED,
                    timestamp=datetime.utcnow(),
                    data={},
                    errors=[error],
                )

            rows, columns, execution_time = self._execute_query(
                query, limit, timeout_seconds
            )

            result_data = {
                "rows": rows,
                "row_count": len(rows),
                "columns": columns,
                "execution_time_ms": execution_time,
                "executed_at": datetime.utcnow().isoformat(),
                "limit": limit,
            }

            logger.info(
                "Query executed successfully",
                row_count=len(rows),
                execution_time_ms=execution_time,
            )

            return IntegrationResult(
                operation_id="execute_query",
                status=OperationStatus.SUCCESS,
                timestamp=datetime.utcnow(),
                data=result_data,
                errors=[],
            )

        except Exception as e:
            error_msg = f"Error executing query: {str(e)}"
            logger.error("Query execution failed", error=str(e))
            return IntegrationResult(
                operation_id="execute_query",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=[error_msg],
            )

    def _execute_query(
        self, query: str, limit: int, timeout_seconds: int
    ) -> tuple[List[Dict[str, Any]], List[str], int]:
        """Execute query (mock)."""
        # In production, this would:
        # 1. Connect to database with timeout
        # 2. Execute parameterized query
        # 3. Fetch results with limit
        # 4. Measure execution time
        columns = ["id", "name", "value"]
        rows = [
            {"id": 1, "name": "record_1", "value": "data_1"},
            {"id": 2, "name": "record_2", "value": "data_2"},
        ]
        execution_time = 45
        return rows, columns, execution_time
