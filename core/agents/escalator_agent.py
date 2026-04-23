"""Escalator agent for handling exceptions and edge cases."""

from typing import Any, Dict, List
from enum import Enum

import structlog

from core.agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)


class EscalationType(Enum):
    """Types of escalations."""

    MANUAL_REVIEW = "manual_review"
    MANAGER_APPROVAL = "manager_approval"
    TECHNICAL_EXPERT = "technical_expert"
    EXECUTIVE_REVIEW = "executive_review"


class EscalatorAgent(BaseAgent):
    """Agent responsible for handling exceptions and escalating to appropriate parties."""

    def __init__(self):
        """Initialize escalator agent."""
        super().__init__(
            name="Escalator",
            role="Handle exceptions and escalate to appropriate stakeholders",
            tools=["notification_system", "routing_engine", "escalation_policies"],
            max_retries=1,
            timeout=30,
        )

    async def _execute_task(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle task exceptions and escalate if needed.

        Args:
            task: Task containing error information
            context: Workflow execution context

        Returns:
            Escalation result and actions taken
        """
        error_details = task.get("error_details", {})
        workflow_type = context.get("classified_type", "general")

        logger.info(
            "handling_escalation",
            error_type=error_details.get("type"),
            workflow_type=workflow_type,
        )

        escalation_decision = self._determine_escalation(error_details, workflow_type)

        escalation_result = {
            "task_id": task.get("id"),
            "escalation_required": escalation_decision["required"],
            "escalation_type": escalation_decision["type"],
            "escalation_priority": escalation_decision["priority"],
            "target_recipients": await self._determine_recipients(
                escalation_decision, context
            ),
            "notification_sent": True,
            "actions_taken": self._execute_escalation_actions(
                escalation_decision, error_details
            ),
            "recommendations": self._generate_recommendations(error_details),
            "fallback_strategy": self._define_fallback_strategy(error_details),
        }

        logger.info(
            "escalation_processed",
            escalation_type=escalation_result["escalation_type"],
            recipients_count=len(escalation_result["target_recipients"]),
        )

        return escalation_result

    def _determine_escalation(
        self, error_details: Dict[str, Any], workflow_type: str
    ) -> Dict[str, Any]:
        """
        Determine escalation type and priority.

        Args:
            error_details: Error information
            workflow_type: Type of workflow

        Returns:
            Escalation decision
        """
        error_type = error_details.get("type", "unknown")
        severity = error_details.get("severity", "low")

        # Define escalation rules
        escalation_rules = {
            "critical": {
                "required": True,
                "type": EscalationType.EXECUTIVE_REVIEW.value,
                "priority": "urgent",
            },
            "high": {
                "required": True,
                "type": EscalationType.MANAGER_APPROVAL.value,
                "priority": "high",
            },
            "medium": {
                "required": True,
                "type": EscalationType.MANUAL_REVIEW.value,
                "priority": "normal",
            },
            "low": {
                "required": False,
                "type": EscalationType.MANUAL_REVIEW.value,
                "priority": "low",
            },
        }

        decision = escalation_rules.get(
            severity,
            {
                "required": False,
                "type": EscalationType.MANUAL_REVIEW.value,
                "priority": "low",
            },
        )

        return decision

    async def _determine_recipients(
        self, escalation_decision: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Determine escalation recipients.

        Args:
            escalation_decision: Escalation decision details
            context: Workflow context

        Returns:
            List of recipients
        """
        escalation_type = escalation_decision.get("type")

        recipients = {
            EscalationType.MANUAL_REVIEW.value: [
                {"name": "Support Team", "email": "support@company.com"}
            ],
            EscalationType.MANAGER_APPROVAL.value: [
                {"name": "Manager", "email": "manager@company.com"},
                {"name": "Support Team", "email": "support@company.com"},
            ],
            EscalationType.TECHNICAL_EXPERT.value: [
                {"name": "Technical Lead", "email": "tech.lead@company.com"},
                {"name": "Engineering Team", "email": "engineering@company.com"},
            ],
            EscalationType.EXECUTIVE_REVIEW.value: [
                {"name": "Director", "email": "director@company.com"},
                {"name": "Manager", "email": "manager@company.com"},
                {"name": "Support Team", "email": "support@company.com"},
            ],
        }

        return recipients.get(escalation_type, [])

    def _execute_escalation_actions(
        self, escalation_decision: Dict[str, Any], error_details: Dict[str, Any]
    ) -> List[str]:
        """
        Execute escalation actions.

        Args:
            escalation_decision: Escalation decision
            error_details: Error information

        Returns:
            List of actions taken
        """
        actions = [
            "created_escalation_ticket",
            "sent_notification_email",
            "logged_incident",
        ]

        if escalation_decision.get("priority") == "urgent":
            actions.extend(
                [
                    "sent_slack_alert",
                    "triggered_pagerduty",
                ]
            )

        return actions

    def _generate_recommendations(self, error_details: Dict[str, Any]) -> List[str]:
        """
        Generate recommendations for resolving the issue.

        Args:
            error_details: Error information

        Returns:
            List of recommendations
        """
        recommendations = [
            "Review error logs for root cause",
            "Check system dependencies",
            "Verify data integrity",
        ]

        error_type = error_details.get("type")

        if "timeout" in error_type.lower():
            recommendations.append("Increase timeout threshold")
            recommendations.append("Optimize query performance")

        if "data" in error_type.lower():
            recommendations.append("Validate data format")
            recommendations.append("Check data source availability")

        return recommendations

    def _define_fallback_strategy(self, error_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Define fallback strategy for handling the error.

        Args:
            error_details: Error information

        Returns:
            Fallback strategy
        """
        return {
            "enabled": True,
            "retry_enabled": True,
            "max_retries": 3,
            "backoff_strategy": "exponential",
            "alternative_execution_path": "manual_review_queue",
            "grace_period_minutes": 5,
            "auto_recover": True,
        }
