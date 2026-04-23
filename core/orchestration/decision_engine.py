"""Decision engine for evaluating stage results and making pipeline routing decisions."""

from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)


class DecisionEngine:
    """Evaluates stage results and makes decisions on pipeline continuation, escalation, and routing."""

    def __init__(self):
        """Initialize decision engine."""
        self.decision_history = []
        self.escalation_threshold = 0.7
        self.confidence_threshold = 0.6

    def evaluate_stage_result(
        self,
        stage_name: str,
        result: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Evaluate stage result and determine next actions.

        Args:
            stage_name: Name of the completed stage
            result: Result from the stage
            context: Current workflow context

        Returns:
            Decision dict with actions and reasons
        """
        decision = {
            "stage": stage_name,
            "continue": True,
            "escalate": False,
            "reason": None,
            "confidence": 0.95,
        }

        # Stage-specific evaluation
        if stage_name == "classify":
            decision.update(self._evaluate_classification(result, context))
        elif stage_name == "gather_context":
            decision.update(self._evaluate_context_gathering(result, context))
        elif stage_name == "plan":
            decision.update(self._evaluate_planning(result, context))
        elif stage_name == "execute":
            decision.update(self._evaluate_execution(result, context))
        elif stage_name == "validate":
            decision.update(self._evaluate_validation(result, context))

        self.decision_history.append(decision)

        logger.info(
            "stage_evaluated",
            stage=stage_name,
            continue_pipeline=decision["continue"],
            escalate=decision["escalate"],
            confidence=decision["confidence"],
        )

        return decision

    def _evaluate_classification(
        self, result: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate classification stage results.

        Args:
            result: Classification result
            context: Workflow context

        Returns:
            Evaluation decision
        """
        classified_type = result.get("classified_type")
        confidence = result.get("confidence", 0.0)

        # Check if classification confidence is sufficient
        if confidence < self.confidence_threshold:
            return {
                "continue": False,
                "escalate": True,
                "reason": f"Low classification confidence ({confidence:.2f})",
                "confidence": confidence,
            }

        # Check if classification type is recognized
        valid_types = [
            "sales_qualification",
            "support_triage",
            "service_processing",
            "contract_review",
        ]
        if classified_type not in valid_types:
            return {
                "continue": False,
                "escalate": True,
                "reason": f"Unknown classification type: {classified_type}",
                "confidence": 0.0,
            }

        return {
            "continue": True,
            "escalate": False,
            "reason": "Classification successful",
            "confidence": confidence,
        }

    def _evaluate_context_gathering(
        self, result: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate context gathering stage results.

        Args:
            result: Context gathering result
            context: Workflow context

        Returns:
            Evaluation decision
        """
        gathered_sources = result.get("gathered_from", [])
        data_quality = result.get("data_quality_score", 0.0)

        # Check data quality
        if data_quality < 0.5:
            return {
                "continue": False,
                "escalate": True,
                "reason": f"Insufficient data quality ({data_quality:.2f})",
                "confidence": data_quality,
            }

        # Check if critical context was gathered
        if len(gathered_sources) == 0:
            return {
                "continue": False,
                "escalate": True,
                "reason": "No context sources found",
                "confidence": 0.0,
            }

        return {
            "continue": True,
            "escalate": False,
            "reason": "Context gathered successfully",
            "confidence": min(data_quality, 0.95),
        }

    def _evaluate_planning(
        self, result: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate action planning stage results.

        Args:
            result: Planning result
            context: Workflow context

        Returns:
            Evaluation decision
        """
        action_sequence = result.get("action_sequence", [])
        plan_feasibility = result.get("feasibility_score", 0.0)

        # Check if plan is feasible
        if plan_feasibility < 0.6:
            return {
                "continue": False,
                "escalate": True,
                "reason": f"Plan not feasible ({plan_feasibility:.2f})",
                "confidence": plan_feasibility,
            }

        # Check if action sequence exists
        if len(action_sequence) == 0:
            return {
                "continue": False,
                "escalate": True,
                "reason": "No executable actions planned",
                "confidence": 0.0,
            }

        return {
            "continue": True,
            "escalate": False,
            "reason": f"Plan created with {len(action_sequence)} actions",
            "confidence": plan_feasibility,
        }

    def _evaluate_execution(
        self, result: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate execution stage results.

        Args:
            result: Execution result
            context: Workflow context

        Returns:
            Evaluation decision
        """
        execution_summary = result.get("execution_summary", {})
        successful = execution_summary.get("successful", 0)
        failed = execution_summary.get("failed", 0)

        total = successful + failed
        if total == 0:
            return {
                "continue": False,
                "escalate": True,
                "reason": "No actions were executed",
                "confidence": 0.0,
            }

        success_rate = successful / total
        failed_actions = result.get("failed_actions", [])

        # Check for critical failures
        for action in failed_actions:
            if action.get("critical"):
                return {
                    "continue": False,
                    "escalate": True,
                    "reason": f"Critical action failed: {action.get('action')}",
                    "confidence": success_rate,
                }

        # Check overall success rate
        if success_rate < 0.7:
            return {
                "continue": False,
                "escalate": True,
                "reason": f"Low execution success rate ({success_rate:.2%})",
                "confidence": success_rate,
            }

        return {
            "continue": True,
            "escalate": False,
            "reason": f"Execution successful ({success_rate:.2%} success rate)",
            "confidence": min(success_rate, 0.95),
        }

    def _evaluate_validation(
        self, result: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate validation stage results.

        Args:
            result: Validation result
            context: Workflow context

        Returns:
            Evaluation decision
        """
        validation_status = result.get("validation_status", "failed")
        quality_score = result.get("quality_score", 0.0)

        if validation_status == "failed":
            return {
                "continue": False,
                "escalate": True,
                "reason": f"Validation failed (quality score: {quality_score:.2f})",
                "confidence": quality_score,
            }

        # Check quality score threshold
        if quality_score < 0.8:
            return {
                "continue": False,
                "escalate": True,
                "reason": f"Quality score below threshold ({quality_score:.2f})",
                "confidence": quality_score,
            }

        return {
            "continue": True,
            "escalate": False,
            "reason": f"Validation passed (quality score: {quality_score:.2f})",
            "confidence": quality_score,
        }

    def should_halt_pipeline(
        self, decision: Dict[str, Any]
    ) -> bool:
        """
        Determine if pipeline should halt.

        Args:
            decision: Decision from evaluation

        Returns:
            True if pipeline should halt
        """
        return not decision.get("continue", True)

    def should_escalate(self, decision: Dict[str, Any]) -> bool:
        """
        Determine if escalation is needed.

        Args:
            decision: Decision from evaluation

        Returns:
            True if escalation is needed
        """
        return decision.get("escalate", False)

    def get_decision_history(self) -> list:
        """
        Get decision history.

        Returns:
            List of all decisions made
        """
        return self.decision_history

    def reset(self) -> None:
        """Reset decision engine state."""
        self.decision_history = []

        logger.info("decision_engine_reset")
