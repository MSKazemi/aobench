"""exabench validate — validate benchmark data files."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

validate_app = typer.Typer(help="Validate benchmark data.")


@validate_app.command("benchmark")
def validate_benchmark(
    benchmark_root: Annotated[str, typer.Option("--benchmark")] = "benchmark",
) -> None:
    """Validate all task specs and environment bundles."""
    from exabench.loaders.registry import BenchmarkRegistry

    root = Path(benchmark_root)
    typer.echo(f"Validating benchmark at {root.resolve()}")
    registry = BenchmarkRegistry(root)
    registry.load_all()
    typer.echo(f"  Tasks loaded:        {len(registry.task_ids)}")
    typer.echo(f"  Environments loaded: {len(registry.environment_ids)}")
    typer.echo("Validation passed.")


@validate_app.command("tasks")
def validate_tasks_cmd(
    task_file: Annotated[str, typer.Option("--task-file", help="Task corpus JSON")] = "benchmark/tasks/task_set_v1.json",
    snapshot_dir: Annotated[str, typer.Option("--snapshot-dir", help="Environments directory")] = "benchmark/environments/",
    catalog: Annotated[str, typer.Option("--catalog", help="Tool catalog YAML")] = "benchmark/configs/hpc_tool_catalog.yaml",
    checks: Annotated[str, typer.Option("--checks", help="Comma-separated checks, e.g. t1,t3 (default: all)")] = "all",
    output: Annotated[str, typer.Option("--output", "-o", help="Output report path (default: stdout)")] = "-",
    fmt: Annotated[str, typer.Option("--format", help="Output format: json | text | csv")] = "json",
    strict: Annotated[bool, typer.Option("--strict/--no-strict", help="Treat WARN as FAIL")] = False,
    summary: Annotated[bool, typer.Option("--summary/--no-summary", help="Print T1–T10 pass/fail summary table")] = True,
) -> None:
    """Run T1–T10 validity checks and print a pass/fail summary.

    Wraps validate_tasks.py and adds a human-readable T1–T10 summary table.
    """
    import sys
    from exabench.cli.validate_tasks import main as _validate_main

    argv: list[str] = [
        "--task-file", task_file,
        "--snapshot-dir", snapshot_dir,
        "--catalog", catalog,
        "--checks", checks,
        "--format", fmt,
    ]
    if output and output != "-":
        argv += ["--output", output]
    if strict:
        argv.append("--strict")

    rc = _validate_main(argv)

    if summary:
        _print_t1_t10_summary(task_file, snapshot_dir, catalog, checks, strict)

    raise typer.Exit(rc)


def _print_t1_t10_summary(
    task_file: str,
    snapshot_dir: str,
    catalog: str,
    checks: str,
    strict: bool,
) -> None:
    """Print a compact T1–T10 pass/fail summary table to stdout."""
    import sys
    from exabench.tasks.task_loader import load_hpc_task_set
    from exabench.cli.validators.base import aggregate_overall
    from exabench.cli.validators.t1_tool_versions import check_tool_version_pinning
    from exabench.cli.validators.t2_tool_setup import check_tool_setup
    from exabench.cli.validators.t3_oracle_solvability import check_oracle_solvability
    from exabench.cli.validators.t4_residual_state import check_residual_state_policy
    from exabench.cli.validators.t5_gt_isolation import check_ground_truth_isolation
    from exabench.cli.validators.t6_env_freeze import check_environment_freeze
    from exabench.cli.validators.t7_gt_correctness import check_ground_truth_correctness
    from exabench.cli.validators.t8_ambiguity import check_task_ambiguity
    from exabench.cli.validators.t9_shortcuts import check_shortcut_prevention
    from exabench.cli.validators.base import CheckResult

    _ALL = ["t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9"]
    if checks.lower() == "all":
        enabled = _ALL
    else:
        enabled = [c.strip().lower() for c in checks.split(",")]

    task_file_path = Path(task_file)
    snapshot_dir_path = Path(snapshot_dir)
    catalog_path = Path(catalog)

    try:
        all_tasks = load_hpc_task_set(task_file_path)
    except Exception as exc:
        typer.echo(f"[summary] Could not load tasks: {exc}", err=True)
        return

    cat = None
    if any(c in enabled for c in ("t1", "t5")):
        try:
            from exabench.tools.catalog_loader import load_catalog
            cat = load_catalog(catalog_path if catalog_path.exists() else None)
        except Exception:
            pass

    t6_result = None
    if "t6" in enabled:
        t6_result = check_environment_freeze(snapshot_dir_path)

    rows = []
    for task in all_tasks:
        row: dict[str, str] = {"task_id": task.task_id}
        check_map: dict[str, CheckResult] = {}

        if "t1" in enabled:
            check_map["t1"] = check_tool_version_pinning(task, cat) if cat else CheckResult(status="SKIP", detail="")
        if "t2" in enabled:
            check_map["t2"] = check_tool_setup(task, snapshot_dir_path)
        if "t3" in enabled:
            check_map["t3"] = check_oracle_solvability(task, snapshot_dir_path)
        if "t4" in enabled:
            check_map["t4"] = check_residual_state_policy(task)
        if "t5" in enabled:
            check_map["t5"] = check_ground_truth_isolation(task, cat, snapshot_dir_path) if cat else CheckResult(status="SKIP", detail="")
        if "t6" in enabled and t6_result:
            check_map["t6"] = t6_result
        if "t7" in enabled:
            check_map["t7"] = check_ground_truth_correctness(task, snapshot_dir_path, judge=None)
        if "t8" in enabled:
            check_map["t8"] = check_task_ambiguity(task)
        if "t9" in enabled:
            check_map["t9"] = check_shortcut_prevention(task, all_tasks)

        overall = aggregate_overall(check_map, strict=strict)
        for k in _ALL:
            cr = check_map.get(k)
            row[k] = cr.status[0] if cr else "-"  # P/W/F/S
        row["overall"] = overall
        rows.append(row)

    # Print summary table
    col_w = 3
    header = f"{'task_id':<20}" + "".join(f"{c:>{col_w}}" for c in _ALL) + f"  {'overall'}"
    typer.echo("\nT1–T10 Validity Summary")
    typer.echo("=" * len(header))
    typer.echo(header)
    typer.echo("-" * len(header))
    pass_count = warn_count = fail_count = 0
    for row in rows:
        cells = "".join(f"{row.get(c, '-'):>{col_w}}" for c in _ALL)
        overall = row["overall"]
        if overall == "PASS":
            pass_count += 1
        elif overall == "WARN":
            warn_count += 1
        else:
            fail_count += 1
        typer.echo(f"{row['task_id']:<20}{cells}  {overall}")
    typer.echo("-" * len(header))
    typer.echo(f"TOTAL: {len(rows)}  PASS={pass_count}  WARN={warn_count}  FAIL={fail_count}")
    typer.echo("")
