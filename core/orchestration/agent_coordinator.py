"""Coordinates communication and state sharing between agents."""

from typing import Any, Dict, List, Optional
from datetime import datetime

import structlog

logger = structlog.get_logger(__name__)


class AgentCoordinator:
    """Manages communication, state sharing, and coordination between agents."""

    def __init__(self):
        """Initialize agent coordinator."""
        self.agent_states = {}
        self.shared_context = {}
        self.message_queue = []
        self.coordination_log = []

    def register_agent(self, agent_name: str, agent_id: str) -> None:
        """
        Register an agent with the coordinator.

        Args:
            agent_name: Name of the agent
            agent_id: Unique identifier for the agent instance
        """
        self.agent_states[agent_id] = {
            "agent_name": agent_name,
            "status": "idle",
            "last_activity": datetime.utcnow().isoformat(),
            "execution_count": 0,
        }

        logger.info(
            "agent_registered",
            agent_name=agent_name,
            agent_id=agent_id,
        )

    def update_agent_state(
        self, agent_id: str, status: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update agent state.

        Args:
            agent_id: Agent identifier
            status: New status (idle, executing, completed, failed)
            metadata: Optional metadata about the agent state
        """
        if agent_id not in self.agent_states:
            return

        self.agent_states[agent_id]["status"] = status
        self.agent_states[agent_id]["last_activity"] = datetime.utcnow().isoformat()

        if metadata:
            self.agent_states[agent_id].update(metadata)

    def share_context(
        self, context_key: str, context_value: Any, source_agent: Optional[str] = None
    ) -> None:
        """
        Share context between agents.

        Args:
            context_key: Key for the shared context
            context_value: Value to share
            source_agent: Optional source agent identifier
        """
        self.shared_context[context_key] = {
            "value": context_value,
            "source": source_agent,
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.info(
            "context_shared",
            context_key=context_key,
            source_agent=source_agent,
        )

    def get_shared_context(self, context_key: str) -> Any:
        """
        Retrieve shared context.

        Args:
            context_key: Key for the context

        Returns:
            Context value or None if not found
        """
        if context_key in self.shared_context:
            return self.shared_context[context_key]["value"]
        return None

    def pass_data_between_agents(
        self,
        source_agent: str,
        target_agent: str,
        data: Dict[str, Any],
        stage_name: str,
    ) -> None:
        """
        Pass data from one agent to the next in the pipeline.

        Args:
            source_agent: Source agent name
            target_agent: Target agent name
            data: Data to pass
            stage_name: Pipeline stage name
        """
        message = {
            "source": source_agent,
            "target": target_agent,
            "data": data,
            "stage": stage_name,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self.message_queue.append(message)
        self.coordination_log.append(message)

        logger.info(
            "data_passed",
            from_agent=source_agent,
            to_agent=target_agent,
            stage=stage_name,
        )

    def get_coordination_status(self) -> Dict[str, Any]:
        """
        Get overall coordination status.

        Returns:
            Coordination status information
        """
        return {
            "registered_agents": len(self.agent_states),
            "agent_states": self.agent_states,
            "shared_context_keys": list(self.shared_context.keys()),
            "pending_messages": len(self.message_queue),
            "total_coordination_events": len(self.coordination_log),
        }

    def reset(self) -> None:
        """Reset coordinator state."""
        self.agent_states = {}
        self.shared_context = {}
        self.message_queue = []

        logger.info("coordinator_reset")
