"""Base agent class for all specialized agents."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional, List
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all agents in the orchestration framework."""

    def __init__(
        self,
        name: str,
        role: str,
        tools: Optional[List[str]] = None,
        max_retries: int = 3,
        timeout: int = 60,
    ):
        """
        Initialize base agent.

        Args:
            name: Unique agent identifier
            role: Agent role/responsibility
            tools: List of tool names available to agent
            max_retries: Maximum retry attempts on failure
            timeout: Execution timeout in seconds
        """
        self.agent_id = str(uuid4())
        self.name = name
        self.role = role
        self.tools = tools or []
        self.max_retries = max_retries
        self.timeout = timeout
        self.execution_history = []

    async def execute(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute agent task with context.

        Args:
            task: Task configuration and parameters
            context: Workflow execution context

        Returns:
            Execution result with status and output
        """
        execution_id = str(uuid4())
        start_time = datetime.utcnow()

        try:
            logger.info(
                "agent_execution_started",
                agent_name=self.name,
                agent_role=self.role,
                execution_id=execution_id,
                task_id=task.get("id"),
            )

            result = await self._execute_task(task, context)

            end_time = datetime.utcnow()
            execution_record = {
                "execution_id": execution_id,
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "status": "success",
                "result": result,
                "started_at": start_time.isoformat(),
                "completed_at": end_time.isoformat(),
                "duration_ms": int((end_time - start_time).total_seconds() * 1000),
            }

            self.execution_history.append(execution_record)

            logger.info(
                "agent_execution_completed",
                agent_name=self.name,
                execution_id=execution_id,
                status="success",
                duration_ms=execution_record["duration_ms"],
            )

            return execution_record

        except Exception as e:
            end_time = datetime.utcnow()
            logger.error(
                "agent_execution_failed",
                agent_name=self.name,
                execution_id=execution_id,
                error=str(e),
                error_type=type(e).__name__,
            )

            execution_record = {
                "execution_id": execution_id,
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "status": "failed",
                "error": str(e),
                "error_type": type(e).__name__,
                "started_at": start_time.isoformat(),
                "completed_at": end_time.isoformat(),
                "duration_ms": int((end_time - start_time).total_seconds() * 1000),
            }

            self.execution_history.append(execution_record)
            raise

    @abstractmethod
    async def _execute_task(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Implement agent-specific task execution.

        Must be overridden by subclasses.

        Args:
            task: Task configuration
            context: Workflow context

        Returns:
            Task execution result
        """
        pass

    def get_execution_history(self) -> List[Dict[str, Any]]:
        """Get agent execution history."""
        return self.execution_history

    def reset_history(self) -> None:
        """Clear execution history."""
        self.execution_history = []

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.agent_id}, name={self.name}, role={self.role})"
