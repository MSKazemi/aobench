"""Factory for building a role-bound ToolRegistry from a loaded environment bundle."""

from __future__ import annotations

from aobench.schemas.environment import EnvironmentBundle
from aobench.tools.docs_tool import MockDocsTool
from aobench.tools.facility_tool import MockFacilityTool
from aobench.tools.rbac_tool import MockRBACTool
from aobench.tools.registry import ToolRegistry
from aobench.tools.slurm_tool import MockSlurmTool
from aobench.tools.telemetry_tool import MockTelemetryTool


def build_tool_registry(
    bundle: EnvironmentBundle,
    role: str,
    requester_user: str = "alice",
    allowed_tools: list[str] | None = None,
) -> ToolRegistry:
    """Instantiate all mock tools from an environment bundle, bound to a role.

    Args:
        bundle: Loaded environment bundle (from load_environment()).
        role: The agent role for this task (e.g. "sysadmin", "scientific_user").
        requester_user: The username of the agent — used for own-job filtering.
        allowed_tools: Subset of tool names the task permits. None means all tools.

    Returns:
        A ToolRegistry with every tool initialised from the bundle snapshot.
    """
    root = bundle.root_path
    tools = [
        MockSlurmTool(root, role=role, requester_user=requester_user),
        MockTelemetryTool(root, role=role),
        MockRBACTool(root, role=role),
        MockDocsTool(root, role=role),
        MockFacilityTool(root, role=role),
    ]
    return ToolRegistry(tools, allowed_tool_names=allowed_tools, role=role)
