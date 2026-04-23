"""Task classifier agent for intelligent request categorization."""

from typing import Any, Dict

import structlog

from core.agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)


class TaskClassifierAgent(BaseAgent):
    """Agent responsible for classifying incoming requests and tasks."""

    def __init__(self):
        """Initialize task classifier agent."""
        super().__init__(
            name="TaskClassifier",
            role="Classify incoming requests and determine workflow type",
            tools=["nlp_analyzer", "pattern_matcher", "knowledge_base"],
            max_retries=3,
            timeout=30,
        )
        self.classification_rules = {}
        self.confidence_threshold = 0.8

    async def _execute_task(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Classify task and determine workflow type.

        Args:
            task: Input task with request data
            context: Workflow execution context

        Returns:
            Classification result with workflow type and confidence
        """
        request_data = task.get("data", {})
        request_text = request_data.get("description", "")
        request_type = request_data.get("type", "general")

        logger.info(
            "classifying_task",
            request_type=request_type,
            text_length=len(request_text),
        )

        classification_result = {
            "original_type": request_type,
            "classified_type": self._classify_request(request_text, request_type),
            "confidence": 0.95,
            "sub_category": self._determine_subcategory(request_text),
            "priority": self._determine_priority(request_data),
            "routing_path": self._determine_routing_path(request_text),
            "requirements": self._extract_requirements(request_text),
        }

        logger.info(
            "task_classified",
            classified_type=classification_result["classified_type"],
            confidence=classification_result["confidence"],
        )

        return classification_result

    def _classify_request(self, text: str, request_type: str) -> str:
        """
        Classify request based on content and type.

        Args:
            text: Request text content
            request_type: Request type hint

        Returns:
            Classified workflow type
        """
        text_lower = text.lower()

        # Sales workflow
        if any(
            keyword in text_lower
            for keyword in ["lead", "prospect", "sales", "opportunity", "deal"]
        ):
            return "sales_qualification"

        # Support workflow
        if any(
            keyword in text_lower
            for keyword in ["issue", "problem", "support", "ticket", "help"]
        ):
            return "support_triage"

        # Service workflow
        if any(
            keyword in text_lower
            for keyword in ["service", "request", "order", "fulfillment", "delivery"]
        ):
            return "service_processing"

        # Contract workflow
        if any(
            keyword in text_lower
            for keyword in ["contract", "agreement", "document", "review", "approval"]
        ):
            return "contract_review"

        return request_type or "general_workflow"

    def _determine_subcategory(self, text: str) -> str:
        """Determine sub-category within workflow."""
        text_lower = text.lower()

        if any(keyword in text_lower for keyword in ["urgent", "critical", "asap"]):
            return "high_priority"

        if any(keyword in text_lower for keyword in ["batch", "bulk", "multiple"]):
            return "bulk_processing"

        return "standard"

    def _determine_priority(self, request_data: Dict[str, Any]) -> str:
        """Determine request priority level."""
        if request_data.get("priority") == "urgent":
            return "high"

        if request_data.get("customer_tier") == "enterprise":
            return "high"

        return "normal"

    def _determine_routing_path(self, text: str) -> str:
        """Determine execution routing path."""
        text_lower = text.lower()

        if any(keyword in text_lower for keyword in ["salesforce", "crm"]):
            return "salesforce_route"

        if any(keyword in text_lower for keyword in ["database", "data", "record"]):
            return "database_route"

        return "standard_route"

    def _extract_requirements(self, text: str) -> Dict[str, Any]:
        """Extract special requirements from request."""
        requirements = {
            "requires_approval": "approval" in text.lower(),
            "requires_notification": "notify" in text.lower(),
            "requires_escalation": any(
                keyword in text.lower()
                for keyword in ["escalate", "manager", "review"]
            ),
            "data_sensitivity": "sensitive" in text.lower(),
        }

        return requirements
