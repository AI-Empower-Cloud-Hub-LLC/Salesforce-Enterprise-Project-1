"""Main orchestrator for managing multi-agent workflow execution."""

from typing import Any, Dict, List, Optional
from datetime import datetime
from uuid import uuid4

import structlog

from core.agents.task_classifier_agent import TaskClassifierAgent
from core.agents.context_gatherer_agent import ContextGathererAgent
from core.agents.action_planner_agent import ActionPlannerAgent
from core.agents.executor_agent import ExecutorAgent
from core.agents.validator_agent import ValidatorAgent
from core.agents.escalator_agent import EscalatorAgent
from core.orchestration.agent_coordinator import AgentCoordinator
from core.orchestration.decision_engine import DecisionEngine

logger = structlog.get_logger(__name__)


class WorkflowOrchestrator:
    """Orchestrates multi-agent workflow execution with state management and coordination."""

    def __init__(self):
        """Initialize workflow orchestrator with agents and coordinators."""
        self.workflow_id = None
        self.execution_history = []
        self.current_state = {}

        # Initialize all agents
        self.task_classifier = TaskClassifierAgent()
        self.context_gatherer = ContextGathererAgent()
        self.action_planner = ActionPlannerAgent()
        self.executor = ExecutorAgent()
        self.validator = ValidatorAgent()
        self.escalator = EscalatorAgent()

        # Initialize coordination components
        self.coordinator = AgentCoordinator()
        self.decision_engine = DecisionEngine()

        # Define workflow pipeline
        self.pipeline = [
            ("classify", self.task_classifier),
            ("gather_context", self.context_gatherer),
            ("plan", self.action_planner),
            ("execute", self.executor),
            ("validate", self.validator),
        ]

    async def execute_workflow(
        self,
        request: Dict[str, Any],
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute complete workflow from request to result.

        Args:
            request: Incoming workflow request
            initial_context: Optional initial context data

        Returns:
            Complete workflow execution result
        """
        self.workflow_id = str(uuid4())
        execution_start = datetime.utcnow()

        logger.info(
            "workflow_started",
            workflow_id=self.workflow_id,
            request_type=request.get("type"),
        )

        # Initialize workflow state
        self.current_state = {
            "workflow_id": self.workflow_id,
            "original_request": request,
            "timestamp": execution_start.isoformat(),
            "status": "in_progress",
            "context": initial_context or {},
        }

        try:
            # Execute pipeline stages
            result = await self._execute_pipeline(request)

            self.current_state["status"] = "completed"
            self.current_state["result"] = result

            logger.info(
                "workflow_completed",
                workflow_id=self.workflow_id,
                duration_seconds=(datetime.utcnow() - execution_start).total_seconds(),
            )

            return self._build_workflow_result(result, execution_start)

        except Exception as e:
            logger.error(
                "workflow_failed",
                workflow_id=self.workflow_id,
                error=str(e),
            )

            self.current_state["status"] = "failed"
            self.current_state["error"] = str(e)

            # Attempt escalation on workflow failure
            escalation_result = await self._handle_workflow_failure(e)

            return {
                "workflow_id": self.workflow_id,
                "status": "failed",
                "error": str(e),
                "escalation": escalation_result,
                "execution_time_seconds": (
                    datetime.utcnow() - execution_start
                ).total_seconds(),
            }

    async def _execute_pipeline(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute agent pipeline in sequence.

        Args:
            request: Incoming request

        Returns:
            Final pipeline result
        """
        pipeline_state = {
            "id": self.workflow_id,
            "original_request": request,
        }

        execution_timeline = []

        for stage_name, agent in self.pipeline:
            stage_start = datetime.utcnow()

            logger.info(
                "pipeline_stage_starting",
                stage=stage_name,
                workflow_id=self.workflow_id,
            )

            try:
                # Execute agent
                result = await agent.execute(pipeline_state, self.current_state)

                stage_duration = (datetime.utcnow() - stage_start).total_seconds()

                execution_timeline.append(
                    {
                        "stage": stage_name,
                        "status": "completed",
                        "duration_seconds": stage_duration,
                        "agent": agent.name,
                    }
                )

                # Update pipeline state with agent result
                pipeline_state[f"{stage_name}_result"] = result

                # Make decision on next steps
                decision = self.decision_engine.evaluate_stage_result(
                    stage_name, result, self.current_state
                )

                if decision.get("escalate"):
                    logger.warning(
                        "escalation_triggered_during_pipeline",
                        stage=stage_name,
                        reason=decision.get("reason"),
                    )
                    pipeline_state["escalation_required"] = True
                    pipeline_state["escalation_reason"] = decision.get("reason")
                    break

                # Check if pipeline should continue
                if not decision.get("continue"):
                    logger.info(
                        "pipeline_halted",
                        stage=stage_name,
                        reason=decision.get("reason"),
                    )
                    break

                logger.info(
                    "pipeline_stage_completed",
                    stage=stage_name,
                    duration_seconds=stage_duration,
                )

            except Exception as e:
                logger.error(
                    "pipeline_stage_failed",
                    stage=stage_name,
                    error=str(e),
                )

                execution_timeline.append(
                    {
                        "stage": stage_name,
                        "status": "failed",
                        "error": str(e),
                    }
                )

                raise

        pipeline_state["execution_timeline"] = execution_timeline
        self.current_state["pipeline_state"] = pipeline_state

        return pipeline_state

    async def _handle_workflow_failure(self, error: Exception) -> Dict[str, Any]:
        """
        Handle workflow failure through escalation.

        Args:
            error: The exception that caused failure

        Returns:
            Escalation result
        """
        escalation_task = {
            "id": self.workflow_id,
            "error_details": {
                "type": type(error).__name__,
                "message": str(error),
                "severity": "high",
            },
        }

        escalation_result = await self.escalator.execute(
            escalation_task, self.current_state
        )

        return escalation_result

    def _build_workflow_result(
        self, pipeline_result: Dict[str, Any], start_time: datetime
    ) -> Dict[str, Any]:
        """
        Build final workflow result combining all stage outputs.

        Args:
            pipeline_result: Result from pipeline execution
            start_time: Workflow start time

        Returns:
            Final workflow result
        """
        execution_time = (datetime.utcnow() - start_time).total_seconds()

        return {
            "workflow_id": self.workflow_id,
            "status": "completed",
            "classification": pipeline_result.get("classify_result"),
            "context": pipeline_result.get("gather_context_result"),
            "execution_plan": pipeline_result.get("plan_result"),
            "execution_result": pipeline_result.get("execute_result"),
            "validation_result": pipeline_result.get("validate_result"),
            "execution_timeline": pipeline_result.get("execution_timeline", []),
            "execution_time_seconds": execution_time,
            "timestamp": start_time.isoformat(),
        }

    def get_workflow_status(self) -> Dict[str, Any]:
        """
        Get current workflow status.

        Returns:
            Workflow status information
        """
        return {
            "workflow_id": self.workflow_id,
            "status": self.current_state.get("status"),
            "state": self.current_state,
            "execution_history": self.execution_history,
        }

    def reset(self) -> None:
        """Reset orchestrator state for next workflow."""
        self.workflow_id = None
        self.current_state = {}
        self.execution_history = []

        logger.info("orchestrator_reset")
