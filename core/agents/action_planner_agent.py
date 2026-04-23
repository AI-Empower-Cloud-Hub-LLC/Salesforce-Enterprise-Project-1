"""Action planner agent for developing execution strategies."""

from typing import Any, Dict, List

import structlog

from core.agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)


class ActionPlannerAgent(BaseAgent):
    """Agent responsible for planning execution strategies and action sequences."""

    def __init__(self):
        """Initialize action planner agent."""
        super().__init__(
            name="ActionPlanner",
            role="Develop execution strategy and action sequences",
            tools=["strategy_engine", "constraint_solver", "decision_tree"],
            max_retries=2,
            timeout=40,
        )

    async def _execute_task(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Develop execution plan based on context and constraints.

        Args:
            task: Task configuration
            context: Gathered workflow context

        Returns:
            Execution plan with action sequence and strategy
        """
        workflow_type = context.get("workflow_type", "general")
        classified_type = context.get("classified_type")

        logger.info(
            "planning_execution",
            workflow_type=workflow_type,
            classified_type=classified_type,
        )

        action_plan = {
            "workflow_id": task.get("id"),
            "strategy": self._determine_strategy(classified_type, context),
            "action_sequence": await self._generate_action_sequence(
                classified_type, context
            ),
            "dependencies": self._identify_dependencies(classified_type),
            "constraints": self._identify_constraints(context),
            "rollback_plan": self._create_rollback_plan(classified_type),
            "success_criteria": self._define_success_criteria(classified_type),
        }

        logger.info(
            "execution_plan_created",
            actions_count=len(action_plan["action_sequence"]),
            strategy=action_plan["strategy"],
        )

        return action_plan

    def _determine_strategy(self, workflow_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine execution strategy based on workflow type and context.

        Args:
            workflow_type: Type of workflow
            context: Workflow context

        Returns:
            Strategy configuration
        """
        strategies = {
            "sales_qualification": {
                "approach": "sequential_validation",
                "parallelizable_steps": False,
                "requires_approval": True,
                "escalation_threshold": 0.7,
            },
            "support_triage": {
                "approach": "parallel_analysis",
                "parallelizable_steps": True,
                "requires_approval": False,
                "escalation_threshold": 0.8,
            },
            "service_processing": {
                "approach": "state_machine",
                "parallelizable_steps": True,
                "requires_approval": False,
                "escalation_threshold": 0.6,
            },
            "contract_review": {
                "approach": "multi_stage_review",
                "parallelizable_steps": False,
                "requires_approval": True,
                "escalation_threshold": 0.5,
            },
        }

        return strategies.get(
            workflow_type,
            {
                "approach": "standard",
                "parallelizable_steps": False,
                "requires_approval": False,
                "escalation_threshold": 0.75,
            },
        )

    async def _generate_action_sequence(
        self,
        workflow_type: str,
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Generate sequence of actions for workflow execution.

        Args:
            workflow_type: Type of workflow
            context: Workflow context

        Returns:
            Ordered list of actions
        """
        base_sequence = [
            {
                "step": 1,
                "action": "data_validation",
                "description": "Validate input data quality",
                "tools": ["validator"],
                "timeout_seconds": 30,
            },
            {
                "step": 2,
                "action": "enrichment",
                "description": "Enrich data with additional context",
                "tools": ["data_enricher"],
                "timeout_seconds": 45,
            },
            {
                "step": 3,
                "action": "analysis",
                "description": "Analyze enriched data",
                "tools": ["analyzer"],
                "timeout_seconds": 60,
            },
        ]

        if workflow_type == "sales_qualification":
            base_sequence.extend(
                [
                    {
                        "step": 4,
                        "action": "lead_scoring",
                        "description": "Score lead quality",
                        "tools": ["ml_scorer"],
                        "timeout_seconds": 30,
                    },
                    {
                        "step": 5,
                        "action": "routing",
                        "description": "Route to appropriate sales team",
                        "tools": ["router"],
                        "timeout_seconds": 20,
                    },
                ]
            )
        elif workflow_type == "support_triage":
            base_sequence.extend(
                [
                    {
                        "step": 4,
                        "action": "priority_assignment",
                        "description": "Assign issue priority",
                        "tools": ["priority_engine"],
                        "timeout_seconds": 20,
                    },
                    {
                        "step": 5,
                        "action": "ticket_creation",
                        "description": "Create support ticket",
                        "tools": ["ticket_system"],
                        "timeout_seconds": 30,
                    },
                ]
            )

        base_sequence.append(
            {
                "step": len(base_sequence) + 1,
                "action": "notification",
                "description": "Send notifications to stakeholders",
                "tools": ["notifier"],
                "timeout_seconds": 15,
            }
        )

        return base_sequence

    def _identify_dependencies(self, workflow_type: str) -> List[Dict[str, Any]]:
        """
        Identify action dependencies.

        Args:
            workflow_type: Type of workflow

        Returns:
            List of dependencies
        """
        return [
            {
                "action_a": "data_validation",
                "action_b": "enrichment",
                "type": "sequential",
            },
            {
                "action_a": "enrichment",
                "action_b": "analysis",
                "type": "sequential",
            },
        ]

    def _identify_constraints(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Identify execution constraints.

        Args:
            context: Workflow context

        Returns:
            Constraints configuration
        """
        constraints = {
            "time_limit_minutes": 30,
            "max_retries": 3,
            "rate_limiting": {"requests_per_minute": 100},
            "resource_limits": {
                "memory_mb": 1024,
                "cpu_cores": 2,
            },
        }

        return constraints

    def _create_rollback_plan(self, workflow_type: str) -> Dict[str, Any]:
        """
        Create rollback plan for failure scenarios.

        Args:
            workflow_type: Type of workflow

        Returns:
            Rollback strategy
        """
        return {
            "enabled": True,
            "revert_on_failure": True,
            "state_checkpoint_frequency": "every_step",
            "cleanup_actions": [
                "remove_temporary_data",
                "reset_state",
                "notify_stakeholders",
            ],
        }

    def _define_success_criteria(self, workflow_type: str) -> Dict[str, Any]:
        """
        Define success criteria for workflow completion.

        Args:
            workflow_type: Type of workflow

        Returns:
            Success criteria
        """
        criteria = {
            "primary": {
                "condition": "all_steps_completed",
                "required": True,
            },
            "secondary": {
                "condition": "data_validation_passed",
                "required": True,
            },
            "tertiary": {
                "condition": "stakeholder_notification_sent",
                "required": False,
            },
        }

        return criteria
