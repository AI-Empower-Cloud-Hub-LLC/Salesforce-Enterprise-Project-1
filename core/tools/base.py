from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import structlog

from core.integrations.base import IntegrationResult, OperationStatus

logger = structlog.get_logger(__name__)


@dataclass
class ToolMetadata:
    name: str
    description: str
    category: str
    version: str = "1.0.0"
    required_inputs: Dict[str, str] = field(default_factory=dict)
    optional_inputs: Dict[str, str] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    auth_required: bool = False
    rate_limit_per_minute: Optional[int] = None


class BaseTool(ABC):
    """Abstract base class for all tools."""

    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """Return tool metadata."""
        pass

    @abstractmethod
    async def execute(self, inputs: Dict[str, Any]) -> IntegrationResult:
        """Execute the tool with given inputs.

        Returns IntegrationResult with status, data, and errors.
        """
        pass

    async def validate(self, inputs: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate inputs before execution.

        Returns (is_valid, error_messages)
        """
        errors = []
        meta = self.metadata

        for key, input_type in meta.required_inputs.items():
            if key not in inputs:
                errors.append(f"Missing required input: {key}")
            elif not self._validate_type(inputs[key], input_type):
                errors.append(f"Invalid type for {key}: expected {input_type}, got {type(inputs[key]).__name__}")

        return len(errors) == 0, errors

    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type string."""
        type_map = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "dict": dict,
            "list": list,
        }

        if expected_type not in type_map:
            return True

        return isinstance(value, type_map[expected_type])

    async def get_metadata(self) -> Dict[str, Any]:
        """Return tool metadata as dictionary."""
        meta = self.metadata
        return {
            "name": meta.name,
            "description": meta.description,
            "category": meta.category,
            "version": meta.version,
            "required_inputs": meta.required_inputs,
            "optional_inputs": meta.optional_inputs,
            "output_schema": meta.output_schema,
            "auth_required": meta.auth_required,
            "rate_limit_per_minute": meta.rate_limit_per_minute,
        }
