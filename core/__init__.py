"""Core agentic AI automation package."""

__version__ = "1.0.0"
__author__ = "Enterprise AI Team"

from core.agents.base_agent import BaseAgent
from core.orchestration.workflow_orchestrator import WorkflowOrchestrator
from core.state.state_manager import StateManager

__all__ = [
    "BaseAgent",
    "WorkflowOrchestrator",
    "StateManager",
]
