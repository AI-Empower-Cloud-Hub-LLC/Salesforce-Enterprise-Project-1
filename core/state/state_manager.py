"""Manages workflow state lifecycle and persistence."""

from typing import Any, Dict, Optional
from threading import RLock
from datetime import datetime

import structlog

from core.state.workflow_state import WorkflowState, StageExecution, WorkflowStatus

logger = structlog.get_logger(__name__)


class StateManager:
    """Manages workflow state lifecycle, updates, and persistence."""

    def __init__(self):
        """Initialize state manager with in-memory state cache."""
        self._states: Dict[str, WorkflowState] = {}
        self._lock = RLock()
        self._persistence = None

    def set_persistence(self, persistence) -> None:
        """
        Set the persistence layer for state storage.

        Args:
            persistence: Persistence implementation
        """
        self._persistence = persistence
        logger.info("persistence_layer_set")

    def create_workflow_state(
        self, workflow_id: str, request: Dict[str, Any]
    ) -> WorkflowState:
        """
        Create and register a new workflow state.

        Args:
            workflow_id: Unique workflow identifier
            request: Original workflow request

        Returns:
            Created WorkflowState instance
        """
        with self._lock:
            if workflow_id in self._states:
                logger.warning(
                    "workflow_state_already_exists",
                    workflow_id=workflow_id,
                )
                return self._states[workflow_id]

            state = WorkflowState(workflow_id, request)
            self._states[workflow_id] = state

            logger.info(
                "workflow_state_created",
                workflow_id=workflow_id,
            )

            return state

    def get_workflow_state(self, workflow_id: str) -> Optional[WorkflowState]:
        """
        Retrieve workflow state by ID.

        Args:
            workflow_id: Workflow identifier

        Returns:
            WorkflowState or None if not found
        """
        with self._lock:
            return self._states.get(workflow_id)

    def update_workflow_status(
        self, workflow_id: str, status: str, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update workflow status.

        Args:
            workflow_id: Workflow identifier
            status: New status value
            details: Optional status details
        """
        state = self.get_workflow_state(workflow_id)
        if not state:
            logger.warning(
                "workflow_state_not_found",
                workflow_id=workflow_id,
            )
            return

        state.update_status(status, details)
        self._persist_state(state)

        logger.info(
            "workflow_status_updated",
            workflow_id=workflow_id,
            status=status,
        )

    def add_stage_execution(
        self, workflow_id: str, stage: StageExecution
    ) -> None:
        """
        Add stage execution to workflow timeline.

        Args:
            workflow_id: Workflow identifier
            stage: Stage execution details
        """
        state = self.get_workflow_state(workflow_id)
        if not state:
            logger.warning(
                "workflow_state_not_found",
                workflow_id=workflow_id,
            )
            return

        state.add_stage_execution(stage)
        self._persist_state(state)

        logger.info(
            "stage_execution_added",
            workflow_id=workflow_id,
            stage_name=stage.stage_name,
        )

    def set_context_value(
        self, workflow_id: str, key: str, value: Any
    ) -> None:
        """
        Set a context value in workflow state.

        Args:
            workflow_id: Workflow identifier
            key: Context key
            value: Context value
        """
        state = self.get_workflow_state(workflow_id)
        if not state:
            logger.warning(
                "workflow_state_not_found",
                workflow_id=workflow_id,
            )
            return

        state.set_context(key, value)
        self._persist_state(state)

    def get_context_value(
        self, workflow_id: str, key: str, default: Any = None
    ) -> Any:
        """
        Get a context value from workflow state.

        Args:
            workflow_id: Workflow identifier
            key: Context key
            default: Default value if not found

        Returns:
            Context value or default
        """
        state = self.get_workflow_state(workflow_id)
        if not state:
            return default

        return state.get_context(key, default)

    def mark_completed(self, workflow_id: str) -> None:
        """
        Mark workflow as completed.

        Args:
            workflow_id: Workflow identifier
        """
        state = self.get_workflow_state(workflow_id)
        if not state:
            logger.warning(
                "workflow_state_not_found",
                workflow_id=workflow_id,
            )
            return

        state.mark_completed()
        self._persist_state(state)

        logger.info(
            "workflow_marked_completed",
            workflow_id=workflow_id,
        )

    def mark_failed(
        self,
        workflow_id: str,
        error: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Mark workflow as failed.

        Args:
            workflow_id: Workflow identifier
            error: Error message
            details: Optional error details
        """
        state = self.get_workflow_state(workflow_id)
        if not state:
            logger.warning(
                "workflow_state_not_found",
                workflow_id=workflow_id,
            )
            return

        state.mark_failed(error, details)
        self._persist_state(state)

        logger.info(
            "workflow_marked_failed",
            workflow_id=workflow_id,
            error=error,
        )

    def mark_escalated(
        self, workflow_id: str, escalation_result: Dict[str, Any]
    ) -> None:
        """
        Mark workflow as escalated.

        Args:
            workflow_id: Workflow identifier
            escalation_result: Escalation details
        """
        state = self.get_workflow_state(workflow_id)
        if not state:
            logger.warning(
                "workflow_state_not_found",
                workflow_id=workflow_id,
            )
            return

        state.mark_escalated(escalation_result)
        self._persist_state(state)

        logger.info(
            "workflow_marked_escalated",
            workflow_id=workflow_id,
        )

    def get_workflow_summary(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get workflow summary information.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Workflow summary or None
        """
        state = self.get_workflow_state(workflow_id)
        if not state:
            return None

        return {
            "workflow_id": state.workflow_id,
            "status": state.status,
            "created_at": state.created_at.isoformat(),
            "updated_at": state.updated_at.isoformat(),
            "completed_at": state.completed_at.isoformat()
            if state.completed_at
            else None,
            "stage_count": len(state.timeline.stages),
            "audit_trail_size": len(state.audit_trail),
        }

    def get_workflow_full_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete workflow state as dictionary.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Complete workflow state or None
        """
        state = self.get_workflow_state(workflow_id)
        if not state:
            return None

        return state.to_dict()

    def restore_workflow_state(self, workflow_id: str) -> Optional[WorkflowState]:
        """
        Restore workflow state from persistence layer.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Restored WorkflowState or None
        """
        if not self._persistence:
            logger.warning("persistence_layer_not_configured")
            return None

        state_data = self._persistence.load_workflow_state(workflow_id)
        if not state_data:
            return None

        state = WorkflowState.from_dict(state_data)
        with self._lock:
            self._states[workflow_id] = state

        logger.info(
            "workflow_state_restored",
            workflow_id=workflow_id,
        )

        return state

    def cleanup_workflow_state(self, workflow_id: str) -> None:
        """
        Clean up completed workflow from memory.

        Args:
            workflow_id: Workflow identifier
        """
        with self._lock:
            if workflow_id in self._states:
                del self._states[workflow_id]

        logger.info(
            "workflow_state_cleaned_up",
            workflow_id=workflow_id,
        )

    def _persist_state(self, state: WorkflowState) -> None:
        """
        Persist state to persistence layer if configured.

        Args:
            state: WorkflowState to persist
        """
        if self._persistence:
            self._persistence.save_workflow_state(state.workflow_id, state.to_dict())

    def get_active_workflows(self) -> Dict[str, str]:
        """
        Get summary of active workflows in memory.

        Returns:
            Dictionary mapping workflow_id to status
        """
        with self._lock:
            return {
                workflow_id: state.status for workflow_id, state in self._states.items()
            }

    def reset(self) -> None:
        """Reset state manager, clearing all states."""
        with self._lock:
            self._states.clear()

        logger.info("state_manager_reset")
