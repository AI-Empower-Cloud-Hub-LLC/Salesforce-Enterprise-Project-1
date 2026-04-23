from typing import Dict, Any, List
from datetime import datetime
import structlog

from core.tools.base import BaseTool, ToolMetadata
from core.integrations.base import IntegrationResult, OperationStatus

logger = structlog.get_logger(__name__)


class NotifyTool(BaseTool):
    """Sends notifications via email, Slack, or webhooks."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="NotifyTool",
            description="Sends notifications via email, Slack, or webhooks",
            category="common",
            version="1.0.0",
            required_inputs={"channel": "str", "message": "str"},
            optional_inputs={"recipients": "list", "metadata": "dict", "priority": "str"},
            output_schema={
                "notification_id": "str",
                "channel": "str",
                "status": "str",
                "recipients_count": "int",
                "sent_at": "str",
                "delivery_status": "dict",
            },
            auth_required=True,
            rate_limit_per_minute=60,
        )

    async def execute(self, inputs: Dict[str, Any]) -> IntegrationResult:
        """Send notification via specified channel."""
        is_valid, errors = await self.validate(inputs)
        if not is_valid:
            return IntegrationResult(
                operation_id="notify",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=errors,
            )

        try:
            channel = inputs.get("channel", "").lower()
            message = inputs.get("message")
            recipients = inputs.get("recipients", [])
            metadata = inputs.get("metadata", {})
            priority = inputs.get("priority", "normal")

            valid_channels = ["email", "slack", "webhook", "sms"]
            if channel not in valid_channels:
                error = f"Invalid channel. Must be one of: {valid_channels}"
                logger.warn("Invalid notification channel", channel=channel)
                return IntegrationResult(
                    operation_id="notify",
                    status=OperationStatus.FAILED,
                    timestamp=datetime.utcnow(),
                    data={},
                    errors=[error],
                )

            if not message:
                error = "No message provided for notification"
                logger.warn("Empty notification message")
                return IntegrationResult(
                    operation_id="notify",
                    status=OperationStatus.FAILED,
                    timestamp=datetime.utcnow(),
                    data={},
                    errors=[error],
                )

            delivery_status = self._send_notification(
                channel, message, recipients, metadata, priority
            )

            result_data = {
                "notification_id": f"notif_{int(datetime.utcnow().timestamp())}",
                "channel": channel,
                "status": "sent",
                "recipients_count": len(recipients),
                "sent_at": datetime.utcnow().isoformat(),
                "delivery_status": delivery_status,
                "priority": priority,
            }

            logger.info(
                "Notification sent",
                channel=channel,
                recipients_count=len(recipients),
                priority=priority,
            )

            return IntegrationResult(
                operation_id="notify",
                status=OperationStatus.SUCCESS,
                timestamp=datetime.utcnow(),
                data=result_data,
                errors=[],
            )

        except Exception as e:
            error_msg = f"Error sending notification: {str(e)}"
            logger.error("Notification send failed", error=str(e))
            return IntegrationResult(
                operation_id="notify",
                status=OperationStatus.FAILED,
                timestamp=datetime.utcnow(),
                data={},
                errors=[error_msg],
            )

    def _send_notification(
        self,
        channel: str,
        message: str,
        recipients: List[str],
        metadata: Dict[str, Any],
        priority: str,
    ) -> Dict[str, Any]:
        """Send notification (mock)."""
        # In production, this would:
        # 1. For email: Use SMTP or email service (SendGrid, AWS SES)
        # 2. For Slack: Call Slack API with webhook or bot token
        # 3. For webhook: POST to provided URL
        # 4. For SMS: Use Twilio or similar service
        # 5. Track delivery status
        # 6. Implement retry logic for failures
        delivery_status = {
            "successful": len(recipients),
            "failed": 0,
            "details": [{"recipient": r, "status": "delivered"} for r in recipients],
        }
        return delivery_status
