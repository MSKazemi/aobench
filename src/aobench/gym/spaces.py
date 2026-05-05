"""Lightweight space definitions mirroring the gymnasium API.

Used when gymnasium is not installed. When gymnasium is available,
AOBenchEnv can inherit from gymnasium.Env instead.
"""

from __future__ import annotations

from typing import Any


class Space:
    """Base space."""

    def contains(self, x: Any) -> bool:
        raise NotImplementedError

    def sample(self) -> Any:
        raise NotImplementedError


class TextSpace(Space):
    """Unbounded text (string) space."""

    def contains(self, x: Any) -> bool:
        return isinstance(x, str)

    def sample(self) -> str:
        return ""


class DiscreteSpace(Space):
    """Discrete integer space [0, n)."""

    def __init__(self, n: int) -> None:
        self.n = n

    def contains(self, x: Any) -> bool:
        return isinstance(x, int) and 0 <= x < self.n

    def sample(self) -> int:
        import random
        return random.randrange(self.n)


class DictSpace(Space):
    """Dictionary of named sub-spaces."""

    def __init__(self, spaces: dict[str, Space]) -> None:
        self.spaces = spaces

    def contains(self, x: Any) -> bool:
        if not isinstance(x, dict):
            return False
        return all(k in x and self.spaces[k].contains(x[k]) for k in self.spaces)

    def sample(self) -> dict[str, Any]:
        return {k: s.sample() for k, s in self.spaces.items()}


# Pre-built AOBench observation and action spaces (§11)
#
# Observation: {task_query, role, environment_id, last_tool_result, step_count}
# Action:      {type, tool_name, method, arguments, message, finish_answer}

OBSERVATION_SPACE = DictSpace({
    "task_query":       TextSpace(),
    "role":             TextSpace(),
    "environment_id":   TextSpace(),
    "last_tool_result": TextSpace(),
    "step_count":       DiscreteSpace(1000),
})

ACTION_SPACE = DictSpace({
    "type":          TextSpace(),   # "tool_call" | "message" | "finish"
    "tool_name":     TextSpace(),   # tool to invoke (for tool_call)
    "method":        TextSpace(),   # method name (for tool_call)
    "arguments":     TextSpace(),   # JSON-encoded arguments
    "message":       TextSpace(),   # free-text message
    "finish_answer": TextSpace(),   # final answer (for finish)
})
