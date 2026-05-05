"""aobench validate — validate benchmark data files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

validate_app = typer.Typer(help="Validate benchmark data.")


@validate_app.command("benchmark")
def validate_benchmark(
    benchmark_root: Annotated[str, typer.Option("--benchmark")] = "benchmark",
) -> None:
    """Validate all task specs and environment bundles."""
    from aobench.loaders.registry import BenchmarkRegistry

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
    from aobench.cli.validate_tasks import main as _validate_main

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
    from aobench.tasks.task_loader import load_hpc_task_set
    from aobench.cli.validators.base import aggregate_overall
    from aobench.cli.validators.t1_tool_versions import check_tool_version_pinning
    from aobench.cli.validators.t2_tool_setup import check_tool_setup
    from aobench.cli.validators.t3_oracle_solvability import check_oracle_solvability
    from aobench.cli.validators.t4_residual_state import check_residual_state_policy
    from aobench.cli.validators.t5_gt_isolation import check_ground_truth_isolation
    from aobench.cli.validators.t6_env_freeze import check_environment_freeze
    from aobench.cli.validators.t7_gt_correctness import check_ground_truth_correctness
    from aobench.cli.validators.t8_ambiguity import check_task_ambiguity
    from aobench.cli.validators.t9_shortcuts import check_shortcut_prevention
    from aobench.cli.validators.base import CheckResult

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
            from aobench.tools.catalog_loader import load_catalog
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


@validate_app.command("snapshots")
def validate_snapshots(
    environments_root: Annotated[str, typer.Option("--environments", help="Environments directory")] = "benchmark/environments",
    output_root: Annotated[str, typer.Option("--output", "-o", help="Output directory for fidelity reports")] = "data/fidelity",
) -> None:
    """Run F1–F7 fidelity validators on all env_*/ snapshot bundles.

    Writes per-environment Markdown reports and an aggregate REPORT.md and
    index.json to the output directory.
    """
    from aobench.environment.fidelity_report import FidelityReport

    env_root = Path(environments_root)
    out_root = Path(output_root)
    out_root.mkdir(parents=True, exist_ok=True)

    # Discover all env_* directories
    env_dirs = sorted(
        d for d in env_root.iterdir()
        if d.is_dir() and d.name.startswith("env_")
    ) if env_root.is_dir() else []

    if not env_dirs:
        typer.echo(f"No env_*/ directories found under {env_root}", err=True)
        raise typer.Exit(0)

    typer.echo(f"Scanning {len(env_dirs)} environment(s) in {env_root}")

    index: list[dict] = []
    aggregate_lines: list[str] = ["# AOBench Fidelity Report — All Environments", ""]

    pass_count = 0
    fail_count = 0

    for env_dir in env_dirs:
        env_id = env_dir.name
        report = FidelityReport(env_id=env_id, env_dir=env_dir)
        report.run_all()

        md_path = out_root / f"{env_id}.md"
        md_path.write_text(report.to_markdown(), encoding="utf-8")

        status = "PASS" if report.passed else "FAIL"
        if report.passed:
            pass_count += 1
        else:
            fail_count += 1

        index.append(
            {
                "env_id": env_id,
                "passed": report.passed,
                "generated_at": report.generated_at,
            }
        )

        # Short summary row for aggregate report
        aggregate_lines.append(f"## {env_id} — {status}")
        for r in report.results:
            sym = "✓" if r.passed else "✗"
            aggregate_lines.append(f"- {sym} {r.validator_id}: {r.message}")
        aggregate_lines.append("")

    aggregate_lines.append(f"**Summary: {pass_count} PASS / {fail_count} FAIL**")

    # Write aggregate report
    agg_path = out_root / "REPORT.md"
    agg_path.write_text("\n".join(aggregate_lines), encoding="utf-8")

    # Write index JSON
    index_path = out_root / "index.json"
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")

    # Print summary table to stdout
    typer.echo(f"\n{'env_id':<20} {'passed':>6}")
    typer.echo("-" * 28)
    for entry in index:
        symbol = "PASS" if entry["passed"] else "FAIL"
        typer.echo(f"{entry['env_id']:<20} {symbol:>6}")
    typer.echo("-" * 28)
    typer.echo(f"Total: {len(index)}  PASS={pass_count}  FAIL={fail_count}")
    typer.echo(f"\nReports written to: {out_root}")


# ---------------------------------------------------------------------------
# Authoring validation subcommand (E1.1)
# ---------------------------------------------------------------------------

def _oracle_check_task(task_path: pathlib.Path, env_dir: str) -> tuple[str, bool, str]:
    """Return (task_id, passed, reason) for a single task spec file."""
    with open(task_path) as f:
        d = json.load(f)
    task_id = d.get("task_id", task_path.stem)

    # Check environment directory exists
    env_id = d.get("environment_id", "")
    env_path = pathlib.Path(env_dir) / env_id
    if not env_path.exists():
        return task_id, False, f"env dir missing: {env_id}"

    # Check gold_answer is set
    eval_criteria = d.get("eval_criteria") or {}
    gold_answer = eval_criteria.get("gold_answer") if eval_criteria else None
    if not gold_answer:
        return task_id, False, "gold_answer missing"

    # Check evidence refs exist
    refs = d.get("gold_evidence_refs", [])
    for ref in refs:
        ref_path_str = ref.split("#")[0]  # strip fragment
        ref_path = env_path / ref_path_str
        if not ref_path.exists():
            return task_id, False, f"evidence missing: {ref_path_str}"

    return task_id, True, "ok"


@validate_app.command("authoring")
def validate_authoring(
    task_dir: str = typer.Option("benchmark/tasks/specs", help="Task spec directory"),
    env_dir: str = typer.Option("benchmark/environments", help="Environment directory"),
) -> None:
    """Run oracle_check and independence_check on all tasks."""
    import sys
    import math

    task_dir_path = pathlib.Path(task_dir)
    if not task_dir_path.exists():
        typer.echo(f"ERROR: task-dir does not exist: {task_dir_path}", err=True)
        raise typer.Exit(2)

    task_files = sorted(task_dir_path.glob("*.json"))
    if not task_files:
        typer.echo("No task spec files found.", err=True)
        raise typer.Exit(0)

    # --- Oracle check ---
    typer.echo("\nOracle Check")
    typer.echo("=" * 70)
    typer.echo(f"{'Task':30} {'Status':8} {'Reason'}")
    typer.echo("-" * 70)

    oracle_passed = oracle_failed = 0
    oracle_results: list[tuple[str, bool, str]] = []
    for f in task_files:
        result = _oracle_check_task(f, env_dir)
        oracle_results.append(result)
        task_id, ok, reason = result
        status = "PASS" if ok else "FAIL"
        typer.echo(f"{task_id:30} {status:8} {reason}")
        if ok:
            oracle_passed += 1
        else:
            oracle_failed += 1

    typer.echo(f"\nOracle: {oracle_passed} passed, {oracle_failed} failed")

    # --- Independence check ---
    _DIFFICULTY_TO_TIER = {"easy": 1, "medium": 2, "hard": 3, "adversarial": 3}

    def _vec(d: dict) -> list[float]:
        tier = _DIFFICULTY_TO_TIER.get(d.get("difficulty", "easy"), 1)
        refs = d.get("gold_evidence_refs") or []
        query = d.get("query_text") or ""
        ec = d.get("eval_criteria") or {}
        gold = ec.get("gold_answer") or ""
        tools = d.get("allowed_tools") or []
        return [
            min(tier / 3.0, 1.0),
            min(len(refs) / 10.0, 1.0),
            min(len(query) / 500.0, 1.0),
            min(len(gold) / 1000.0, 1.0),
            1.0 if "slurm" in tools else 0.0,
        ]

    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        return dot / (na * nb) if na and nb else 0.0

    specs: list[tuple[str, list[float]]] = []
    for f in task_files:
        with open(f) as fh:
            d = json.load(fh)
        specs.append((d.get("task_id", f.stem), _vec(d)))

    threshold = 0.95
    flagged: list[tuple[str, str, float]] = []
    for i in range(len(specs)):
        for j in range(i + 1, len(specs)):
            sim = _cosine(specs[i][1], specs[j][1])
            if sim >= threshold:
                flagged.append((specs[i][0], specs[j][0], sim))

    typer.echo("\nIndependence Check")
    typer.echo("=" * 70)
    if flagged:
        typer.echo(f"WARNING: {len(flagged)} near-duplicate pair(s) (threshold={threshold}):")
        for tid_a, tid_b, sim in flagged:
            typer.echo(f"  {tid_a} <-> {tid_b}  sim={sim:.4f}")
    else:
        typer.echo(f"OK: no near-duplicate pairs found (threshold={threshold})")

    # Exit non-zero if oracle check failed
    if oracle_failed > 0:
        raise typer.Exit(1)
