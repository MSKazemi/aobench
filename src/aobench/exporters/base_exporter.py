"""BaseExporter — abstract contract for post-run observability exporters."""

from __future__ import annotations

from abc import ABC, abstractmethod

from aobench.schemas.result import BenchmarkResult
from aobench.schemas.task import TaskSpec
from aobench.schemas.trace import Trace


class BaseExporter(ABC):
    """Export a completed task run to an external observability backend.

    Implement :meth:`export` to push one trace + result to your backend.
    Optionally override :meth:`flush` if the backend uses batched writes.
    """

    @abstractmethod
    def export(self, trace: Trace, result: BenchmarkResult, task: TaskSpec) -> None:
        """Push one completed task run to the observability backend.

        Called by :class:`~aobench.runners.runner.BenchmarkRunner` after both
        the trace and the result have been written to disk.

        Args:
            trace:  Full execution trace produced by the adapter.
            result: Scored benchmark result.
            task:   Original task specification.
        """

    def flush(self) -> None:
        """Flush any buffered data to the backend.

        The default implementation is a no-op.  Override when the backend
        client buffers writes internally (e.g. Langfuse SDK).
        """
