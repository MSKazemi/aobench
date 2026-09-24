"""``aobench quickstart`` — the whole benchmark in one zero-argument command.

The shortest previous path to a first result was
``aobench run task --task JOB_USR_001 --env env_01 --adapter direct_qa``: three flags
whose values a new user has no way to know, and which silently assume a source
checkout. This command takes no arguments, needs no API key and no network, picks a
representative task itself, runs it, explains the score it produced, and names the
next three commands worth running.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

quickstart_app = typer.Typer(help="Run your first benchmark task in one command.")

#: Preferred demo task. A stable, tier-1 job-failure task on the canonical snapshot —
#: it exercises tool use, grounding, and RBAC without needing a model provider.
_PREFERRED_TASK = "JOB_USR_001"

_DIMENSION_BLURB: dict[str, str] = {
    "outcome": "did the answer match the gold answer",
    "tool_use": "were the right tools called, with the right arguments, in order",
    "governance": "did the agent stay inside its RBAC role",
    "grounding": "was the answer supported by the snapshot evidence",
    "efficiency": "how much work was spent getting there",
}


def _pick_task(root: Path) -> tuple[str, str, str]:
    """Return ``(task_id, env_id, title)`` for the demo task.

    Prefers :data:`_PREFERRED_TASK`; otherwise falls back to the first dev-split task,
    then to the first task of any split, so the command still works against a trimmed
    or custom corpus.
    """
    specs_dir = root / "tasks" / "specs"
    preferred = specs_dir / f"{_PREFERRED_TASK}.json"
    candidates = [preferred] if preferred.is_file() else []
    others = sorted(p for p in specs_dir.glob("*.json") if p != preferred)

    dev_first: list[Path] = []
    rest: list[Path] = []
    for path in others:
        try:
            data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        (dev_first if data.get("benchmark_split") == "dev" else rest).append(path)

    for path in [*candidates, *dev_first, *rest]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        env_id = str(data.get("environment_id", ""))
        if (data.get("scoring_readiness", "blocked") != "blocked"
                and env_id and (root / "environments" / env_id).is_dir()):
            return str(data.get("task_id", path.stem)), env_id, str(data.get("title", ""))

    typer.echo(
        f"No runnable task found in {specs_dir} — check task readiness and environments.",
        err=True,
    )
    raise typer.Exit(code=2)


@quickstart_app.callback(invoke_without_command=True)
def quickstart(
    ctx: typer.Context,
    task_id: str = typer.Option(None, "--task", "-t", help="Task to run (default: chosen for you)."),
    adapter: str = typer.Option(
        "direct_qa", "--adapter", "-a", help="Adapter to evaluate. The default needs no API key."
    ),
    output_root: str = typer.Option("data/runs", "--output", "-o", help="Where to write the run."),
    benchmark_root: str = typer.Option("benchmark", "--benchmark-root"),
) -> None:
    """Run one benchmark task end-to-end and explain the result.

    Requires no API key, no network, and no cluster: the default ``direct_qa``
    adapter answers from the deterministic snapshot alone.
    """
    if ctx.invoked_subcommand is not None:  # pragma: no cover - no sub-commands today
        return

    from aobench.cli._common import require_task_spec, resolve_root
    from aobench.cli.run_cmd import _build_adapter
    from aobench.runners.run_artifacts import finalize_run_artifacts, write_run_manifest
    from aobench.runners.runner import BenchmarkRunner, BlockedTaskError
    from aobench.utils.ids import make_run_id
    from aobench.utils.logging import configure_logging

    configure_logging("WARNING")
    root = resolve_root(benchmark_root)

    if task_id:
        require_task_spec(root, task_id)
        spec = json.loads((root / "tasks" / "specs" / f"{task_id}.json").read_text(encoding="utf-8"))
        env_id, title = str(spec.get("environment_id", "")), str(spec.get("title", ""))
    else:
        task_id, env_id, title = _pick_task(root)
        spec = json.loads((root / "tasks" / "specs" / f"{task_id}.json").read_text(encoding="utf-8"))

    if spec.get("scoring_readiness", "blocked") == "blocked":
        typer.echo(str(BlockedTaskError(task_id)), err=True)
        raise typer.Exit(code=2)

    try:
        adapter_obj = _build_adapter(adapter)
    except ValueError:
        typer.echo(
            f"Unknown adapter '{adapter}'. Run `aobench list adapters` to see the options.",
            err=True,
        )
        raise typer.Exit(code=2) from None

    typer.echo("AOBench quickstart\n")
    typer.echo(f"  corpus   {root}")
    typer.echo(f"  task     {task_id}" + (f" — {title}" if title else ""))
    typer.echo(f"  env      {env_id}")
    typer.echo(f"  adapter  {adapter}" + ("  (tool-free baseline, no API key)" if adapter == "direct_qa" else ""))
    typer.echo("\nRunning…\n")

    run_id = make_run_id()
    run_dir = Path(output_root) / run_id
    write_run_manifest(run_dir, model=adapter, adapter=adapter, split="quickstart")

    runner = BenchmarkRunner(adapter=adapter_obj, benchmark_root=root, output_root=Path(output_root))
    try:
        result = runner.run(task_id, env_id, run_id=run_id)
    except Exception as exc:  # noqa: BLE001 - report the cause, never a traceback
        typer.echo(f"The run failed: {exc}", err=True)
        typer.echo("Run `aobench doctor` to check the installation.", err=True)
        raise typer.Exit(code=1) from exc

    finalize_run_artifacts(run_dir, [result])

    typer.echo(f"Aggregate score: {result.aggregate_score:.4f}   (0 = worst, 1 = best)")
    if result.hard_fail:
        typer.echo("Hard fail: the agent violated its RBAC role, which zeroes the task score.")
    typer.echo("\nPer dimension:")
    dims = result.dimension_scores
    for name, blurb in _DIMENSION_BLURB.items():
        value = getattr(dims, name, None)
        if value is not None:
            typer.echo(f"  {name:<12} {float(value):.4f}   {blurb}")

    typer.echo(
        "\nA low score is expected here: direct_qa is the tool-free reference baseline,"
        "\nso it answers without calling any HPC tool. That is the number a real agent"
        "\nhas to beat."
    )

    typer.echo(f"\nRun written to: {run_dir.resolve()}")
    typer.echo("\nNext:")
    typer.echo(f"  aobench report json {run_dir}   — the full per-dimension report")
    typer.echo("  aobench list tasks --split dev   — browse the dev split (including blocked drafts)")
    typer.echo("  aobench list adapters            — evaluate a real model instead")
