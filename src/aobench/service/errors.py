"""Typed error hierarchy for the AOBench service façade (spec-0001, R7).

Transports (REST/MCP/A2A) map these to their own status codes; the CLI surfaces
them as messages. Keeping them here (not in the CLI) preserves the dependency
direction cli/server → service.
"""

from __future__ import annotations


class AOBenchServiceError(Exception):
    """Base class for all service-façade errors."""


class TaskNotFound(AOBenchServiceError):
    """The requested task_id has no spec under benchmark/tasks/specs/."""


class TaskBlocked(AOBenchServiceError):
    """The requested task cannot start a new run while scoring_readiness is blocked."""


class EnvNotFound(AOBenchServiceError):
    """The requested env_id has no bundle under benchmark/environments/."""


class AdapterError(AOBenchServiceError):
    """The adapter string could not be resolved or the adapter failed to run."""


class SplitLockedError(AOBenchServiceError):
    """The held-out 'test' split was requested without AOBENCH_UNLOCK_TEST=1."""


class RoleForbidden(AOBenchServiceError):
    """The caller's role is not permitted for the requested operation."""


class RunNotFound(AOBenchServiceError):
    """No run directory exists for the requested run_id."""
