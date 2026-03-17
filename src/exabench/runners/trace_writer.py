"""TraceWriter — persists trace and result artifacts to disk."""

from __future__ import annotations

import json
from pathlib import Path

from exabench.schemas.result import BenchmarkResult
from exabench.schemas.trace import Trace


class TraceWriter:
    def __init__(self, run_dir: str | Path) -> None:
        self._run_dir = Path(run_dir)

    def write_trace(self, trace: Trace) -> Path:
        out = self._run_dir / "traces" / f"{trace.task_id}_trace.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(trace.model_dump_json(indent=2))
        return out

    def write_result(self, result: BenchmarkResult) -> Path:
        out = self._run_dir / "results" / f"{result.task_id}_result.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(result.model_dump_json(indent=2))
        return out
