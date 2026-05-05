"""T1 checker: Tool version pinning.

Verifies that every tool listed in a task's ``required_tools`` field is
present in the tool catalog and that the catalog entry has an explicit
version string (i.e., not ``"unknown"`` or absent).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aobench.cli.validators.base import CheckResult

if TYPE_CHECKING:
    from aobench.schemas.task import HPCTaskSpec
    from aobench.tools.catalog_loader import ToolCatalog


def check_tool_version_pinning(
    task: "HPCTaskSpec",
    catalog: "ToolCatalog",
) -> CheckResult:
    """Check that every required tool is catalogued with a pinned version.

    Parameters
    ----------
    task:
        The HPC task spec to validate.
    catalog:
        Loaded ToolCatalog instance.

    Returns
    -------
    CheckResult
        PASS — all tools are present in the catalog.
        WARN — catalog version is unknown/missing (version field not set on catalog).
        FAIL — one or more required tools are absent from the catalog.
        SKIP — task declares no required tools.
    """
    required = task.required_tools
    if not required:
        return CheckResult(
            status="SKIP",
            detail="Task declares no required_tools; skipping version-pinning check.",
        )

    missing: list[str] = []
    for tool_name in required:
        try:
            catalog.get_tool(tool_name)
        except KeyError:
            missing.append(tool_name)

    if missing:
        return CheckResult(
            status="FAIL",
            detail=f"Required tool(s) not found in catalog: {missing}",
            fix_suggestion=(
                f"Add entries for {missing} to the tool catalog YAML, or remove them "
                "from the task's required_tools list."
            ),
        )

    # Check that the catalog itself has a proper version (not "unknown")
    if not catalog.version or catalog.version == "unknown":
        return CheckResult(
            status="WARN",
            detail=(
                f"All required tools ({required}) are in the catalog, but the catalog "
                "has no version string (version='unknown'). Tool versions are not pinned."
            ),
            fix_suggestion=(
                "Add a 'catalog_version' field to hpc_tool_catalog.yaml, e.g. "
                "'catalog_version: \"1.0.0\"'."
            ),
        )

    return CheckResult(
        status="PASS",
        detail=(
            f"All {len(required)} required tool(s) are present in catalog "
            f"version '{catalog.version}'."
        ),
    )
