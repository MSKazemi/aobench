"""Mock RBAC tool — checks permissions from environment policy file."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from exabench.tools.base import BaseTool, ToolResult


class MockRBACTool(BaseTool):
    name = "rbac"

    def __init__(self, env_root: str, role: str) -> None:
        super().__init__(env_root)
        self._role = role
        self._policy = self._load_policy()

    def _load_policy(self) -> dict[str, Any]:
        p = Path(self._env_root) / "policy" / "rbac_policy.yaml"
        if not p.exists():
            return {}
        with p.open() as f:
            return yaml.safe_load(f) or {}

    def call(self, method: str, **kwargs: Any) -> ToolResult:
        dispatch = {
            "check": self._check,
            "list_permissions": self._list_permissions,
        }
        if method not in dispatch:
            return self._error(f"Unknown rbac method: '{method}'")
        return dispatch[method](**kwargs)

    def _check(self, resource: str, action: str) -> ToolResult:
        role_policy = self._policy.get("roles", {}).get(self._role, {})
        permissions = role_policy.get("permissions", [])
        for perm in permissions:
            r = perm.get("resource", "")
            actions = perm.get("actions", [])
            if (r == resource or r == "*") and (action in actions or "*" in actions):
                return self._ok({"allowed": True, "role": self._role,
                                  "resource": resource, "action": action})
        return self._ok({"allowed": False, "role": self._role,
                          "resource": resource, "action": action})

    def _list_permissions(self) -> ToolResult:
        role_policy = self._policy.get("roles", {}).get(self._role, {})
        return self._ok(role_policy.get("permissions", []))
