"""Base class for all ExaBench mock HPC tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class ToolResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    tool_name: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    permission_denied: bool = False


class BaseTool(ABC):
    """Abstract base for all mock tools. Each tool is backed by an environment bundle."""

    name: str  # Must be set as a class attribute by subclasses

    def __init__(self, env_root: str) -> None:
        self._env_root = env_root

    @abstractmethod
    def call(self, method: str, **kwargs: Any) -> ToolResult:
        """Dispatch a method call on this tool."""
        ...

    def _error(self, msg: str) -> ToolResult:
        return ToolResult(tool_name=self.name, success=False, error=msg)

    def _ok(self, data: Any) -> ToolResult:
        return ToolResult(tool_name=self.name, success=True, data=data)

    def _permission_denied(self, msg: str = "Permission denied") -> ToolResult:
        return ToolResult(tool_name=self.name, success=False,
                          error=msg, permission_denied=True)
