"""Workflow state data model."""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum


class WorkflowStatus(Enum):
    """Workflow execution status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"
    HALTED = "halted"


class PipelineStageStatus(Enum):
    """Pipeline stage execution status."""

    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StageExecution:
    """Execution details for a pipeline stage."""

    stage_name: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    agent_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class WorkflowContext:
    """Context maintained throughout workflow execution."""

    workflow_id: str
    original_request: Dict[str, Any]
    timestamp: str
    status: str
    context: Dict[str, Any] = field(default_factory=dict)
    pipeline_state: Dict[str, Any] = field(default_factory=dict)
    classification: Optional[Dict[str, Any]] = None
    execution_plan: Optional[Dict[str, Any]] = None
    execution_results: Optional[Dict[str, Any]] = None
    validation_results: Optional[Dict[str, Any]] = None
    escalation_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "WorkflowContext":
        """Create from dictionary."""
        return WorkflowContext(**data)


@dataclass
class ExecutionTimeline:
    """Tracks execution timeline of workflow."""

    workflow_id: str
    started_at: str
    stages: List[StageExecution] = field(default_factory=list)
    completed_at: Optional[str] = None
    total_duration_seconds: Optional[float] = None

    def add_stage(self, stage: StageExecution) -> None:
        """Add stage execution to timeline."""
        self.stages.append(stage)

    def complete(self, duration_seconds: float) -> None:
        """Mark timeline as complete."""
        self.completed_at = datetime.utcnow().isoformat()
        self.total_duration_seconds = duration_seconds

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "workflow_id": self.workflow_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_duration_seconds": self.total_duration_seconds,
            "stages": [s.to_dict() for s in self.stages],
        }


class WorkflowState:
    """Comprehensive workflow state tracking."""

    def __init__(self, workflow_id: str, request: Dict[str, Any]):
        """
        Initialize workflow state.

        Args:
            workflow_id: Unique workflow identifier
            request: Original workflow request
        """
        self.workflow_id = workflow_id
        self.request = request
        self.status = WorkflowStatus.PENDING.value
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None

        self.context = WorkflowContext(
            workflow_id=workflow_id,
            original_request=request,
            timestamp=self.created_at.isoformat(),
            status=self.status,
        )

        self.timeline = ExecutionTimeline(
            workflow_id=workflow_id,
            started_at=self.created_at.isoformat(),
        )

        self.audit_trail: List[Dict[str, Any]] = []

    def update_status(self, status: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Update workflow status.

        Args:
            status: New status
            details: Optional additional details
        """
        self.status = status
        self.context.status = status
        self.updated_at = datetime.utcnow()

        self._log_audit(
            action="status_update",
            status=status,
            details=details,
        )

    def add_stage_execution(self, stage: StageExecution) -> None:
        """
        Add stage execution to timeline.

        Args:
            stage: Stage execution details
        """
        self.timeline.add_stage(stage)
        self.updated_at = datetime.utcnow()

        self._log_audit(
            action="stage_executed",
            stage=stage.stage_name,
            status=stage.status,
        )

    def set_context(self, key: str, value: Any) -> None:
        """
        Set context value.

        Args:
            key: Context key
            value: Context value
        """
        setattr(self.context, key, value)
        self.updated_at = datetime.utcnow()

    def get_context(self, key: str, default: Any = None) -> Any:
        """
        Get context value.

        Args:
            key: Context key
            default: Default value if not found

        Returns:
            Context value or default
        """
        return getattr(self.context, key, default)

    def mark_completed(self) -> None:
        """Mark workflow as completed."""
        self.completed_at = datetime.utcnow()
        duration = (self.completed_at - self.created_at).total_seconds()
        self.timeline.complete(duration)
        self.update_status(WorkflowStatus.COMPLETED.value)

    def mark_failed(self, error: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Mark workflow as failed.

        Args:
            error: Error message
            details: Optional error details
        """
        self.context.error = error
        self.context.error_details = details
        self.update_status(WorkflowStatus.FAILED.value, {"error": error})

    def mark_escalated(self, escalation_result: Dict[str, Any]) -> None:
        """
        Mark workflow as escalated.

        Args:
            escalation_result: Escalation details
        """
        self.context.escalation_result = escalation_result
        self.update_status(WorkflowStatus.ESCALATED.value)

    def _log_audit(self, action: str, **details: Any) -> None:
        """
        Log audit trail entry.

        Args:
            action: Action name
            details: Action details
        """
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "details": details,
        }
        self.audit_trail.append(audit_entry)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert state to dictionary.

        Returns:
            State as dictionary
        """
        return {
            "workflow_id": self.workflow_id,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "context": self.context.to_dict(),
            "timeline": self.timeline.to_dict(),
            "audit_trail": self.audit_trail,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "WorkflowState":
        """
        Create state from dictionary.

        Args:
            data: State dictionary

        Returns:
            WorkflowState instance
        """
        state = WorkflowState(
            workflow_id=data["workflow_id"],
            request=data["context"]["original_request"],
        )

        state.status = data.get("status", WorkflowStatus.PENDING.value)
        state.created_at = datetime.fromisoformat(data["created_at"])
        state.updated_at = datetime.fromisoformat(data["updated_at"])

        if data.get("completed_at"):
            state.completed_at = datetime.fromisoformat(data["completed_at"])

        state.context = WorkflowContext.from_dict(data["context"])
        state.audit_trail = data.get("audit_trail", [])

        return state
