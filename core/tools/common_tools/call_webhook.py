from typing import Dict, Any
from datetime import datetime
import structlog

from core.tools.base import BaseTool, ToolMetadata
from core.integrations.base import IntegrationResult, OperationStatus

logger = structlog.get_logger(__name__)


class CallWebhookTool(BaseTool):
    """Sends HTTP requests to external webhooks and APIs."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="CallWebhookTool",
            description="Sends HTTP requests to external webhooks and APIs",
            category="common",
            version="1.0.0",
            required_inputs={"url": "str", "method": "str"},
            optional_inputs={"headers": "dict", "body": "dict", "timeout_seconds": "int"},
            output_schema={
                "status_code": "int",
                "response_body": "dict",
                "response_time_ms": "int",
                "called_at": "str",
                "success": "bool",
            },
            auth_required=False,
            rate_limit_per_minute=60,
        )

    async def execute(self, inputs: Dict[str, Any]) -> IntegrationResult:
        """Call external webhook."""
        is_valid, errors = await self.validate(inputs)
        if not is_valid:
            return IntegrationResult(
                operation_id="call_webhook",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=errors,
            )

        try:
            url = inputs.get("url")
            method = inputs.get("method", "POST").upper()
            headers = inputs.get("headers", {})
            body = inputs.get("body")
            timeout_seconds = inputs.get("timeout_seconds", 30)

            valid_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"]
            if method not in valid_methods:
                error = f"Invalid HTTP method. Must be one of: {valid_methods}"
                logger.warn("Invalid HTTP method", method=method)
                return IntegrationResult(
                    operation_id="call_webhook",
                    status=OperationStatus.FAILED,
                    timestamp=datetime.utcnow(),
                    data={},
                    errors=[error],
                )

            status_code, response_body, response_time = self._call_webhook(
                url, method, headers, body, timeout_seconds
            )

            success = 200 <= status_code < 300

            result_data = {
                "url": url,
                "method": method,
                "status_code": status_code,
                "response_body": response_body,
                "response_time_ms": response_time,
                "called_at": datetime.utcnow().isoformat(),
                "success": success,
            }

            log_level = "info" if success else "warn"
            logger.bind(level=log_level).msg(
                "Webhook called",
                url=url,
                method=method,
                status_code=status_code,
                response_time_ms=response_time,
            )

            return IntegrationResult(
                operation_id="call_webhook",
                status=OperationStatus.SUCCESS if success else OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data=result_data,
                errors=[] if success else [f"HTTP {status_code}"],
            )

        except Exception as e:
            error_msg = f"Error calling webhook: {str(e)}"
            logger.error("Webhook call failed", error=str(e))
            return IntegrationResult(
                operation_id="call_webhook",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=[error_msg],
            )

    def _call_webhook(
        self,
        url: str,
        method: str,
        headers: Dict[str, str],
        body: Dict[str, Any],
        timeout_seconds: int,
    ) -> tuple[int, Dict[str, Any], int]:
        """Call webhook (mock)."""
        # In production, this would:
        # 1. Validate URL format
        # 2. Add default headers (Content-Type, User-Agent)
        # 3. Execute HTTP request
        # 4. Handle timeouts and retries
        # 5. Parse response body
        status_code = 200
        response_body = {"success": True, "message": "Webhook processed"}
        response_time = 150
        return status_code, response_body, response_time
