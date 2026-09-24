"""AOBench service façade — transport-agnostic run/score/report engine access.

Every access surface (CLI, REST, MCP, A2A) calls this shared façade, so scores are
identical across transports.
"""

from __future__ import annotations

from aobench.service.errors import (
    AdapterError,
    AOBenchServiceError,
    EnvNotFound,
    RoleForbidden,
    RunNotFound,
    SplitLockedError,
    TaskBlocked,
    TaskNotFound,
)
from aobench.service.facade import BenchmarkService, resolve_adapter
from aobench.service.jobs import (
    InMemoryJobRegistry,
    JobRecord,
    JobResult,
    JobState,
    run_job,
)
from aobench.service.models import (
    CompareResult,
    DatasetInfo,
    EnvSummary,
    Fingerprint,
    ReportModel,
    RobustnessResult,
    RunHandle,
    RunRecord,
    TaskSummary,
)

__all__ = [
    "BenchmarkService",
    "resolve_adapter",
    "AOBenchServiceError",
    "TaskNotFound",
    "TaskBlocked",
    "EnvNotFound",
    "AdapterError",
    "SplitLockedError",
    "RoleForbidden",
    "RunNotFound",
    "RunHandle",
    "RunRecord",
    "TaskSummary",
    "EnvSummary",
    "CompareResult",
    "RobustnessResult",
    "Fingerprint",
    "ReportModel",
    "DatasetInfo",
    "InMemoryJobRegistry",
    "JobRecord",
    "JobResult",
    "JobState",
    "run_job",
]
