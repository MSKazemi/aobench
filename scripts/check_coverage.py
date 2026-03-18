#!/usr/bin/env python3
"""Print the task coverage matrix: role × category, plus readiness summary."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running as a script without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from exabench.loaders.task_loader import load_tasks_from_dir
from exabench.schemas.task import TaskSpec

BENCHMARK_ROOT = Path(__file__).parent.parent / "benchmark"
ROLES   = ["scientific_user", "sysadmin", "facility_admin", "researcher", "system_designer"]
QCATS   = ["JOB", "PERF", "DATA", "MON", "ENERGY", "SEC", "FAC", "ARCH", "AIOPS", "DOCS"]
DIFFS   = ["easy", "medium", "hard", "adversarial"]
READINESS = ["ready", "partial", "blocked"]


def _bar(n: int, total: int, width: int = 20) -> str:
    filled = round(width * n / total) if total else 0
    return "█" * filled + "░" * (width - filled)


def main() -> None:
    tasks: list[TaskSpec] = load_tasks_from_dir(BENCHMARK_ROOT / "tasks" / "specs")
    total = len(tasks)

    if total == 0:
        print("No tasks found in benchmark/tasks/specs/")
        return

    # ── Role × Category matrix ────────────────────────────────────────────────
    print(f"\n{'─'*56}")
    print(f"  ExaBench Coverage Matrix   ({total} tasks total)")
    print(f"{'─'*56}")

    # Header
    col_w = 16
    print(f"\n  {'Role / QCAT':<22}", end="")
    for q in QCATS:
        print(f"{q:>{col_w}}", end="")
    print(f"{'TOTAL':>{col_w}}")
    print(f"  {'─'*22}", end="")
    print("─" * (col_w * (len(QCATS) + 1)))

    role_totals = {r: 0 for r in ROLES}
    qcat_totals = {q: 0 for q in QCATS}

    for role in ROLES:
        role_tasks = [t for t in tasks if t.role == role]
        label = role.replace("_", " ")
        print(f"  {label:<22}", end="")
        for q in QCATS:
            n = sum(1 for t in role_tasks if t.qcat == q)
            qcat_totals[q] += n
            role_totals[role] += n
            print(f"{n:>{col_w}}", end="")
        print(f"{len(role_tasks):>{col_w}}")

    # QCAT totals row
    print(f"  {'─'*22}", end="")
    print("─" * (col_w * (len(QCATS) + 1)))
    print(f"  {'TOTAL':<22}", end="")
    for q in QCATS:
        print(f"{qcat_totals[q]:>{col_w}}", end="")
    print(f"{total:>{col_w}}")

    # ── Difficulty breakdown ───────────────────────────────────────────────────
    print(f"\n  {'─'*40}")
    print(f"  Difficulty breakdown")
    print(f"  {'─'*40}")
    for d in DIFFS:
        n = sum(1 for t in tasks if t.difficulty == d)
        if n > 0:
            print(f"  {d:<14} {n:>3}  {_bar(n, total)}")

    # ── Scoring readiness ─────────────────────────────────────────────────────
    print(f"\n  {'─'*40}")
    print(f"  Scoring readiness")
    print(f"  {'─'*40}")
    for r in READINESS:
        n = sum(1 for t in tasks if t.scoring_readiness == r)
        if n > 0:
            print(f"  {r:<14} {n:>3}  {_bar(n, total)}")

    # ── Benchmark split ───────────────────────────────────────────────────────
    splits = {}
    for t in tasks:
        key = t.benchmark_split or "unassigned"
        splits[key] = splits.get(key, 0) + 1
    if splits:
        print(f"\n  {'─'*40}")
        print(f"  Benchmark splits")
        print(f"  {'─'*40}")
        for s, n in sorted(splits.items()):
            print(f"  {s:<14} {n:>3}  {_bar(n, total)}")

    # ── v0.1 target progress ──────────────────────────────────────────────────
    TARGET = 30
    print(f"\n  {'─'*40}")
    pct = round(100 * total / TARGET)
    print(f"  v0.1 target: {total}/{TARGET} tasks  [{pct}%]  {_bar(total, TARGET)}")
    print(f"{'─'*56}\n")


if __name__ == "__main__":
    main()
