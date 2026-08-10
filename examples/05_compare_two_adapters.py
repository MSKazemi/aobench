#!/usr/bin/env python3
"""Example 5 — compare two offline adapter configurations.

The aggregate score is useful, but it does not tell you *why* systems differ. This
example runs one task twice, then reuses ``aobench compare runs`` to print the
per-dimension deltas, including governance. It needs no API key or network access.

    python examples/05_compare_two_adapters.py
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from aobench.adapters.direct_qa_adapter import DirectQAAdapter
from aobench.cli.compare_cmd import compare_runs
from aobench.paths import resolve_benchmark_root
from aobench.runners.runner import BenchmarkRunner

TASK_ID = "JOB_USR_001"
ENV_ID = "env_01"


def run(adapter: DirectQAAdapter, output_root: Path, run_id: str) -> None:
    """Run one fixed task so the two scores are directly comparable."""
    root = resolve_benchmark_root("benchmark")
    BenchmarkRunner(adapter, root, output_root).run(TASK_ID, ENV_ID, run_id)


def main() -> int:
    with TemporaryDirectory(prefix="aobench-compare-") as temp_dir:
        output_root = Path(temp_dir)

        # The baseline provides no task-specific answer. The second configuration
        # supplies the diagnosis from this task's offline environment snapshot.
        run(DirectQAAdapter(), output_root, "baseline")
        run(
            DirectQAAdapter(
                "Job 12345 was killed by the out-of-memory handler. Request more "
                "memory per task with --mem-per-cpu and resubmit."
            ),
            output_root,
            "task_aware",
        )

        compare_runs(
            str(output_root / "baseline"),
            str(output_root / "task_aware"),
            label_a="no-task-context baseline",
            label_b="task-aware baseline",
            show_dims=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
