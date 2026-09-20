#!/usr/bin/env python3
"""Example 4 — turn an AOBench run into a CI pass/fail gate.

Usage::

    aobench run all --adapter my_agent --split dev --qcat JOB
    python examples/04_ci_gate.py data/runs/<run_id> --min-score 0.62 --max-hard-fails 0

Exit code 0 passes the build, 1 fails it.

**Hard fails are gated separately and at zero.** An RBAC violation is a different class
of event from "slightly worse at diagnosis", and averaging it into one number hides
exactly the thing you most want CI to catch.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def collect_results(run_dir: Path) -> list[dict[str, Any]]:
    """Return one dict per scored task.

    Prefers ``run_summary.json`` when the run generated reports, and falls back to the
    per-task files under ``results/`` otherwise — ``aobench run`` writes those
    unconditionally, so the gate works whether or not reports were requested.
    """
    summaries = sorted(run_dir.rglob("run_summary.json"))
    if summaries:
        summary = json.loads(summaries[0].read_text(encoding="utf-8"))
        results = summary.get("results") or summary.get("task_results")
        if results:
            return [r for r in results if isinstance(r, dict)]

    per_task = sorted(run_dir.rglob("results/*_result.json"))
    if per_task:
        return [json.loads(p.read_text(encoding="utf-8")) for p in per_task]

    sys.exit(
        f"No results found under {run_dir}.\n"
        "Did the run complete? Expected either run_summary.json or results/*_result.json.\n"
        "Check `aobench run all --output data/runs`."
    )


def extract(results: list[dict[str, Any]]) -> tuple[float, int, int]:
    """Return ``(mean aggregate score, hard-fail count, task count)``.

    Deliberately tolerant of shape differences across AOBench versions: a CI gate that
    breaks on a schema tweak gets disabled, and a disabled gate protects nothing.
    """
    scores = [
        float(r["aggregate_score"])
        for r in results
        if r.get("aggregate_score") is not None
    ]
    hard_fails = sum(1 for r in results if r.get("hard_fail"))
    mean = sum(scores) / len(scores) if scores else 0.0
    return mean, hard_fails, len(results)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path, help="directory written by `aobench run`")
    parser.add_argument("--min-score", type=float, default=0.0, help="fail below this")
    parser.add_argument(
        "--max-hard-fails",
        type=int,
        default=0,
        help="fail above this many RBAC hard fails (default 0 — do not raise it)",
    )
    args = parser.parse_args()

    score, hard_fails, tasks = extract(collect_results(args.run_dir))

    print(f"tasks       : {tasks}")
    print(f"aggregate   : {score:.4f}   (threshold {args.min_score:.4f})")
    print(f"hard fails  : {hard_fails}   (threshold {args.max_hard_fails})")

    failures = []
    if hard_fails > args.max_hard_fails:
        failures.append(
            f"{hard_fails} RBAC hard-fail(s) — an agent that oversteps its role is not "
            "acceptable at any score"
        )
    if score < args.min_score:
        failures.append(f"aggregate {score:.4f} below threshold {args.min_score:.4f}")

    if failures:
        print("\nFAIL")
        for failure in failures:
            print(f"  - {failure}")
        print(f"\nInspect the traces in {args.run_dir} to see what changed.")
        return 1

    print("\nPASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
