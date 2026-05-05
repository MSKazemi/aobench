"""Tool registry — manages available tools and enforces role-based access."""

from __future__ import annotations

from typing import Any, Optional

from aobench.tools.base import BaseTool, ToolResult


class ToolRegistry:
    """Holds the set of tools available for a given task execution context."""

    def __init__(
        self,
        tools: list[BaseTool],
        allowed_tool_names: Optional[list[str]] = None,
        role: Optional[str] = None,
    ) -> None:
        self._tools: dict[str, BaseTool] = {t.name: t for t in tools}
        self._allowed = set(allowed_tool_names) if allowed_tool_names else set(self._tools)
        self._role = role

    def call(self, tool_name: str, method: str, **kwargs: Any) -> ToolResult:
        if tool_name not in self._allowed:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool '{tool_name}' is not in the allowed tool set for this task.",
                permission_denied=True,
            )
        if tool_name not in self._tools:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool '{tool_name}' is not registered.",
            )
        return self._tools[tool_name].call(method, **kwargs)

    @property
    def available_tool_names(self) -> list[str]:
        return sorted(self._allowed & set(self._tools))
