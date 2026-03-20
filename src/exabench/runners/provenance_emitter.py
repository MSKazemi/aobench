"""Optional Flowcept provenance emitter.

Enabled by setting EXABENCH_FLOWCEPT=1 in the environment.
Requires: pip install flowcept  (only at runtime, not at import time)

When enabled, every tool call and reasoning step is emitted as a
Flowcept provenance event with W3C PROV-aligned fields.

Event format (JSON-lines, one event per line):
    {"activity_id": "abc123_step_007", "workflow_id": "abc123",
     "campaign_id": "task_job_001__sysadmin__gpt-4o",
     "type": "tool_call", "started_at": "2026-03-19T10:00:07Z",
     "status": "FINISHED", "used": ["slurm/slurm_state.json"],
     "generated": [], "exabench:task_id": "task_job_001",
     "exabench:role": "sysadmin",
     "exabench:tool_name": "slurm", "exabench:method": "query_jobs"}

Sources:
  Skluzacek et al. (2023-2025). Flowcept: HPC Workflow Provenance Agent.
  ORNL. github.com/ORNL/flowcept. Presented at SC'25.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from exabench.schemas.trace import Trace, TraceStep


class ProvenanceEmitter:
    """Emits ExaBench trace steps as Flowcept provenance events.

    Usage::

        emitter = ProvenanceEmitter.from_env()  # None if EXABENCH_FLOWCEPT not set
        if emitter:
            emitter.emit_step(trace, step)
            emitter.emit_run_complete(trace)
    """

    def __init__(self, output_dir: str | Path) -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._events_file = self._output_dir / "events.jsonl"

    @classmethod
    def from_env(cls, run_dir: Optional[str | Path] = None) -> Optional["ProvenanceEmitter"]:
        """Return an emitter if EXABENCH_FLOWCEPT=1, else None.

        Args:
            run_dir: Base run directory. If not provided, uses
                     EXABENCH_FLOWCEPT_DIR env var.
        """
        if os.environ.get("EXABENCH_FLOWCEPT") != "1":
            return None
        if run_dir is not None:
            output_dir = Path(run_dir) / "provenance"
        else:
            flowcept_dir = os.environ.get("EXABENCH_FLOWCEPT_DIR")
            if flowcept_dir:
                output_dir = Path(flowcept_dir)
            else:
                return None
        return cls(output_dir=output_dir)

    def emit_step(self, trace: Trace, step: TraceStep) -> None:
        """Emit one Flowcept provenance event for a TraceStep."""
        span_id = step.span_id or f"{trace.trace_id}_step_{step.step_id:03d}"
        event: dict = {
            "activity_id": span_id,
            "workflow_id": trace.trace_id,
            "campaign_id": trace.campaign_id,
            "type": step.step_type,
            "started_at": step.timestamp.isoformat() if step.timestamp else None,
            "status": "FAILED" if (step.observation and step.observation.error) else "FINISHED",
            "used": step.tool_call.accessed_artifacts if step.tool_call else [],
            "generated": step.observation.generated_artifacts if step.observation else [],
            # ExaBench-specific extensions
            "exabench:task_id": trace.task_id,
            "exabench:role": trace.role,
            "exabench:environment_id": trace.environment_id,
            "exabench:tool_name": step.tool_call.tool_name if step.tool_call else None,
            "exabench:method": step.tool_call.method if step.tool_call else None,
        }
        self._write_event(event)

    def emit_run_complete(self, trace: Trace, score: Optional[float] = None) -> None:
        """Emit a run-completion provenance event with optional score."""
        event: dict = {
            "activity_id": f"{trace.trace_id}_complete",
            "workflow_id": trace.trace_id,
            "campaign_id": trace.campaign_id,
            "type": "run_complete",
            "started_at": trace.start_time.isoformat() if trace.start_time else None,
            "ended_at": trace.end_time.isoformat() if trace.end_time else None,
            "status": "FAILED" if trace.hard_fail else "FINISHED",
            "used": [],
            "generated": [],
            "exabench:task_id": trace.task_id,
            "exabench:model_name": trace.model_name,
            "exabench:score": score,
            "exabench:total_tokens": trace.total_tokens,
        }
        self._write_event(event)

    def _write_event(self, event: dict) -> None:
        """Append event as one JSON line to the provenance log."""
        with self._events_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, default=str) + "\n")
